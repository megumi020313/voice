# GitHub 上传清单

根据当前 `.gitignore` 规则，以下为文件上传状态清单。

## ✅ 会被上传的文件

### 根目录文件
- `.gitignore` - Git 忽略规则文件
- `requirements.txt` - Python 依赖清单
- `启动` - 启动脚本
- `稳定环境清单.txt` - 环境清单
- `ASR精度提升技术方案.md` - 技术方案文档
- `更换模型方案书.md` - 模型方案文档
- `部署指南_Windows_macOS.md` - 部署指南

### 源代码文件
- **Python 源代码** (`*.py`)
  - `remote/remote-v2/backend/**/*.py` - 后端代码
  - `remote/brain_core/backend/**/*.py` - Brain-Core 代码
  - `SMP/backend/**/*.py` - SMP 模块代码
  - `remote/3D-Speaker/speakerlab/**/*.py` - 3D-Speaker 代码
  - 所有 Python 源代码文件（除 `__pycache__/` 和编译文件）

- **配置文件**
  - `*.yaml` / `*.yml` - YAML 配置文件
  - `*.json` - JSON 配置文件（模型配置等）
  - `remote/remote-v2/config/*.yaml` - 服务器和模型配置
  - `remote/remote-v2/config/model_config.yaml.bak` - 配置备份

- **前端文件**
  - `*.html` - HTML 模板文件
  - `*.js` - JavaScript 文件（除 `node_modules/`）
  - `*.css` - CSS 样式文件
  - `remote/remote-v2/web/**/*` - Web 前端文件

- **文档文件**
  - `*.md` - Markdown 文档
  - `remote/remote-v2/docs/**/*.md` - 项目文档
  - `remote/brain_core/docs/**/*.md` - Brain-Core 文档
  - `README.md` - 项目说明文件

- **脚本文件**
  - `*.sh` - Shell 脚本
  - `remote/remote-v2/scripts/**/*.py` - Python 脚本
  - `remote/remote-v2/scripts/**/*.sh` - Shell 脚本

- **其他文本文件**
  - `*.txt` - 文本文件（除日志文件）
  - `remote/remote-v2/快速使用` - 使用说明
  - `remote/remote-v2/1.txt` - 环境清单

- **模型配置文件（不含模型权重）**
  - `remote/remote-v2/models/**/*.json` - 模型配置文件
  - `remote/remote-v2/models/**/*.md` - 模型说明文档
  - `remote/remote-v2/models/**/*.py` - 模型代码

- **图片文件**
  - `*.png` - PNG 图片（如 `as_norm_distribution.png`, `calibration_result.png`）
  - `*.jpg` / `*.jpeg` - JPG 图片
  - `*.gif` - GIF 图片

- **GitHub 相关**
  - `.github/**/*` - GitHub 配置和说明文件

## ❌ 不会被上传的文件（被 .gitignore 忽略）

### Python 相关
- `__pycache__/` - Python 缓存目录
- `*.pyc`, `*.pyo`, `*.pyd` - Python 编译文件
- `*.so` - 共享库文件
- `build/`, `dist/`, `*.egg-info/` - 构建产物
- `*.egg` - Python 包文件

### 虚拟环境
- `.env`, `.venv`, `venv/`, `env/` - 虚拟环境目录
- `ENV/`, `env.bak/`, `venv.bak/` - 环境备份

### IDE 配置
- `.vscode/` - VS Code 配置
- `.idea/` - IntelliJ IDEA 配置
- `.history/` - 编辑器历史记录目录
- `*.swp`, `*.swo`, `*~` - 编辑器临时文件

### 操作系统文件
- `.DS_Store` - macOS 系统文件
- `Thumbs.db`, `ehthumbs.db` - Windows 缩略图
- `._*` - macOS 资源分支文件

### 日志文件
- `*.log` - 所有日志文件
- `logs/` - 日志目录
- `*.log.*` - 日志轮转文件
- `remote/remote-v2/logs/**/*` - 日志目录

### 音频数据文件
- `*.wav`, `*.mp3`, `*.flac`, `*.aac`, `*.ogg`, `*.m4a` - 音频文件
- `data/audio_samples/` - 音频样本目录
- `data/raw_long_audio/` - 原始长音频目录
- `data/test/` - 测试数据目录
- `data/noise/` - 噪声数据目录
- `data/calibration/` - 校准数据目录（但保留 Python 脚本）

