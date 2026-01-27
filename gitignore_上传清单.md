# .gitignore 上传清单

## ⚠️ 重要说明：.gitignore 工作原理

**目录忽略规则**：当一个目录被添加到 `.gitignore` 时，该目录下的**所有文件和子目录**都会被忽略。

- `faster-whisper/` → 该目录下的所有内容都不会上传
- `3D-Speaker/` → 该目录下的所有内容都不会上传

**即使文件本身没有被其他规则忽略，只要它在被忽略的目录下，也不会上传。**

## 修改说明
根据用户需求，对 `.gitignore` 文件进行了以下修改：

### 移除的忽略规则（现在会上传）
- `data/vector_db/` - 向量数据库目录
- `models/` - 模型目录

### 添加的忽略规则（现在不会上传）
- `faster-whisper/` - Faster Whisper 项目目录
- `3D-Speaker/` - 3D Speaker 项目目录

## 当前项目目录结构及上传状态

### 项目根目录结构
```
/home/swufe/Project/zhoulonghao/
├── ✅ gitignore_上传清单.md          # 会上传 (新创建的文档)
├── ❌ faster-whisper/                 # 不会上传 (新忽略规则)
│   ├── ❌ backend/                     # 不会上传
│   ├── ❌ config/                      # 不会上传
│   ├── ❌ data/                        # 不会上传
│   ├── ❌ docs/                        # 不会上传
│   ├── ❌ logs/                        # 不会上传
│   ├── ❌ README.md                    # 不会上传
│   ├── ❌ requirements.txt             # 不会上传
│   ├── ❌ run_asr.sh                   # 不会上传
│   └── ❌ scripts/                     # 不会上传
├── ✅ remote/                         # 会上传
│   ├── ✅ 1.html                      # 会上传
│   ├── ❌ 3D-Speaker/                 # 不会上传 (新忽略规则)
│   │   ├── ❌ docs/                    # 不会上传
│   │   ├── ❌ egs/                     # 不会上传
│   │   ├── ❌ LICENSE                  # 不会上传
│   │   ├── ❌ README.md                # 不会上传
│   │   ├── ❌ requirements.txt         # 不会上传
│   │   ├── ❌ runtime/                 # 不会上传
│   │   └── ❌ speakerlab/              # 不会上传
│   ├── ✅ brain_core/                 # 会上传
│   ├── ✅ remote-v2/                  # 会上传
│   │   ├── ✅ 1.txt                   # 会上传
│   │   ├── ✅ as_norm_distribution.png # 会上传
│   │   ├── ✅ backend/                # 会上传
│   │   │   ├── ✅ __init__.py
│   │   │   ├── ❌ __pycache__/        # 不会上传 (默认忽略)
│   │   │   ├── ✅ api/
│   │   │   ├── ✅ common/
│   │   │   ├── ✅ controller/
│   │   │   ├── ✅ core/
│   │   │   ├── ✅ data/
│   │   │   ├── ✅ models/             # 会上传 (移除忽略)
│   │   │   │   ├── ✅ __init__.py
│   │   │   │   ├── ❌ __pycache__/    # 不会上传 (默认忽略)
│   │   │   │   ├── ✅ speaker/
│   │   │   │   └── ✅ vad/
│   │   │   ├── ✅ modules/
│   │   │   ├── ✅ pipeline/
│   │   │   ├── ✅ scheduler/
│   │   │   ├── ✅ schema/
│   │   │   ├── ✅ service/
│   │   │   ├── ✅ training/
│   │   │   └── ✅ utils/
│   │   ├── ✅ calibration_result.png  # 会上传
│   │   ├── ✅ config/                 # 会上传
│   │   ├── ✅ data/                   # 会上传
│   │   │   ├── ❌ audio_samples/      # 不会上传 (默认忽略)
│   │   │   ├── ❌ calibration/        # 不会上传 (默认忽略)
│   │   │   ├── ❌ noise/              # 不会上传 (默认忽略)
│   │   │   ├── ✅ prepare_cohort_targets.py # 会上传
│   │   │   ├── ❌ raw_long_audio/     # 不会上传 (默认忽略)
│   │   │   ├── ❌ test/               # 不会上传 (默认忽略)
│   │   │   └── ✅ vector_db/          # 会上传 (移除忽略)
│   │   │       ├── ✅ cohort.npy      # 会上传
│   │   │       ├── ✅ users.pkl       # 会上传
│   │   │       └── ✅ vectors/        # 会上传 (空目录)
│   │   ├── ✅ docs/                   # 会上传
│   │   ├── ✅ logs/                   # 会上传 (但日志文件会被忽略)
│   │   ├── ❌ models/                 # 不会上传 (根目录models忽略规则)
│   │   ├── ✅ README.md               # 会上传
│   │   ├── ✅ requirements.txt        # 会上传
│   │   ├── ✅ scripts/                # 会上传
│   │   ├── ✅ snorm_calibration_result.png # 会上传
│   │   ├── ✅ tests/                  # 会上传
│   │   ├── ✅ web/                    # 会上传
│   │   ├── ✅ 快速使用               # 会上传
│   │   └── ✅ 识别结果               # 会上传
│   └── ✅ 多模态业务编排系统 实施方案书.md # 会上传
└── ✅ SMP/                            # 会上传
    ├── ✅ backend/
    ├── ✅ frontend/
    ├── ✅ README.md
    ├── ✅ requirements.txt
    ├── ✅ scripts/
    ├── ✅ tests/
    ├── ✅ 快速使用
    └── ✅ 迁移方案.md
```

