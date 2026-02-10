# ERes2NetV2 声纹模型

将预训练权重放到本目录，文件名任选其一：

- `pretrained_eres2netv2.ckpt`（推荐）
- 或任意 `.ckpt` / `.pth` / `.pt` / `.bin`（程序会自动选用第一个）

**一键下载（推荐）**：在 `remote/remote-v2/` 下执行：

```bash
pip install modelscope
python scripts/setup_eres2netv2.py
```

脚本会从 ModelScope 下载 `iic/speech_eres2netv2_sv_zh-cn_16k-common` 并复制到本目录。

**手动**：从 [ModelScope ERes2NetV2](https://www.modelscope.cn/models/iic/speech_eres2netv2_sv_zh-cn_16k-common) 下载权重文件到本目录。

放置完成后重启 API 服务即可加载声纹识别。
