#!/usr/bin/env python3
"""从 ModelScope 下载 ERes2NetV2 预训练权重到 models/eres2netv2/。"""
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_DIR = ROOT / "models" / "eres2netv2"
MODEL_ID = "iic/speech_eres2netv2_sv_zh-cn_16k-common"


def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    ckpt = TARGET_DIR / "pretrained_eres2netv2.ckpt"
    if ckpt.exists():
        print(f"已存在 {ckpt}，跳过下载")
        return 0

    try:
        from modelscope.hub.snapshot_download import snapshot_download
    except ImportError:
        print("请先安装: pip install modelscope")
        return 1

    print(f"正在从 ModelScope 下载 {MODEL_ID} ...")
    try:
        cache_dir = snapshot_download(MODEL_ID, cache_dir=str(ROOT / "models" / ".cache"))
    except Exception as e:
        print(f"下载失败: {e}")
        print("可手动从 https://www.modelscope.cn/models/iic/speech_eres2netv2_sv_zh-cn_16k-common 下载权重并放到 models/eres2netv2/")
        return 1

    cache_path = Path(cache_dir)
    # 查找 .pth / .pt / .ckpt
    for ext in ("*.pth", "*.pt", "*.ckpt", "*.bin"):
        for f in cache_path.rglob(ext):
            if "model" in f.name.lower() or "checkpoint" in f.name.lower() or f.suffix == ".pth":
                shutil.copy2(f, ckpt)
                print(f"已复制到 {ckpt}")
                return 0
    # 任意一个权重文件
    for ext in ("*.pth", "*.pt", "*.ckpt"):
        for f in sorted(cache_path.rglob(ext)):
            shutil.copy2(f, ckpt)
            print(f"已复制 {f.name} 到 {ckpt}")
            return 0

    print("未在下载目录中找到权重文件，请检查 ModelScope 模型结构")
    return 1


if __name__ == "__main__":
    sys.exit(main())