### 📊 上传状态统计

#### ✅ 会上传的目录 (主要变更)
**向量数据库目录 (新增上传):**
```
remote/remote-v2/data/vector_db/        # 向量数据库 (~2.8MB)
├── cohort.npy                        # 群组向量数据 (2.8MB)
├── users.pkl                         # 用户数据文件 (~2.5KB)
└── vectors/                          # 向量存储目录 (空)
```

**模型代码目录 (新增上传):**
```
remote/remote-v2/backend/models/       # 模型相关代码
├── __init__.py                       # 模型包初始化
├── speaker/                          # 说话人识别模型代码
└── vad/                              # 语音活动检测模型代码
```

#### ❌ 不会上传的目录 (新忽略规则)
**完整项目目录 (新增忽略 - 包括所有子文件):**
```
faster-whisper/                        # Faster Whisper 项目 (完整独立项目)
├── backend/                          # 后端代码 - 不会上传
├── config/                           # 配置文件 - 不会上传
├── data/                             # 数据目录 - 不会上传
├── docs/                             # 文档 - 不会上传
├── logs/                             # 日志 - 不会上传
├── README.md                         # 说明文档 - 不会上传
├── requirements.txt                  # 依赖文件 - 不会上传
├── run_asr.sh                        # 运行脚本 - 不会上传
└── scripts/                          # 脚本目录 - 不会上传

3D-Speaker/                           # 3D Speaker 项目 (完整独立项目)
├── docs/                             # 文档 - 不会上传
├── egs/                              # 示例 - 不会上传
├── LICENSE                           # 许可证 - 不会上传
├── README.md                         # 说明文档 - 不会上传
├── requirements.txt                  # 依赖文件 - 不会上传
├── runtime/                          # 运行时文件 - 不会上传
└── speakerlab/                       # 说话人实验室代码 - 不会上传
```</xai:function_call">### ❌ 新增忽略的完整项目 (所有文件都不会上传)
1. **Faster Whisper 项目** (完整项目):
   - `faster-whisper/` 下的所有文件和目录
   - 包括 README.md, requirements.txt, run_asr.sh 等所有文件

2. **3D Speaker 项目** (完整项目):
   - `remote/3D-Speaker/` 下的所有文件和目录
   - 包括 LICENSE, README.md, requirements.txt 等所有文件

## 其他默认忽略规则（仍不会上传）

### 🔍 默认忽略的文件类型
以下类型的文件仍然会被 `.gitignore` 忽略：

