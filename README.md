# 新闻处理流水线系统

自动下载抖音视频，转换为MP3，转文字，AI总结，并提交到Git。支持多种AI模型（通义千问、OpenAI、本地部署）。

## 功能特性

- 🎬 自动下载抖音视频
- 🎵 MP4转MP3音频转换
- 📝 语音转文字（使用Whisper）
- 🤖 AI智能总结和投资建议
- 📚 自动Git提交和推送
- 🔧 灵活的AI模型配置

## 快速开始

1. 安装依赖：`pip install -r requirements.txt` 和 `sudo apt update && sudo apt install ffmpeg -y`
2. 配置AI模型：编辑 `config.py` 中的相关配置
3. 运行：`python scripts/run_pipeline.py "抖音视频链接"`

## 支持的AI模型

### 1. 通义千问（Qwen）
- 云端API服务
- 需要配置API密钥

### 2. OpenAI
- 云端API服务或本地兼容服务
- 支持自定义API URL
- 可连接本地部署的OpenAI兼容服务（如Ollama）

### 3. 本地模型
- 支持本地部署的Qwen模型
- 支持本地部署的OpenAI兼容服务
- 无需网络连接，保护隐私

## 配置说明

### 编辑 config.py

```python
# AI模型配置
AI_MODEL_TYPE = "qwen"  # 可选：qwen, openai, local

# 通义千问配置
QWEN_API_KEY = "your_qwen_api_key_here"
QWEN_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

# OpenAI配置
OPENAI_API_KEY = "your_openai_api_key_here"
OPENAI_API_URL = "https://api.openai.com/v1"  # 可改为本地服务地址
OPENAI_MODEL = "gpt-3.5-turbo"

# 本地模型配置
LOCAL_MODEL_PATH = "/path/to/your/local/model"
LOCAL_API_URL = "http://127.0.0.1:11434"  # Ollama默认地址
LOCAL_MODEL_NAME = "qwen2.5:7b"
```

### 配置示例

#### 使用通义千问
```python
AI_MODEL_TYPE = "qwen"
QWEN_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

#### 使用OpenAI
```python
AI_MODEL_TYPE = "openai"
OPENAI_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

#### 使用本地Ollama服务
```python
AI_MODEL_TYPE = "local"
LOCAL_API_URL = "http://127.0.0.1:11434"
LOCAL_MODEL_NAME = "qwen2.5:7b"
```

#### 使用本地Qwen模型
```python
AI_MODEL_TYPE = "local"
LOCAL_MODEL_PATH = "/home/user/models/Qwen-1_8B-Chat"
LOCAL_MODEL_NAME = "qwen1.8b"
```

## 使用方法

### 1. 一键运行完整流水线

```bash
python scripts/run_pipeline.py "https://v.douyin.com/xxxxx/"
```

### 2. 完整流程

流水线会自动执行以下步骤：

1. **下载抖音视频** → 保存到 `downloads/` 目录
2. **MP4转MP3** → 自动转换音频格式
3. **语音转文字** → 使用Whisper模型
4. **AI总结** → 根据配置选择AI模型
5. **Git提交** → 自动提交到仓库

### 3. 分步运行

```bash
# 步骤1：下载视频
python scripts/douyin_download.py --url "your_douyin_url"

# 步骤2：转文字
python scripts/mp3_2_txt.py --timestamp 20250812-0456

# 步骤3：AI总结（选择一种）
python scripts/qwen_news_summary.py --timestamp 20250812-0456
# 或者
python scripts/openai_news_summary.py --timestamp 20250812-0456 --local

# 步骤4：Git提交
python scripts/git_commit.py
```

### 4. 手动指定时间戳

```bash
timestamp=$(date +"%Y%m%d-%H%M")
python scripts/mp3_2_txt.py --timestamp $timestamp
python scripts/qwen_news_summary.py --timestamp $timestamp
```

## 本地模型部署

### 1. 使用Ollama

```bash
# 安装Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 下载模型
ollama pull qwen2.5:7b

# 启动服务
ollama serve
```

### 2. 使用本地Qwen模型

```bash
# 下载模型到本地
git clone https://github.com/QwenLM/Qwen-VL.git
cd Qwen-VL

# 安装依赖
pip install -r requirements.txt

# 运行本地服务
python -m transformers.models.qwen_vl.qwen_vl_chat --model-path /path/to/model
```

### 3. vLLM + 开源模型

```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2-7B-Instruct --host 0.0.0.0 --port 8000
```

## 工作流程

1. 下载抖音视频 → MP4文件
2. MP4转MP3 → 使用ffmpeg
3. MP3转文字 → 支持时间戳，自动错别字校验
4. AI总结 → 生成投资建议（多种模型选择）
5. Git提交 → 自动提交到仓库

## 文件结构

```
news_summary/
├── scripts/                    # 核心脚本
│   ├── run_pipeline.py        # 完整流水线
│   ├── douyin_download.py     # 下载抖音视频
│   ├── mp3_2_txt.py          # MP3转文字（含错别字校验）
│   ├── qwen_news_summary.py   # 通义千问AI总结
│   ├── openai_news_summary.py # OpenAI AI总结
│   └── git_commit.py          # Git提交
├── config.py                   # 配置文件
├── requirements.txt            # 依赖
└── .github/workflows/          # GitHub Actions
```

## 输出文件

- **音频文件**: `downloads/` 目录
- **文字文件**: `news/` 目录（格式：`YYYYMMDD-HHMM.txt`）
- **总结文件**: `news/` 目录（格式：`YYYYMMDD-HHMM_标题.md`）
- **音频切片**: `segments/` 目录

## 注意事项

1. **API密钥安全**: 不要在代码中硬编码API密钥，使用环境变量或配置文件
2. **网络连接**: 云端模型需要稳定的网络连接
3. **本地资源**: 本地模型需要足够的计算资源（GPU推荐）
4. **文件权限**: 确保脚本有读写权限
5. **依赖安装**: 确保所有Python包已正确安装

## 故障排除

### 常见问题

1. **API调用失败**: 检查API密钥和网络连接
2. **本地模型无法启动**: 检查模型路径和服务状态
3. **文件权限错误**: 检查目录权限
4. **依赖缺失**: 运行 `pip install -r requirements.txt`

### 调试模式

在脚本中添加 `--verbose` 参数可以获取更详细的输出信息。

## GitHub Actions

在仓库设置中添加 `QWEN_API_KEY` secret，然后在Actions页面手动触发工作流。

## 更新日志

- v2.0: 支持多种AI模型选择，配置集中化管理
- v1.0: 基础流水线功能

## 技术支持

如有问题，请检查：
1. 配置文件是否正确
2. 依赖是否完整安装
3. 网络连接是否正常
4. 模型服务是否启动 