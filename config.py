# -*- coding: utf-8 -*-
"""
配置文件
请在此文件中设置您的API密钥和其他配置
"""

# 通义千问API配置
QWEN_API_KEY = "your_qwen_api_key_here"  # 请替换为您的实际API密钥
QWEN_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

# 文件路径配置
AUDIO_PATH = "downloads/audio.mp3"  # 输入MP3文件路径
SEGMENT_DIR = "segments"  # 音频切片目录
OUTPUT_DIR = "news"  # 输出目录
NEWS_DIR = "news"  # 新闻文件目录

# 音频处理配置
SEGMENT_SECONDS = 65  # 每段音频长度（秒）
MODEL_NAME = "base"   # Whisper模型名称，可选：tiny, base, small, medium, large

# Git配置
GIT_AUTO_COMMIT = True  # 是否自动提交到Git
GIT_AUTO_PUSH = True    # 是否自动推送到远程仓库

# 提示词配置
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

然后空一行，再开始正式的markdown内容。

**原始新闻内容（请自动纠正错误）：**
{news_content}

请确保输出格式清晰，内容专业，投资建议要具体可行。""" 