#### Python 相关
- `__pycache__/` - Python 缓存目录
- `*.py[cod]` - Python 编译文件
- `*$py.class` - Python 类文件
- `*.so` - Python 扩展文件
- 各种 Python 包文件 (`.egg-info/`, `dist/`, `build/` 等)

#### 虚拟环境
- `.env`, `.venv` - 环境配置文件
- `env/`, `venv/`, `ENV/` - 虚拟环境目录

#### IDE 和编辑器文件
- `.vscode/`, `.idea/` - IDE 配置
- `*.swp`, `*.swo` - Vim 交换文件
- `*~` - 备份文件

#### 日志和调试文件
- `*.log` - 日志文件
- `logs/` - 日志目录

#### 数据和媒体文件
- `*.wav`, `*.mp3`, `*.flac` 等音频文件
- `data/audio_samples/` - 音频样本
- `data/raw_long_audio/` - 原始音频
- `data/test/` - 测试数据
- `data/noise/` - 噪音数据
- `data/calibration/` - 校准数据

#### 模型和权重文件
- `*.onnx`, `*.pt`, `*.pth`, `*.pkl` - 模型文件
- `*.h5`, `*.pb`, `*.ckpt` - 其他模型格式
- `*.bin`, `*.model`, `*.weights` - 二进制模型
- `*.safetensors`, `*.tflite`, `*.mlmodel` - 特定格式模型

#### 临时和缓存文件
- `*.tmp`, `*.temp` - 临时文件
- `temp/`, `tmp/` - 临时目录
- `.cache`, `.pytest_cache/` - 缓存目录

#### 数据库和存储文件
- `*.db`, `*.sqlite`, `*.sqlite3` - 数据库文件

#### 大文件和压缩包
- `*.tar.gz`, `*.zip`, `*.7z`, `*.rar` - 压缩文件

#### 运行时和训练产物
- `runtime/`, `onnxruntime/` - 运行时文件
- `checkpoints/`, `tensorboard/`, `wandb/` - 训练产物
- `speaker_templates/`, `cohort_targets/` - 说话人模板

### 📋 当前项目中被默认规则忽略的具体文件

#### 在当前项目结构中被忽略的文件/目录：
```
remote/remote-v2/backend/__pycache__/           # Python 缓存
remote/remote-v2/backend/models/__pycache__/   # Python 缓存
remote/remote-v2/data/audio_samples/           # 音频样本数据
remote/remote-v2/data/raw_long_audio/          # 原始音频数据
remote/remote-v2/data/test/                    # 测试数据
remote/remote-v2/data/noise/                   # 噪音数据
remote/remote-v2/data/calibration/             # 校准数据
```

## 📈 最终总结

### ✅ 上传到 Git 的文件 (新增)
1. **向量数据库文件** (~2.8MB):
   - `remote/remote-v2/data/vector_db/cohort.npy`
   - `remote/remote-v2/data/vector_db/users.pkl`

2. **模型代码文件**:
   - `remote/remote-v2/backend/models/` 目录下所有代码文件
   - 说话人识别和语音活动检测相关代码

### ❌ 不上传到 Git 的文件 (新增忽略 - 完整项目)
1. **Faster Whisper 项目** (完整项目):
   - `faster-whisper/` 目录下的所有文件和子目录
   - 包括 `README.md`, `requirements.txt`, `run_asr.sh` 等所有文件

2. **3D Speaker 项目** (完整项目):
   - `remote/3D-Speaker/` 目录下的所有文件和子目录
   - 包括 `LICENSE`, `README.md`, `requirements.txt` 等所有文件

### 🔄 保持不变的规则
- 所有默认忽略规则保持不变
- 其他项目文件正常上传
- Python 缓存、日志、大文件等仍被忽略

### 💾 存储空间影响
- **新增上传**: ~2.8MB (主要是向量数据库)
- **减少上传**: 两个完整项目目录 (Faster Whisper + 3D Speaker)
- **净影响**: 大幅减少仓库大小，避免上传重复的项目代码
