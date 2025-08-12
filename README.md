# 新闻处理流水线系统

自动下载抖音视频，转换为MP3，转文字，AI总结，并提交到Git。支持多种AI模型（通义千问、OpenAI、本地部署）。

## 快速开始

1. 安装依赖：`pip install -r requirements.txt`
2. 设置API密钥：编辑 `config.py` 中的 `QWEN_API_KEY`
3. 运行：`python scripts/run_pipeline.py`

## 功能

- 下载抖音视频（MP4格式）
- MP4转MP3（使用ffmpeg）
- MP3转文字（支持时间戳参数，自动错别字校验）
- AI总结和投资建议（支持多种模型）
- 自动Git提交

## 支持的AI模型

### 通义千问API
```bash
python scripts/qwen_news_summary.py --timestamp 20250812-0456
```

### OpenAI API
```bash
python scripts/openai_news_summary.py --timestamp 20250812-0456
```

### 本地模型部署
```bash
# 通义千问本地模型
python scripts/qwen_news_summary.py --timestamp 20250812-0456 --local

# OpenAI兼容本地服务
python scripts/openai_news_summary.py --timestamp 20250812-0456 --local --api-url http://localhost:8000/v1
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

## 使用方法

### 一键运行完整流水线
```bash
python scripts/run_pipeline.py
```

### 分步运行
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

### 手动指定时间戳
```bash
timestamp=$(date +"%Y%m%d-%H%M")
python scripts/mp3_2_txt.py --timestamp $timestamp
python scripts/qwen_news_summary.py --timestamp $timestamp
```

## 本地模型部署

### vLLM + 开源模型
```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2-7B-Instruct --host 0.0.0.0 --port 8000
```

### Ollama
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2:7b
ollama serve
```

## GitHub Actions

在仓库设置中添加 `QWEN_API_KEY` secret，然后在Actions页面手动触发工作流。 