### 模型权重文件
- `*.onnx` - ONNX 模型文件
- `*.pt`, `*.pth` - PyTorch 模型文件
- `*.pkl` - Pickle 序列化文件
- `*.h5` - HDF5 文件
- `*.pb` - TensorFlow 模型文件
- `*.ckpt` - 检查点文件
- `*.bin` - 二进制模型文件
- `*.model`, `*.weights` - 模型权重
- `*.safetensors` - SafeTensors 格式
- `*.tflite` - TensorFlow Lite 模型
- `*.mlmodel` - Core ML 模型
- `*.joblib` - Joblib 序列化文件
- `*.npy`, `*.npz` - NumPy 数组文件

### 项目特定目录
- `faster-whisper/` - Faster-Whisper 目录
- `3D-Speaker/` - 3D-Speaker 目录（但保留源代码）

### 临时文件
- `*.tmp`, `*.temp` - 临时文件
- `temp/`, `tmp/` - 临时目录

### Jupyter Notebook
- `.ipynb_checkpoints/` - Jupyter 检查点

### Node.js
- `node_modules/` - Node.js 依赖
- `npm-debug.log*`, `yarn-debug.log*`, `yarn-error.log*` - 包管理器日志

### Docker
- `.dockerignore` - Docker 忽略文件

### 测试相关
- `.coverage`, `*.cover` - 测试覆盖率文件
- `.pytest_cache/`, `.tox/`, `.cache/` - 测试缓存
- `coverage.xml`, `nosetests.xml` - 测试报告
- `.hypothesis/` - Hypothesis 测试数据

### 文档构建
- `docs/_build/` - 文档构建输出
- `*.pdf` - PDF 文档

### 密钥和证书
- `config/certs/` - 证书目录（但 `server.crt` 可能被上传，需注意）
- `*.key`, `*.pem` - 密钥文件
- `secrets.json` - 密钥配置文件
- `.env.local`, `.env.*.local` - 本地环境变量

### 数据库文件
- `*.db`, `*.sqlite`, `*.sqlite3` - 数据库文件

### Web 上传文件
- `static/uploads/` - 上传文件目录

### 压缩文件
- `*.zip`, `*.tar.gz`, `*.7z`, `*.rar` - 压缩文件

### 运行时目录
- `runtime/` - 运行时目录
- `onnxruntime/` - ONNX Runtime 目录

### 训练产物
- `checkpoints/` - 检查点目录
- `tensorboard/` - TensorBoard 日志
- `wandb/` - Weights & Biases 日志

### 声纹模板
- `speaker_templates/` - 说话人模板目录
- `cohort_targets/` - 队列目标目录

### Hugging Face 缓存
- `*.huggingface/` - Hugging Face 模型目录
- `huggingface_cache/` - Hugging Face 缓存
- `transformers_cache/` - Transformers 缓存

### 实验和输出
- `artifacts/` - 实验产物
- `runs/` - 运行记录
- `experiments/` - 实验目录
- `output/` - 输出目录
- `results/` - 结果目录


## ⚠️ 需要注意的文件

以下文件可能包含敏感信息，上传前请检查：

1. **证书文件**
   - `remote/remote-v2/config/certs/server.crt` - 服务器证书（如果包含敏感信息）

2. **配置文件中的敏感信息**
   - `remote/remote-v2/config/server_config.yaml` - 可能包含服务器地址、端口等
   - `remote/remote-v2/config/model_config.yaml` - 可能包含模型路径等

3. **测试数据**
   - `remote/remote-v2/data/calibration/` 目录下的数据文件（但 Python 脚本会被上传）

## 📊 统计信息

根据 `.gitignore` 规则：

- **会被上传**：源代码、配置文件、文档、脚本、前端资源
- **不会被上传**：模型权重、音频数据、日志、缓存、虚拟环境、构建产物

## 🔍 建议

1. **上传前检查**：使用 `git status` 查看实际会被跟踪的文件
2. **敏感信息**：检查配置文件中是否包含密钥、密码等敏感信息
3. **大文件**：确认没有大文件（>100MB）需要上传，GitHub 有文件大小限制
4. **模型文件**：模型权重文件已被正确忽略，不会上传

## 📝 验证命令

在初始化 Git 仓库后，可以使用以下命令验证：

```bash
# 查看会被跟踪的文件
git ls-files

# 查看被忽略的文件
git status --ignored

# 查看所有文件状态
git status
```
