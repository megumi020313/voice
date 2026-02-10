#!/usr/bin/env python3
"""从 Hugging Face 下载 faster-whisper-large-v3 到 models/faster-whisper-large-v3。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_DIR = ROOT / "models" / "faster-whisper-large-v3"
REPO_ID = "Systran/faster-whisper-large-v3"


def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    # 检查是否已有模型权重（大文件）
    has_weights = any(
        f.suffix in (".bin", ".safetensors", ".pt", ".onnx")
        for f in TARGET_DIR.rglob("*")
        if f.is_file()
    )
    if has_weights:
        print(f"models/faster-whisper-large-v3 已含权重，跳过下载")
        return 0

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("请先安装: pip install huggingface_hub")
        return 1

    print(f"正在从 Hugging Face 下载 {REPO_ID}（约 3GB，网络不稳可多试几次）...")
    try:
        snapshot_download(
            repo_id=REPO_ID,
            local_dir=str(TARGET_DIR),
        )
        print(f"已下载到 {TARGET_DIR}")
        return 0
    except Exception as e:
        print(f"下载失败: {e}")
        print("可稍后重试，或使用稳定网络/VPN 后执行: python scripts/setup_faster_whisper.py")
        print("或手动从 https://huggingface.co/Systran/faster-whisper-large-v3 下载到本目录")
        return 1


if __name__ == "__main__":
    sys.exit(main())
