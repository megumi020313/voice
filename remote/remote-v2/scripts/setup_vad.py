#!/usr/bin/env python3
"""将 Silero VAD 从 torch.hub 下载到 models/vad，供 source='local' 加载。"""
import os
import shutil
import sys
from pathlib import Path

# 项目根目录 (remote-v2)
ROOT = Path(__file__).resolve().parent.parent
VAD_DIR = ROOT / "models" / "vad"


def main():
    VAD_DIR.mkdir(parents=True, exist_ok=True)
    if (VAD_DIR / "hubconf.py").exists() and (VAD_DIR / "src" / "silero_vad" / "data" / "silero_vad.jit").exists():
        print("models/vad 已存在且包含 silero_vad.jit，跳过下载")
        return 0

    import torch
    hub_dir = torch.hub.get_dir()
    # 从 GitHub 加载一次，会克隆到 hub 缓存
    print("正在从 torch.hub 下载 Silero VAD（仅首次较慢）...")
    try:
        torch.hub.load("snakers4/silero-vad", "silero_vad", source="github", trust_repo=True)
    except Exception as e:
        print(f"下载失败: {e}")
        print("请检查网络后重试，或手动克隆: git clone https://github.com/snakers4/silero-vad.git models/vad")
        return 1

    # 查找缓存中的 silero-vad 目录（含 hubconf.py）
    hub_path = Path(hub_dir)
    found = None
    for f in hub_path.rglob("hubconf.py"):
        try:
            with open(f) as fp:
                if "silero_vad" in fp.read():
                    found = f.parent
                    break
        except Exception:
            continue
    if not found:
        print("未在 torch hub 缓存中找到 silero-vad，请手动: git clone https://github.com/snakers4/silero-vad.git models/vad")
        return 1

    if VAD_DIR.exists():
        shutil.rmtree(VAD_DIR)
    shutil.copytree(found, VAD_DIR)
    print(f"已复制到 {VAD_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
