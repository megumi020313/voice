"""声纹识别推理流水线"""
from __future__ import annotations

import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Union, List, Tuple

from backend.models.vad import SileroVAD
from backend.models.speaker import ERes2NetV2
from backend.core.vector_storage import VectorStorage, get_vector_storage
from backend.core.config import get_config
from backend.core.exceptions import AudioFormatError, ModelInferenceError
from backend.utils.logger import get_logger
from backend.utils.audio_utils import (
    validate_audio,
    calculate_precise_intervals,
    calculate_session_intervals,
    calculate_diarization_intervals,
    augment_with_noise,
    map_score_to_percentage,
)


class InferencePipeline:
    """端到端的声纹识别推理流水线"""
    
    def __init__(
        self,
        vad_model: Optional[SileroVAD] = None,
        speaker_model: Optional[ERes2NetV2] = None,
        vector_storage: Optional[VectorStorage] = None,
        enable_asr: bool = False
    ):
        """
        初始化推理流水线
        
        Args:
            vad_model: VAD模型实例
            speaker_model: 声纹识别模型实例
            vector_storage: 向量存储实例
            enable_asr: 是否启用 ASR（自动语音识别）
        """
        self.logger = get_logger()
        self.config = get_config()
        
        # 初始化组件
        self.vad = vad_model or SileroVAD()
        self.speaker_model = speaker_model or ERes2NetV2()
        self.vector_storage = vector_storage or get_vector_storage()
        
        # 初始化 ASR（可选）
        self.asr_service = None
        self.enable_asr = enable_asr
        if enable_asr:
            try:
                from backend.modules.audio_analysis import WhisperService
                self.asr_service = WhisperService()
                self.logger.info("✅ ASR 服务已启用")
            except Exception as e:
                self.logger.error(f"❌ ASR 服务初始化失败: {e}")
                self.enable_asr = False
        
        # 初始化 IoTDB 连接器（可选）
        self.iotdb_connector = None
        if self.config.iotdb_enabled:
            try:
                from backend.data.iotdb import IoTDBConnector
                self.iotdb_connector = IoTDBConnector()
                self.logger.info("✅ IoTDB 连接器已启用")
            except Exception as e:
                self.logger.warning(f"IoTDB 连接器初始化失败: {e}")
                self.logger.warning("将继续运行但不写入 IoTDB")
        
        # 初始化对话智能引擎（V3.0）
        self.diarization_engine = None
        if enable_asr and hasattr(self.config, 'diarization_enabled') and self.config.diarization_enabled:
            try:
                from backend.modules.diarization import DiarizationEngine
                self.diarization_engine = DiarizationEngine(
                    time_threshold=self.config.diarization_time_threshold,
                    similarity_threshold=self.config.diarization_similarity_threshold,
                    low_confidence_threshold=self.config.diarization_low_confidence_threshold
                )
                self.logger.info("✅ 对话智能引擎已初始化")
            except Exception as e:
                self.logger.warning(f"对话智能引擎初始化失败: {e}")
                self.diarization_engine = None
        
        self.logger.info("Inference pipeline initialized successfully")
    
    def _apply_global_vad_gating(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000
    ) -> List[Dict[str, Any]]:
        """V3.1.1 全局VAD门控与片段优化（方案F：分离padding）
        
        实现架构优化文档阶段1 + 方案F改进：
        1. 全局VAD检测有效语音区域
        2. 片段优化器（Merge + 小Padding + 过滤）- 用于边界判断
        3. 生成统一Payload供ASR和SV使用
        
        方案F核心改进：
        - speech_pad_ms（100ms）：仅用于边界判断和合并，避免不同说话人片段重叠
        - extraction_pad_ms（300ms）：仅用于SV特征提取，保证充足上下文
        
        Args:
            audio: 原始音频数据
            sample_rate: 采样率
            
        Returns:
            优化后的片段列表，每个片段包含：
            {
                'start_sample': int,  # 原始起始样本
                'end_sample': int,    # 原始结束样本
                'padded_start_sample': int,  # 小Padding后起始样本（边界判断用）
                'padded_end_sample': int,    # 小Padding后结束样本（边界判断用）
                'extraction_start_sample': int,  # 大Padding后起始样本（特征提取用）
                'extraction_end_sample': int,    # 大Padding后结束样本（特征提取用）
                'start': float,  # 原始起始时间（秒）
                'end': float,    # 原始结束时间（秒）
                'padded_start': float,  # 小Padding后起始时间（秒）
                'padded_end': float,    # 小Padding后结束时间（秒）
                'extraction_start': float,  # 大Padding后起始时间（秒）
                'extraction_end': float,    # 大Padding后结束时间（秒）
                'audio': np.ndarray  # 小Padding后的音频片段（用于边界判断）
                'extraction_audio': np.ndarray  # 大Padding后的音频片段（用于特征提取）
            }
        """
        self.logger.info("🛡️ V3.1.1 全局VAD门控启动（方案F：分离padding）...")
        
        # 1. 全局VAD检测
        vad_regions = self.vad.get_speech_timestamps(
            audio=audio,
            sample_rate=sample_rate,
            threshold=self.config.vad_threshold,
            min_speech_duration_ms=self.config.min_speech_duration_ms,
            min_silence_duration_ms=self.config.min_silence_duration_ms,
            speech_pad_ms=0  # 先不padding，后面统一处理
        )
        
        if not vad_regions:
            self.logger.warning("VAD未检测到有效语音")
            return []
        
        self.logger.info(f"VAD检测到 {len(vad_regions)} 个原始语音片段")
        
        # 2. 片段优化器：Merge（合并短间隔片段）
        merged_regions = []
        if vad_regions:
            current_region = vad_regions[0].copy()
            
            for next_region in vad_regions[1:]:
                # 计算间隔（样本数）
                gap_samples = next_region['start'] - current_region['end']
                gap_ms = (gap_samples / sample_rate) * 1000
                
                # 如果间隔小于 min_silence_duration，合并
                if gap_ms < self.config.min_silence_duration_ms:
                    current_region['end'] = next_region['end']
                    self.logger.debug(f"合并片段：间隔 {gap_ms:.1f}ms < {self.config.min_silence_duration_ms}ms")
                else:
                    merged_regions.append(current_region)
                    current_region = next_region.copy()
            
            # 添加最后一个片段
            merged_regions.append(current_region)
        
        self.logger.info(f"合并后剩余 {len(merged_regions)} 个片段")
        
        # 3. 片段优化器：双重Padding（方案F）+ 过滤（过短片段）
        optimized_segments = []
        total_audio_samples = len(audio)
        
        # 小padding：用于边界判断和合并（避免重叠）
        boundary_padding_samples = int((self.config.speech_pad_ms / 1000) * sample_rate)
        
        # 大padding：用于特征提取（保证上下文）
        extraction_padding_samples = int((self.config.extraction_pad_ms / 1000) * sample_rate)
        
        min_duration_samples = int((self.config.min_speech_duration_ms / 1000) * sample_rate)
        
        for region in merged_regions:
            start_sample = region['start']
            end_sample = region['end']
            
            # 过滤：检查时长
            duration_samples = end_sample - start_sample
            if duration_samples < min_duration_samples:
                duration_ms = (duration_samples / sample_rate) * 1000
                self.logger.debug(f"过滤过短片段: {duration_ms:.1f}ms < {self.config.min_speech_duration_ms}ms")
                continue
            
            # 小Padding：边界判断用（裁剪到音频边界）
            padded_start_sample = max(0, start_sample - boundary_padding_samples)
            padded_end_sample = min(total_audio_samples, end_sample + boundary_padding_samples)
            
            # 大Padding：特征提取用（裁剪到音频边界）
            extraction_start_sample = max(0, start_sample - extraction_padding_samples)
            extraction_end_sample = min(total_audio_samples, end_sample + extraction_padding_samples)
            
            # 提取两种padding的音频片段
            audio_segment = audio[padded_start_sample:padded_end_sample]
            extraction_audio_segment = audio[extraction_start_sample:extraction_end_sample]
            
            # 构建片段信息
            segment = {
                'start_sample': start_sample,
                'end_sample': end_sample,
                'padded_start_sample': padded_start_sample,
                'padded_end_sample': padded_end_sample,
                'extraction_start_sample': extraction_start_sample,
                'extraction_end_sample': extraction_end_sample,
                'start': start_sample / sample_rate,
                'end': end_sample / sample_rate,
                'padded_start': padded_start_sample / sample_rate,
                'padded_end': padded_end_sample / sample_rate,
                'extraction_start': extraction_start_sample / sample_rate,
                'extraction_end': extraction_end_sample / sample_rate,
                'audio': audio_segment,
                'extraction_audio': extraction_audio_segment
            }
            
            optimized_segments.append(segment)
        
        self.logger.info(f"✅ 全局VAD门控完成: {len(optimized_segments)} 个优化片段")
        self.logger.info(
            f"📊 Padding配置: 边界判断={self.config.speech_pad_ms}ms, "
            f"特征提取={self.config.extraction_pad_ms}ms"
        )
        
        # 输出统计信息（可观测指标）
        total_duration = len(audio) / sample_rate
        valid_duration = sum(seg['end'] - seg['start'] for seg in optimized_segments)
        silence_filtering_rate = (total_duration - valid_duration) / total_duration if total_duration > 0 else 0
        
        self.logger.info(
            f"📊 静音过滤率: {silence_filtering_rate:.1%} "
            f"(总时长: {total_duration:.2f}s, 有效时长: {valid_duration:.2f}s)"
        )
        
        return optimized_segments
    
    def _filter_asr_by_vad(
        self,
        asr_results: List[Dict[str, Any]],
        optimized_segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """V3.1.1混合模式：使用VAD结果过滤ASR词（方案B：放宽容忍度）
        
        后处理步骤：过滤落在静音区的ASR词
        
        方案B改进：放宽过滤条件，避免丢失真实语音词
        - 策略1：词的中心点在segment内 → 保留
        - 策略2：词与任意segment有≥30% IoU重叠 → 保留
        - 策略3：词在segment边界±100ms范围内 → 保留
        - 策略4：完全在segment间隙中且无重叠 → 丢弃
        
        Args:
            asr_results: ASR识别结果（词级时间戳）
            optimized_segments: 全局VAD门控生成的有效片段
            
        Returns:
            过滤后的ASR结果（仅保留有效语音区域的词）
        """
        if not asr_results or not optimized_segments:
            return asr_results
        
        filtered_results = []
        filtered_count = 0
        
        # 获取配置参数
        iou_threshold = self.config.asr_filter_iou_threshold  # 默认0.3
        boundary_tolerance = self.config.asr_filter_boundary_tolerance_ms / 1000  # 转换为秒
        
        for word in asr_results:
            word_start = word['start']
            word_end = word['end']
            word_center = (word_start + word_end) / 2
            word_duration = word_end - word_start
            
            should_keep = False
            keep_reason = ""
            
            for seg in optimized_segments:
                seg_start = seg['start']
                seg_end = seg['end']
                
                # 策略1：中心点在segment内
                if seg_start <= word_center <= seg_end:
                    should_keep = True
                    keep_reason = "center_in_segment"
                    break
                
                # 策略2：计算IoU
                overlap_start = max(word_start, seg_start)
                overlap_end = min(word_end, seg_end)
                overlap_duration = max(0, overlap_end - overlap_start)
                
                if overlap_duration > 0:
                    iou = overlap_duration / word_duration
                    if iou >= iou_threshold:
                        should_keep = True
                        keep_reason = f"iou={iou:.2f}>={iou_threshold}"
                        break
                
                # 策略3：边界容忍（±100ms）
                if (abs(word_start - seg_end) <= boundary_tolerance or 
                    abs(word_end - seg_start) <= boundary_tolerance):
                    should_keep = True
                    keep_reason = f"boundary_tolerance<={boundary_tolerance*1000:.0f}ms"
                    break
            
            if should_keep:
                filtered_results.append(word)
                self.logger.debug(
                    f"保留词: '{word.get('word', '')}' "
                    f"[{word_start:.2f}s - {word_end:.2f}s] "
                    f"(原因: {keep_reason})"
                )
            else:
                filtered_count += 1
                # 记录被过滤的词（调试用）
                self.logger.debug(
                    f"过滤静音区词: '{word.get('word', '')}' "
                    f"[{word_start:.2f}s - {word_end:.2f}s] "
                    f"(中心点 {word_center:.2f}s 不在有效区域，无重叠，超出边界容忍)"
                )
        
        if filtered_count > 0:
            self.logger.info(
                f"📊 ASR过滤统计: 保留 {len(filtered_results)}/{len(asr_results)} 个词, "
                f"过滤 {filtered_count} 个词 "
                f"(IoU阈值={iou_threshold}, 边界容忍={boundary_tolerance*1000:.0f}ms)"
            )
        
        return filtered_results
    
    def register(
        self,
        audio: np.ndarray,
        user_id: str,
        sample_rate: int = 16000,
        metadata: Optional[Dict] = None,
        overwrite: bool = False,
        save_audio: bool = False
    ) -> Dict[str, Any]:
        """
        注册用户声纹（单样本模式，兼容旧接口）
        
        Args:
            audio: 音频数据
            user_id: 用户ID
            sample_rate: 采样率
            metadata: 用户元数据
            overwrite: 是否覆盖已存在的用户
            save_audio: 是否保存音频样本
            
        Returns:
            注册结果字典
        """
        # 单样本模式：直接调用多样本注册，只传一个音频
        return self.register_multi_sample(
            audio_list=[audio],
            user_id=user_id,
            sample_rate=sample_rate,
            metadata=metadata,
            overwrite=overwrite,
            save_audio=save_audio
        )
    
    def register_multi_sample(
        self,
        audio_list: List[np.ndarray],
        user_id: str,
        sample_rate: int = 16000,
        metadata: Optional[Dict] = None,
        overwrite: bool = False,
        save_audio: bool = False
    ) -> Dict[str, Any]:
        """
        多样本注册用户声纹（推荐用于火锅店等嘈杂环境）
        
        采用阶梯式注册逻辑：
        - 第3级（警告态）：有效片段 < 3 或总时长 < 5s，注册失败
        - 第2级（标准态）：有效片段 3-10 个，全部使用
        - 第1级（理想态）：有效片段 > 10 个，随机采样8个（防止过拟合）
        
        质量控制：
        - SNR检测：过滤噪音过大的片段（SNR < 5dB）
        - 加权平均：使用余弦距离加权，抑制离群点影响
        
        Args:
            audio_list: 音频数据列表（建议3个样本：安静、稍吵、正常）
            user_id: 用户ID
            sample_rate: 采样率
            metadata: 用户元数据
            overwrite: 是否覆盖已存在的用户
            save_audio: 是否保存音频样本
            
        Returns:
            注册结果字典
        """
        try:
            from backend.utils.audio_utils import calculate_snr
            
            if not audio_list:
                return {
                    "success": False,
                    "error": "No audio provided",
                    "user_id": user_id
                }
            
            valid_segments = []  # 存储有效的音频片段和embedding
            total_duration = 0.0
            
            # 逐个处理每个音频样本
            for idx, audio in enumerate(audio_list, 1):
                # 1. 验证音频格式（不限制最大时长）
                validate_audio(
                    audio,
                    sample_rate=sample_rate,
                    max_duration=None  # 注册时不限制时长
                )
                
                # 2. VAD检测并切分语音片段
                speech_timestamps = self.vad.get_speech_timestamps(
                    audio=audio,
                    sample_rate=sample_rate,
                    threshold=self.config.vad_threshold
                )
                
                if not speech_timestamps:
                    self.logger.warning(f"No speech detected in sample {idx}/{len(audio_list)}")
                    continue
                
                # 3. 处理每个语音片段
                for seg_idx, ts in enumerate(speech_timestamps, 1):
                    start_sample = ts['start']
                    end_sample = ts['end']
                    segment = audio[start_sample:end_sample]
                    
                    # 计算片段时长
                    segment_duration = len(segment) / sample_rate
                    if segment_duration < 0.5:  # 跳过太短的片段
                        continue
                    
                    # SNR质量检测：过滤噪音过大的片段
                    snr = calculate_snr(segment, sample_rate)
                    if snr < 5.0:  # SNR阈值：5dB
                        self.logger.warning(
                            f"Sample {idx} segment {seg_idx} rejected: SNR={snr:.1f}dB < 5dB"
                        )
                        continue
                    
                    # 提取声纹特征（根据配置决定是否使用加噪增强）
                    try:
                        embeddings_to_average = []
                        
                        # 1. 提取原始音频的声纹特征
                        clean_embedding = self.speaker_model.extract_embedding(segment)
                        embeddings_to_average.append(clean_embedding)
                        
                        # 2. 如果启用加噪增强，提取加噪音频的声纹特征
                        if self.config.noise_augmentation_enabled:
                            augmented_segment = augment_with_noise(
                                segment,
                                min_factor=self.config.noise_ratio_min,
                                max_factor=self.config.noise_ratio_max
                            )
                            augmented_embedding = self.speaker_model.extract_embedding(augmented_segment)
                            embeddings_to_average.append(augmented_embedding)
                        
                        # 3. 对提取的特征向量进行平均
                        if len(embeddings_to_average) == 1:
                            # 未启用加噪增强，直接使用原始特征
                            final_embedding = embeddings_to_average[0]
                        else:
                            # 启用了加噪增强，对原始和加噪特征进行平均
                            final_embedding = np.mean(embeddings_to_average, axis=0)
                        
                        valid_segments.append({
                            'audio': segment,
                            'embedding': final_embedding,
                            'duration': segment_duration,
                            'snr': snr,
                            'sample_idx': idx,
                            'segment_idx': seg_idx,
                            'noise_augmented': self.config.noise_augmentation_enabled
                        })
                        total_duration += segment_duration
                        
                        aug_status = "with noise augmentation" if self.config.noise_augmentation_enabled else "clean only"
                        self.logger.info(
                            f"Sample {idx} segment {seg_idx}: duration={segment_duration:.2f}s, SNR={snr:.1f}dB ({aug_status})"
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to extract embedding: {str(e)}")
                        continue
            
            # 阶梯式决策逻辑
            num_valid = len(valid_segments)
            
            # 第3级（警告态）：质量准入门槛
            if num_valid < 3 or total_duration < 5.0:
                return {
                    "success": False,
                    "error": f"Insufficient valid speech: {num_valid} segments, {total_duration:.1f}s total (require ≥3 segments and ≥5s)",
                    "user_id": user_id,
                    "quality_check": {
                        "valid_segments": num_valid,
                        "total_duration": round(total_duration, 2),
                        "min_required_segments": 3,
                        "min_required_duration": 5.0
                    }
                }
            
            # 第2级（标准态）：数据保全策略
            if num_valid <= 10:
                selected_segments = valid_segments
                strategy = "standard_mode_use_all"
                self.logger.info(f"Standard mode: using all {num_valid} segments")
            
            # 第1级（理想态）：多样性最大化策略
            else:
                # 随机采样8个片段（防止过拟合）
                import random
                selected_segments = random.sample(valid_segments, 8)
                strategy = "ideal_mode_random_sample"
                self.logger.info(f"Ideal mode: randomly sampled 8 from {num_valid} segments")
            
            # 提取embeddings
            embeddings = [seg['embedding'] for seg in selected_segments]
            
            # 加权平均算法（质心计算）
            final_embedding = self._weighted_average_embeddings(embeddings)
            
            # AS-Norm显著性检测（软拒绝）
            distinctiveness = self.vector_storage.check_voiceprint_distinctiveness(final_embedding)
            warning = None
            if not distinctiveness['passed']:
                warning = {
                    "level": "warning",  # 软拒绝，非error
                    "message": distinctiveness.get('suggestion', '声音辨识度偏低'),
                    "avg_similarity": distinctiveness.get('avg_similarity', 0.0),
                    "max_similarity": distinctiveness.get('max_similarity', 0.0),
                    "quality_level": distinctiveness.get('quality_level', 'poor'),
                    "can_proceed": True  # 允许用户选择继续
                }
                self.logger.warning(
                    f"User {user_id} voiceprint distinctiveness check: "
                    f"avg_sim={distinctiveness.get('avg_similarity', 0.0):.3f}, "
                    f"quality={distinctiveness.get('quality_level', 'unknown')}"
                )
            
            # 存储到向量数据库（自动预计算T-Norm参数）
            from datetime import datetime
            
            self.vector_storage.register(
                user_id=user_id,
                embedding=final_embedding,
                metadata={
                    **(metadata or {}),
                    "num_valid_segments": num_valid,
                    "num_selected_segments": len(selected_segments),
                    "total_duration": round(total_duration, 2),
                    "registration_strategy": strategy,
                    "registration_mode": "tiered_quality_control",
                    "registered_at": datetime.now().isoformat(),
                    "avg_snr": round(np.mean([seg['snr'] for seg in selected_segments]), 2),
                    "distinctiveness_score": distinctiveness.get('avg_similarity', 0.0),
                    "quality_level": distinctiveness.get('quality_level', 'unknown')
                },
                overwrite=overwrite
            )
            
            # 可选：保存音频样本
            if save_audio:
                for idx, seg in enumerate(selected_segments, 1):
                    self._save_audio_sample(seg['audio'], f"{user_id}_seg{idx}", sample_rate)
            
            self.logger.info(
                f"User {user_id} registered successfully: {num_valid} valid segments, "
                f"{len(selected_segments)} selected, {total_duration:.1f}s total, strategy={strategy}, "
                f"S-Norm enabled, quality={distinctiveness.get('quality_level', 'unknown')}"
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "num_valid_segments": num_valid,
                "num_selected_segments": len(selected_segments),
                "total_duration": round(total_duration, 2),
                "registration_strategy": strategy,
                "registration_mode": "tiered_quality_control_with_snorm",
                "embedding_shape": list(final_embedding.shape),
                "quality_metrics": {
                    "avg_snr": round(np.mean([seg['snr'] for seg in selected_segments]), 2),
                    "min_snr": round(min(seg['snr'] for seg in selected_segments), 2),
                    "max_snr": round(max(seg['snr'] for seg in selected_segments), 2),
                    "distinctiveness_score": distinctiveness.get('avg_similarity', 0.0),
                    "quality_level": distinctiveness.get('quality_level', 'unknown')
                },
                "warning": warning,  # 可能为None或包含警告信息
                "message": f"Registration successful: {num_valid} valid segments, {len(selected_segments)} selected, strategy={strategy}, S-Norm enabled"
            }
            
        except Exception as e:
            self.logger.error(f"Registration failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "user_id": user_id
            }
    
    def _weighted_average_embeddings(self, embeddings: List[np.ndarray], gamma: float = 2.0) -> np.ndarray:
        """
        加权平均算法（质心计算）
        
        使用高斯函数（径向基函数）对embeddings进行加权平均，
        距离质心越近的embedding权重越高，抑制离群点影响。
        
        算法步骤：
        1. 计算几何中心（初步质心）
        2. 计算各向量到中心的余弦距离
        3. 使用高斯函数计算权重：weight = exp(-gamma * distance^2)
        4. 执行加权平均
        5. L2归一化
        
        Args:
            embeddings: embedding向量列表
            gamma: 权重衰减速度参数，默认2.0
            
        Returns:
            加权平均后的embedding向量（已归一化）
        """
        if len(embeddings) == 1:
            emb = embeddings[0].flatten()
            return emb / (np.linalg.norm(emb) + 1e-9)
        
        # 转换为numpy数组
        emb_array = np.array([emb.flatten() for emb in embeddings])
        
        # 1. 计算几何中心（初步质心）
        centroid_initial = np.mean(emb_array, axis=0)
        
        # 2. 计算各向量到中心的余弦距离
        # 归一化向量
        centroid_norm = centroid_initial / (np.linalg.norm(centroid_initial) + 1e-9)
        emb_norms = emb_array / (np.linalg.norm(emb_array, axis=1, keepdims=True) + 1e-9)
        
        # 余弦相似度
        cosine_similarities = np.dot(emb_norms, centroid_norm)
        # 余弦距离 = 1 - 余弦相似度
        cosine_distances = 1.0 - cosine_similarities
        
        # 3. 使用高斯函数计算权重
        weights = np.exp(-gamma * cosine_distances ** 2)
        
        # 归一化权重
        weights = weights / (np.sum(weights) + 1e-9)
        
        # 4. 执行加权平均
        centroid_final = np.average(emb_array, axis=0, weights=weights)
        
        # 5. L2归一化
        final_embedding = centroid_final / (np.linalg.norm(centroid_final) + 1e-9)
        
        self.logger.debug(
            f"Weighted average: weights range [{weights.min():.3f}, {weights.max():.3f}], "
            f"distances range [{cosine_distances.min():.3f}, {cosine_distances.max():.3f}]"
        )
        
        return final_embedding
    
    def recognize(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        threshold: Optional[float] = None,
        multi_speaker: bool = True,
        start_time: Optional[datetime] = None,
        audio_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        识别用户身份（已废弃，请使用recognize_parallel_v3）
        
        注意：此方法已废弃，API现在只使用V3.0模式（recognize_parallel_v3）。
        保留此方法仅用于向后兼容。
        
        Args:
            audio: 音频数据
            sample_rate: 采样率
            threshold: 相似度阈值，默认使用配置值
            multi_speaker: 是否启用多人识别（切片识别）
            start_time: 音频开始的真实时间戳（UTC），用于计算绝对时间
            audio_filename: 音频文件名，用于生成详细日志文件名
            
        Returns:
            识别结果字典，包含绝对时间戳
        """
        # 确定基准时间戳（如果未提供，使用当前时间）
        base_timestamp = start_time if start_time is not None else datetime.now(timezone.utc)
        
        # 使用 low_threshold 作为识别阈值（S-Norm Z-Score）
        threshold = threshold or self.config.low_threshold
        
        try:
            # 1. 验证音频格式（不限制时长）
            validate_audio(
                audio,
                sample_rate=sample_rate,
                max_duration=None  # 识别时不限制时长
            )
            
            # 2. 使用VAD检测所有语音片段
            speech_timestamps = self.vad.get_speech_timestamps(
                audio=audio,
                sample_rate=sample_rate,
                threshold=self.config.vad_threshold
            )
            
            if not speech_timestamps:
                return {
                    "success": False,
                    "recognized": False,
                    "error": "No speech detected in audio",
                    "detections": [],
                    "total_speakers": 0
                }
            
            self.logger.info(f"Found {len(speech_timestamps)} speech segments")
            
            # 3. 对每个语音片段进行识别
            detections = []
            speaker_votes = {}  # 统计每个说话人出现的次数
            
            for idx, ts in enumerate(speech_timestamps, 1):
                start_sample = ts['start']
                end_sample = ts['end']
                
                # 计算片段时长
                segment_duration = (end_sample - start_sample) / sample_rate
                
                # 跳过太短的片段
                if segment_duration < self.config.min_segment_duration:
                    self.logger.debug(f"Segment {idx} too short ({segment_duration:.2f}s), skipping")
                    continue
                
                # 提取音频片段
                segment = audio[start_sample:end_sample]
                
                # 提取声纹特征
                try:
                    embedding = self.speaker_model.extract_embedding(segment)
                    
                    # 向量匹配
                    user_id, similarity = self.vector_storage.identify(
                        embedding=embedding,
                        threshold=threshold
                    )
                    
                    detection = {
                        "segment_id": idx,
                        "time_start": float(start_sample / sample_rate),
                        "time_end": float(end_sample / sample_rate),
                        "duration": float(segment_duration),
                        "user_id": user_id,
                        "similarity": float(similarity),
                        "recognized": user_id is not None
                    }
                    
                    detections.append(detection)
                    
                    # 统计投票
                    if user_id:
                        speaker_votes[user_id] = speaker_votes.get(user_id, 0) + 1
                        self.logger.info(
                            f"Segment {idx} ({segment_duration:.1f}s): {user_id} (similarity: {similarity:.3f}, threshold: {threshold:.3f})"
                        )
                    else:
                        self.logger.info(
                            f"Segment {idx} ({segment_duration:.1f}s): Unknown (similarity: {similarity:.3f}, threshold: {threshold:.3f}) - 相似度低于阈值"
                        )
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process segment {idx}: {str(e)}")
                    continue
            
            # 4. 汇总结果
            if not detections:
                return {
                    "success": False,
                    "recognized": False,
                    "error": "No valid speech segments found",
                    "detections": [],
                    "total_speakers": 0
                }
            
            # 找出出现最多的说话人（主要说话人）
            primary_speaker = None
            max_votes = 0
            if speaker_votes:
                primary_speaker = max(speaker_votes, key=speaker_votes.get)
                max_votes = speaker_votes[primary_speaker]
            
            # 统计唯一说话人数量（不包括unknown）
            unique_speakers = list(speaker_votes.keys())
            
            result = {
                "success": True,
                "recognized": len(unique_speakers) > 0,
                "primary_speaker": primary_speaker,  # 主要说话人
                "detected_speakers": unique_speakers,  # 所有检测到的说话人列表
                "total_speakers": len(unique_speakers),  # 检测到的说话人数量
                "speaker_votes": speaker_votes,  # 每个说话人出现的次数
                "detections": detections,  # 所有片段的详细识别结果
                "total_segments": len(detections),
                "message": f"Detected {len(unique_speakers)} speaker(s) in {len(detections)} segments"
            }
            
            # 添加绝对时间戳
            return self._add_absolute_timestamps(result, base_timestamp)
            
        except Exception as e:
            self.logger.error(f"Recognition failed: {str(e)}")
            return {
                "success": False,
                "recognized": False,
                "error": str(e),
                "detections": [],
                "total_speakers": 0
            }
    
    def _save_audio_sample(
        self,
        audio: np.ndarray,
        user_id: str,
        sample_rate: int
    ) -> None:
        """
        保存音频样本到文件
        
        Args:
            audio: 音频数据数组
            user_id: 用户ID，用于创建用户目录
            sample_rate: 音频采样率
            
        Raises:
            AudioFormatError: 当音频保存失败时（错误会被记录但不会抛出）
        """
        try:
            from backend.utils.audio_utils import save_audio
            from datetime import datetime
            
            # 创建用户目录
            user_dir = self.config.audio_samples_path / user_id
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}.wav"
            filepath = user_dir / filename
            
            # 保存音频
            save_audio(audio, filepath, sample_rate)
            
            self.logger.debug(f"Audio sample saved: {filepath}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save audio sample: {str(e)}")
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户信息字典，包含embedding和metadata，如果用户不存在返回None
        """
        return self.vector_storage.get_user(user_id)
    
    def list_users(self) -> List[str]:
        """
        列出所有注册用户
        
        Returns:
            用户ID列表
        """
        return self.vector_storage.list_users()
    
    def delete_user(self, user_id: str) -> bool:
        """
        删除用户
        
        Args:
            user_id: 要删除的用户ID
            
        Returns:
            删除是否成功
            
        Raises:
            UserNotFoundError: 当用户不存在时（错误会被记录但不会抛出）
        """
        try:
            return self.vector_storage.delete(user_id)
        except Exception as e:
            self.logger.error(f"Failed to delete user {user_id}: {str(e)}")
            return False
    
    def _add_absolute_timestamps(
        self,
        result: Dict[str, Any],
        base_timestamp: datetime
    ) -> Dict[str, Any]:
        """
        为识别结果添加绝对时间戳
        
        Args:
            result: 识别结果字典
            base_timestamp: 基准时间戳（UTC）
            
        Returns:
            增强后的结果字典，包含绝对时间戳
        """
        # 添加基准时间戳到结果中
        result["base_timestamp_utc"] = base_timestamp.isoformat()
        
        # 为 segments 添加绝对时间戳
        if "segments" in result and isinstance(result["segments"], list):
            for segment in result["segments"]:
                if "start" in segment and "end" in segment:
                    # 计算绝对时间
                    absolute_start = base_timestamp + timedelta(seconds=segment["start"])
                    absolute_end = base_timestamp + timedelta(seconds=segment["end"])
                    
                    # 添加绝对时间戳字段
                    segment["absolute_start_time"] = absolute_start.isoformat()
                    segment["absolute_end_time"] = absolute_end.isoformat()
        
        # 为 detections 添加绝对时间戳（兼容旧格式）
        if "detections" in result and isinstance(result["detections"], list):
            for detection in result["detections"]:
                if "time_start" in detection and "time_end" in detection:
                    # 计算绝对时间
                    absolute_start = base_timestamp + timedelta(seconds=detection["time_start"])
                    absolute_end = base_timestamp + timedelta(seconds=detection["time_end"])
                    
                    # 添加绝对时间戳字段
                    detection["absolute_start_time"] = absolute_start.isoformat()
                    detection["absolute_end_time"] = absolute_end.isoformat()
        
        return result
    def _merge_speaker_segments(
        self,
        window_results: list,
        stride: float,
        merge_threshold: float = 0.7
    ) -> list:
        """
        合并连续的同一说话人窗口为片段
        
        策略：
        - 连续窗口识别为同一说话人 -> 合并
        - 说话人切换 -> 开始新片段
        - Unknown窗口：如果相似度很低(<merge_threshold)才独立，否则尝试合并到邻近片段
        
        Args:
            window_results: 窗口识别结果列表
            stride: 窗口步长（秒）
            merge_threshold: 合并阈值，低于此值的Unknown窗口会被独立
        
        Returns:
            合并后的片段列表
        """
        if not window_results:
            return []
        
        # 按时间排序
        windows = sorted(window_results, key=lambda x: x['time_start'])
        
        merged = []
        current_segment = None
        
        for window in windows:
            user_id = window['user_id']
            similarity = window['similarity']
            
            # 第一个窗口
            if current_segment is None:
                current_segment = {
                    'user_id': user_id,
                    'time_start': window['time_start'],
                    'time_end': window['time_end'],
                    'duration': window['time_end'] - window['time_start'],
                    'similarities': [similarity],
                    'window_count': 1
                }
                continue
            
            # 判断是否应该合并到当前片段
            should_merge = False
            
            if user_id == current_segment['user_id']:
                # 同一说话人，直接合并
                should_merge = True
            elif user_id is None and similarity < merge_threshold:
                # Unknown且相似度很低，不合并（开始新片段）
                should_merge = False
            elif current_segment['user_id'] is None and user_id is not None:
                # 从Unknown切换到已知说话人，不合并
                should_merge = False
            
            if should_merge:
                # 合并到当前片段
                current_segment['time_end'] = window['time_end']
                current_segment['duration'] = current_segment['time_end'] - current_segment['time_start']
                current_segment['similarities'].append(similarity)
                current_segment['window_count'] += 1
            else:
                # 保存当前片段，开始新片段
                current_segment['avg_similarity'] = float(np.mean(current_segment['similarities']))
                current_segment['min_similarity'] = float(np.min(current_segment['similarities']))
                current_segment['max_similarity'] = float(np.max(current_segment['similarities']))
                del current_segment['similarities']  # 删除原始列表，节省空间
                
                merged.append(current_segment)
                
                # 开始新片段
                current_segment = {
                    'user_id': user_id,
                    'time_start': window['time_start'],
                    'time_end': window['time_end'],
                    'duration': window['time_end'] - window['time_start'],
                    'similarities': [similarity],
                    'window_count': 1
                }
        
        # 保存最后一个片段
        if current_segment is not None:
            current_segment['avg_similarity'] = float(np.mean(current_segment['similarities']))
            current_segment['min_similarity'] = float(np.min(current_segment['similarities']))
            current_segment['max_similarity'] = float(np.max(current_segment['similarities']))
            del current_segment['similarities']
            merged.append(current_segment)
        
        # 添加片段ID
        for idx, seg in enumerate(merged, 1):
            seg['segment_id'] = idx
        
        self.logger.info(
            f"Merged {len(windows)} windows into {len(merged)} segments "
            f"(avg {len(windows)/len(merged):.1f} windows per segment)"
        )
        
        return merged

    def _smooth_segments(
        self,
        segments: list,
        gap_tolerance: float = 1.0,
        unknown_prune: float = 2.0
    ) -> list:
        """进一步平滑片段，合并同人近邻片段并丢弃极短未知片段。"""
        if not segments:
            return []

        # 按时间排序，避免遗漏乱序数据
        ordered = sorted(segments, key=lambda x: x['time_start'])

        smoothed = []
        current = dict(ordered[0])

        for next_seg in ordered[1:]:
            same_user = current.get('user_id') and current.get('user_id') == next_seg.get('user_id')
            gap = next_seg.get('time_start', 0.0) - current.get('time_end', 0.0)

            if same_user and gap <= gap_tolerance:
                # 加权平均相似度，累积窗口数量
                current_wc = current.get('window_count', 1)
                next_wc = next_seg.get('window_count', 1)
                total_wc = current_wc + next_wc
                if total_wc > 0:
                    weighted_avg = (
                        current.get('avg_similarity', 0.0) * current_wc +
                        next_seg.get('avg_similarity', 0.0) * next_wc
                    ) / total_wc
                else:
                    weighted_avg = 0.0

                current['time_end'] = max(current.get('time_end', 0.0), next_seg.get('time_end', 0.0))
                current['duration'] = float(current['time_end'] - current.get('time_start', 0.0))
                current['window_count'] = total_wc
                current['avg_similarity'] = float(weighted_avg)
                current['max_similarity'] = float(
                    max(
                        current.get('max_similarity', current.get('avg_similarity', 0.0)),
                        next_seg.get('max_similarity', next_seg.get('avg_similarity', 0.0))
                    )
                )
                current['min_similarity'] = float(
                    min(
                        current.get('min_similarity', current.get('avg_similarity', 0.0)),
                        next_seg.get('min_similarity', next_seg.get('avg_similarity', 0.0))
                    )
                )
                continue

            smoothed.append(current)
            current = dict(next_seg)

        smoothed.append(current)

        refined = []
        for seg in smoothed:
            duration = seg.get('duration', seg.get('time_end', 0.0) - seg.get('time_start', 0.0))
            seg['duration'] = float(duration)

            # 丢弃过短的未知片段
            if (seg.get('user_id') is None or seg.get('user_id') == 'unknown') and duration <= unknown_prune:
                continue

            refined.append(seg)

        # 重新编号
        for idx, seg in enumerate(refined, 1):
            seg['segment_id'] = idx

        return refined

    def _build_timeline_segments(
        self,
        raw_windows: list,
        total_duration: float,
        stride: float
    ) -> list:
        """构建覆盖全时长的时间轴分段（含未知）。"""
        if total_duration <= 0:
            return []

        step = max(stride, 0.05)  # 最小步长保护
        steps = int(np.ceil(total_duration / step))

        # 按时间排序窗口
        windows = sorted(raw_windows, key=lambda w: w.get('time_start', 0.0))

        timeline = []
        for idx in range(steps):
            t_start = idx * step
            t_end = min(total_duration, t_start + step)

            # 找到覆盖当前步长的窗口（允许重叠，取相似度最高的一个）
            best_win = None
            best_sim = -1.0
            for w in windows:
                ws = w.get('time_start', 0.0)
                we = w.get('time_end', ws)
                if we <= t_start or ws >= t_end:
                    continue
                sim = w.get('similarity', 0.0)
                if sim > best_sim:
                    best_sim = sim
                    best_win = w

            uid = best_win.get('user_id') if best_win is not None else 'unknown'
            if uid is None:
                uid = 'unknown'

            timeline.append({
                'user_id': uid,
                'similarity': best_sim if best_sim >= 0 else 0.0,
                'time_start': t_start,
                'time_end': t_end
            })

        # 合并连续同一用户的步长段，并统计相似度
        segments = []
        current = None

        for entry in timeline:
            uid = entry['user_id']
            sim = entry['similarity']
            ts = entry['time_start']
            te = entry['time_end']

            if current is None:
                current = {
                    'user_id': uid,
                    'time_start': ts,
                    'time_end': te,
                    'sims': [sim],
                    'step_count': 1
                }
                continue

            if uid == current['user_id']:
                current['time_end'] = te
                current['sims'].append(sim)
                current['step_count'] += 1
            else:
                segments.append(self._finalize_timeline_segment(current))
                current = {
                    'user_id': uid,
                    'time_start': ts,
                    'time_end': te,
                    'sims': [sim],
                    'step_count': 1
                }

        if current is not None:
            segments.append(self._finalize_timeline_segment(current))

        # 重新编号
        for idx, seg in enumerate(segments, 1):
            seg['segment_id'] = idx

        return segments

    @staticmethod
    def _finalize_timeline_segment(seg_dict: dict) -> dict:
        sims = seg_dict.get('sims', []) or [0.0]
        avg_sim = float(np.mean(sims))
        min_sim = float(np.min(sims))
        max_sim = float(np.max(sims))

        return {
            'user_id': seg_dict.get('user_id'),
            'recognized': seg_dict.get('user_id') not in (None, 'unknown'),
            'time_start': float(seg_dict.get('time_start', 0.0)),
            'time_end': float(seg_dict.get('time_end', 0.0)),
            'duration': float(seg_dict.get('time_end', 0.0) - seg_dict.get('time_start', 0.0)),
            'avg_similarity': avg_sim,
            'min_similarity': min_sim,
            'max_similarity': max_sim,
            'window_count': seg_dict.get('step_count', 1),
            'source': 'timeline_full'
        }

    def _aggregate_topk(self, window_results: list, top_k_ratio: float = 0.3) -> Tuple[Optional[str], float]:
        """Top-K 精英投票：按用户取最高分的前K窗口求均值。"""
        if not window_results:
            return None, 0.0

        user_scores: Dict[Optional[str], List[float]] = {}
        for win in window_results:
            uid = win.get("user_id")
            user_scores.setdefault(uid, []).append(win.get("similarity", 0.0))

        best_user = None
        best_score = 0.0

        for uid, scores in user_scores.items():
            scores.sort(reverse=True)
            k = max(1, int(len(scores) * top_k_ratio))
            top_scores = scores[:k]
            elite_score = float(np.mean(top_scores))
            if elite_score > best_score:
                best_score = elite_score
                best_user = uid

        return best_user, best_score

    @staticmethod
    def _final_decision(user_id: Optional[str], score: float, high_threshold: float, low_threshold: float) -> Dict[str, Any]:
        if score >= high_threshold:
            return {"user": user_id, "score": score, "status": "success"}
        if score < low_threshold:
            return {"user": "unknown", "score": score, "status": "rejected"}
        return {"user": "unknown", "score": score, "status": "uncertain"}
    def _identify_window_embedding(
        self, 
        embedding: np.ndarray, 
        threshold: float
    ) -> Tuple[Optional[str], float]:
        """
        识别单个窗口的 embedding 属于哪个用户
        
        Args:
            embedding: 窗口的特征向量
            threshold: 相似度阈值
            
        Returns:
            (user_id, similarity) 元组
        """
        try:
            user_id, similarity = self.vector_storage.identify(
                embedding=embedding,
                threshold=threshold
            )
            return user_id, similarity
        except Exception as e:
            self.logger.warning(f"Failed to identify window: {str(e)}")
            return None, 0.0
    
    def _merge_adjacent_segments(
        self, 
        segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        合并相邻的同一说话人片段
        
        V13.0 优化：允许 1.0s 内的间隙合并
        
        Args:
            segments: 原始片段列表
            
        Returns:
            合并后的片段列表
        """
        if not segments:
            return []
        
        # 按时间排序
        segments = sorted(segments, key=lambda x: x['start'])
        
        merged = [segments[0].copy()]
        
        for curr in segments[1:]:
            prev = merged[-1]
            
            # 如果是同一个人
            if prev.get('user') == curr.get('user'):
                gap = curr['start'] - prev['end']
                
                # 允许 1.0s 内的缝隙合并
                if gap <= 1.0:
                    # 合并片段
                    prev_dur = prev['end'] - prev['start']
                    curr_dur = curr['end'] - curr['start']
                    
                    # 加权平均分数
                    if prev_dur + curr_dur > 0:
                        prev['score'] = (
                            prev.get('score', 0.0) * prev_dur + 
                            curr.get('score', 0.0) * curr_dur
                        ) / (prev_dur + curr_dur)
                    
                    prev['end'] = curr['end']
                    prev['window_count'] = prev.get('window_count', 0) + curr.get('window_count', 0)
                    continue
            
            # 否则添加新片段
            merged.append(curr.copy())
        
        return merged

    def _write_v3_log(
        self,
        sv_results: List[Dict[str, Any]],
        asr_results: List[Dict[str, Any]],
        audio_filename: str
    ) -> str:
        """
        写入V3.0并行感知的详细日志
        
        Args:
            sv_results: 声纹识别结果
            asr_results: ASR识别结果
            audio_filename: 音频文件名
            
        Returns:
            日志文件路径
        """
        try:
            from pathlib import Path
            
            # 创建日志目录
            log_dir = Path("/home/swufe/Project/zhoulonghao/remote/remote-v2/logs/Speaker Recognition")
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成日志文件名（使用音频文件名，而不是 unknown）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 移除文件扩展名
            base_name = Path(audio_filename).stem if audio_filename else "unknown"
            log_filename = f"{base_name}_{timestamp}.log"
            log_path = log_dir / log_filename
            
            # 构建日志内容
            log_lines = []
            log_lines.append("=" * 80)
            log_lines.append("V3.0 并行感知详细日志")
            log_lines.append("=" * 80)
            log_lines.append(f"音频文件: {audio_filename}")
            log_lines.append(f"识别时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            log_lines.append("=" * 80)
            log_lines.append("")
            
            # SV结果
            log_lines.append(f"📊 声纹识别结果 ({len(sv_results)} 个片段):")
            log_lines.append("-" * 80)
            for i, sv in enumerate(sv_results):
                log_lines.append(
                    f"  [{i+1}] {sv['start']:.2f}s - {sv['end']:.2f}s | "
                    f"speaker={sv['speaker']} | z_score={sv['z_score']:.2f}"
                )
            log_lines.append("")
            
            # ASR结果（完整列举）
            log_lines.append(f"📝 ASR识别结果 ({len(asr_results)} 个词):")
            log_lines.append("-" * 80)
            for i, word in enumerate(asr_results):
                log_lines.append(
                    f"  [{i+1}] {word['start']:.2f}s - {word['end']:.2f}s | "
                    f"word='{word['word']}'"
                )
            log_lines.append("")
            
            log_lines.append("=" * 80)
            
            # 写入文件
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(log_lines))
            
            self.logger.info(f"V3.0详细日志已保存: {log_path}")
            
            return str(log_path)
            
        except Exception as e:
            self.logger.warning(f"写入V3.0日志失败: {e}")
            return None

    def transcribe_only(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: str = "zh",
        beam_size: int = 5,
        with_timestamps: bool = False
    ) -> Union[str, List[Dict]]:
        """
        仅执行 ASR 识别（不做声纹识别）
        
        Args:
            audio: 音频数据
            sample_rate: 采样率
            language: 语言代码
            beam_size: Beam search 大小
            with_timestamps: 是否返回带时间戳的片段
            
        Returns:
            如果 with_timestamps=False: 返回完整文本字符串
            如果 with_timestamps=True: 返回片段列表 [{"text": "...", "start": 0.0, "end": 2.5}]
        """
        if not self.enable_asr or self.asr_service is None:
            self.logger.error("ASR 未启用")
            return "" if not with_timestamps else []
        
        try:
            if with_timestamps:
                return self.asr_service.transcribe_with_timestamps(
                    audio=audio,
                    language=language,
                    beam_size=beam_size,
                    initial_prompt=self.config.asr_initial_prompt
                )
            else:
                return self.asr_service.transcribe(
                    audio=audio,
                    language=language,
                    beam_size=beam_size,
                    initial_prompt=self.config.asr_initial_prompt
                )
        except Exception as e:
            self.logger.error(f"ASR 识别失败: {e}", exc_info=True)
            return "" if not with_timestamps else []
    
    def recognize_parallel_v3(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        start_time: Optional[datetime] = None,
        language: str = "zh",
        beam_size: int = 5,
        audio_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """V3.0 并行感知接口
        
        同时执行声纹识别和ASR识别，返回两份独立的原始结果。
        这是V3.0方案的核心接口，为DiarizationEngine提供输入。
        
        Args:
            audio: 音频数据
            sample_rate: 采样率
            start_time: 音频开始时间（UTC）
            language: 语言代码
            beam_size: ASR beam search 大小
        
        Returns:
            {
                "sv_results": [
                    {
                        "start": 0.0,
                        "end": 2.5,
                        "speaker": "zlh",
                        "z_score": 5.2,
                        "embedding": [...],  # 192维向量
                        "confidence": 0.95
                    },
                    ...
                ],
                "asr_results": [
                    {
                        "word": "现在",
                        "start": 0.0,
                        "end": 0.5,
                        "confidence": 0.98
                    },
                    ...
                ],
                "base_timestamp_utc": "2025-12-25T10:00:00.000Z",
                "mode": "parallel_v3"
            }
        """
        if not self.enable_asr or self.asr_service is None:
            self.logger.error("V3.0模式需要启用ASR")
            raise ValueError("V3.0模式需要启用ASR")
        
        self.logger.info("🚀 V3.1 并行感知模式启动（全局VAD门控）...")
        
        # 确定基准时间戳
        if start_time is None:
            start_time = datetime.now(timezone.utc)
        
        # V3.1 阶段1：全局VAD门控与片段优化
        optimized_segments = self._apply_global_vad_gating(audio, sample_rate)
        
        if not optimized_segments:
            self.logger.warning("全局VAD门控：未检测到有效语音")
            return {
                "sv_results": [],
                "asr_results": [],
                "base_timestamp_utc": start_time.isoformat(),
                "mode": "parallel_v3.1"
            }
        
        # 1. 并行感知：声纹识别（使用统一Payload）
        self.logger.info(f"执行声纹识别（使用统一Payload，{len(optimized_segments)} 个片段）...")
        
        try:
            # ========== 批量推理优化：使用优化后的片段（方案F：使用大padding的extraction_audio） ==========
            audio_segments = []
            segment_metadata = []  # 保存每个片段的元数据
            
            for segment in optimized_segments:
                # 方案F：使用大padding的extraction_audio进行特征提取，保证充足上下文
                audio_segments.append(segment['extraction_audio'])
                # 使用原始时间（不含padding）作为SV结果的时间戳
                segment_metadata.append({
                    'start': segment['start'],
                    'end': segment['end']
                })
            
            # ========== 批量提取声纹特征 ==========
            sv_results = []
            if audio_segments:
                self.logger.info(
                    f"🚀 批量提取声纹特征: {len(audio_segments)} 个片段 "
                    f"(使用大padding={self.config.extraction_pad_ms}ms保证上下文)"
                )
                
                try:
                    # 使用批量推理（batch_size=16）
                    embeddings = self.speaker_model.extract_batch_embeddings(
                        audio_segments,
                        batch_size=self.config.speaker_batch_size
                    )
                    
                    # 识别每个片段的说话人
                    for idx, (embedding, metadata) in enumerate(zip(embeddings, segment_metadata)):
                        try:
                            # 识别说话人（使用 S-Norm 计算 Z-score）
                            user_id, z_score = self.vector_storage.identify(
                                embedding=embedding,
                                threshold=self.config.low_threshold,
                                use_as_norm=False,  # 不使用AS-Norm
                                use_snorm=True      # 使用S-Norm
                            )
                            
                            # 如果没有识别到，标记为 unknown
                            speaker = user_id if user_id else 'unknown'
                            
                            # Z-score 就是置信度
                            confidence = float(z_score) if z_score else 0.0
                            
                            sv_results.append({
                                'start': metadata['start'],
                                'end': metadata['end'],
                                'speaker': speaker,
                                'z_score': z_score,
                                'embedding': embedding.flatten().tolist() if hasattr(embedding, 'flatten') else embedding.tolist(),
                                'confidence': confidence
                            })
                            
                        except Exception as e:
                            self.logger.error(f"片段 {idx} 识别失败: {e}")
                            continue
                    
                except Exception as e:
                    self.logger.error(f"批量特征提取失败: {e}")
            
            self.logger.info(f"✅ 声纹识别完成: {len(sv_results)} 个片段")
            
        except Exception as e:
            self.logger.error(f"V3.0并行感知失败: {e}")
            return {
                "sv_results": [],
                "asr_results": [],
                "base_timestamp_utc": start_time.isoformat(),
                "mode": "parallel_v3.1_hybrid",
                "error": str(e)
            }
        
        # 2. 并行感知：ASR识别（混合模式：整段ASR + VAD后处理）
        self.logger.info("执行ASR识别（混合模式：整段ASR + VAD后处理）...")
        
        asr_results = []
        try:
            # V3.1混合模式：ASR处理整段音频（保持完整上下文）
            self.logger.info("🎯 ASR处理整段音频（保持完整上下文）...")
            asr_results = self.asr_service.transcribe_with_word_timestamps(
                audio=audio,  # ⚠️ 整段音频，不是片段
                language=language,
                beam_size=beam_size,
                initial_prompt=self.config.asr_initial_prompt
            )
            
            self.logger.info(f"✅ ASR识别完成: {len(asr_results)} 个词（整段音频）")
            
            # 后处理：过滤静音区的ASR词（使用VAD结果）
            if asr_results and optimized_segments:
                original_count = len(asr_results)
                asr_results = self._filter_asr_by_vad(asr_results, optimized_segments)
                filtered_count = original_count - len(asr_results)
                
                self.logger.info(
                    f"📊 VAD后处理：过滤了 {filtered_count} 个静音区词 "
                    f"({filtered_count}/{original_count} = {filtered_count/original_count:.1%})"
                )
                
                # 输出可观测指标：VAD静音区词占比
                silence_region_word_ratio = filtered_count / original_count if original_count > 0 else 0
                self.logger.info(
                    f"📊 VAD静音区词占比: {silence_region_word_ratio:.1%} "
                    f"(保留 {len(asr_results)}/{original_count} 个有效词)"
                )
            
        except Exception as e:
            self.logger.error(f"ASR识别失败: {e}")
            asr_results = []
        
        # 3. 写入详细日志（返回日志文件路径供后续追加）
        log_path = None
        if audio_filename:
            log_path = self._write_v3_log(sv_results, asr_results, audio_filename)
        
        self.logger.info(
            f"🎉 V3.0 并行感知完成: {len(sv_results)} 个SV片段, {len(asr_results)} 个ASR词"
        )
        
        # 4. 调用对话智能引擎（在Pipeline内部完成）
        dialogue_segments = None
        if self.diarization_engine is not None:
            try:
                dialogue_segments = self.diarization_engine.process(
                    sv_results=sv_results,
                    asr_results=asr_results,
                    log_path=log_path,
                    audio_tensor=audio,              # 传入音频
                    speaker_model=self.speaker_model  # 传入模型
                )
                self.logger.info(f"✅ 对话智能处理完成: {len(dialogue_segments)} 个片段")
            except Exception as e:
                self.logger.error(f"对话智能处理失败: {e}", exc_info=True)
        
        # 5. 返回完整结果
        result = {
            'sv_results': sv_results,
            'asr_results': asr_results,
            'dialogue_segments': dialogue_segments,  # 新增
            'base_timestamp_utc': start_time.isoformat(),
            'mode': 'parallel_v3.1_hybrid',  # V3.1混合模式: 全局VAD门控 + 整段ASR
            'log_path': log_path
        }
        
        return result

