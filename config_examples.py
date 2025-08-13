# -*- coding: utf-8 -*-
"""
配置文件示例
复制此文件为 config.py 并根据需要修改配置
"""

# ===== AI模型配置 =====
# 支持的模型类型：qwen, openai, local
AI_MODEL_TYPE = "qwen"  # 可选：qwen, openai, local

# ===== 通义千问配置 =====
QWEN_API_KEY = "your_qwen_api_key_here"  # 请替换为您的实际API密钥
QWEN_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

# ===== OpenAI配置 =====
OPENAI_API_KEY = "your_openai_api_key_here"  # 请替换为您的实际API密钥
OPENAI_API_URL = "https://api.openai.com/v1"  # 可改为本地服务地址，如 http://127.0.0.1:11434/v1
OPENAI_MODEL = "gpt-3.5-turbo"  # 模型名称

# ===== 本地模型配置 =====
LOCAL_MODEL_PATH = "/path/to/your/local/model"  # 本地模型路径
LOCAL_API_URL = "http://127.0.0.1:11434"  # 本地API服务地址（Ollama默认地址）
LOCAL_MODEL_NAME = "qwen2.5:7b"  # 本地模型名称

# ===== 文件路径配置 =====
AUDIO_PATH = ""  # 输入MP3文件路径
SEGMENT_DIR = "segments"  # 音频切片目录
OUTPUT_DIR = "news"  # 输出目录
NEWS_DIR = "news"  # 新闻文件目录

# ===== 音频处理配置 =====
SEGMENT_SECONDS = 65  # 每段音频长度（秒）
MODEL_NAME = "base"   # Whisper模型名称，可选：tiny, base, small, medium, large

# ===== Git配置 =====
GIT_AUTO_COMMIT = True  # 是否自动提交到Git
GIT_AUTO_PUSH = True    # 是否自动推送到远程仓库

# ===== 提示词配置 =====
SUMMARY_PROMPT = """请分析以下新闻内容，由于这是语音转文字的结果，可能存在同音字错误。分析后并提供：

**内容分析**
请提供：

1. 新闻摘要（200字以内）
2. 关键信息提取
3. 投资建议和风险提示
4. 相关行业影响分析

请用markdown格式输出，标题要简洁明了。

**重要要求**：请在回答的第一行单独写一个简洁的标题（不要包含markdown格式符号），例如：
摩根大通经济分析报告
高盛房地产行业分析报告
经济政策影响评估

然后空一行，再开始正式的markdown内容,不需要以 ```markdown 开头和结尾。

**原始新闻内容（请自动纠正错误）：**
{news_content}

请确保输出格式清晰，内容专业，投资建议要具体可行。"""

# ===== 配置示例 =====

# 示例1：使用通义千问
"""
AI_MODEL_TYPE = "qwen"
QWEN_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
"""

# 示例2：使用OpenAI
"""
AI_MODEL_TYPE = "openai"
OPENAI_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
"""

# 示例3：使用本地Ollama服务
"""
AI_MODEL_TYPE = "local"
LOCAL_API_URL = "http://127.0.0.1:11434"
LOCAL_MODEL_NAME = "qwen2.5:7b"
"""

# 示例4：使用本地Qwen模型
"""
AI_MODEL_TYPE = "local"
LOCAL_MODEL_PATH = "/home/user/models/Qwen-1_8B-Chat"
LOCAL_MODEL_NAME = "qwen1.8b"
""" 