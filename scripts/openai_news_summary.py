#!/usr/bin/env python3
"""
AI新闻总结工具 - 支持OpenAI API和本地部署
支持自定义API URL，可连接本地部署的OpenAI兼容服务
"""

import requests
import json
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import time

# ===== 配置 =====
# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from config import NEWS_DIR, OUTPUT_DIR, SUMMARY_PROMPT
    NEWS_DIR = Path(NEWS_DIR)
    OUTPUT_DIR = Path(OUTPUT_DIR)
except ImportError:
    print("❌ 无法导入配置文件，请确保config.py存在")
    sys.exit(1)

# OpenAI默认配置
DEFAULT_OPENAI_API_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-3.5-turbo"

def call_openai_api(prompt, api_key, api_url=None, model=None):
    """调用OpenAI API或本地兼容服务"""
    if not api_url:
        api_url = DEFAULT_OPENAI_API_URL
    
    if not model:
        model = DEFAULT_MODEL
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 2000,
        "temperature": 0.7
    }
    
    try:
        print(f"🌐 正在调用API: {api_url}")
        print(f"🤖 使用模型: {model}")
        
        response = requests.post(f"{api_url}/chat/completions", headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        # 添加调试信息
        print(f"🔍 API响应状态码: {response.status_code}")
        print(f"🔍 响应键: {list(result.keys())}")
        
        # 检查响应结构
        if "choices" in result and len(result["choices"]) > 0:
            if "message" in result["choices"][0]:
                content = result["choices"][0]["message"]["content"]
                print(f"✅ 成功获取回复，长度: {len(content)} 字符")
                return content
            else:
                print(f"❌ 响应中缺少 'message' 字段")
                print(f"🔍 choices[0] 内容: {result['choices'][0]}")
                return None
        else:
            print(f"❌ 响应结构不符合预期")
            print(f"🔍 完整响应内容: {result}")
            return None
            
    except Exception as e:
        print(f"❌ API调用失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"🔍 错误响应内容: {e.response.text}")
        return None

def call_local_openai_compatible(prompt, api_url, model=None):
    """调用本地OpenAI兼容服务"""
    print(f"🏠 正在使用本地OpenAI兼容服务: {api_url}")
    
    # 尝试不同的认证方式
    api_keys_to_try = [
        os.environ.get('OPENAI_API_KEY'),
        os.environ.get('LOCAL_AI_KEY'),
        "sk-local-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",  # 本地服务常用
        "dummy-key"  # 某些本地服务不需要真实key
    ]
    
    for api_key in api_keys_to_try:
        if not api_key:
            continue
            
        print(f"🔑 尝试API密钥: {api_key[:10]}...")
        result = call_openai_api(prompt, api_key, api_url, model)
        if result:
            return result
    
    print("❌ 所有API密钥都失败")
    return None

def extract_title_from_summary(summary_content):
    """从AI生成的内容中提取标题"""
    if not summary_content:
        return None
    
    # 按行分割
    lines = summary_content.strip().split('\n')
    
    # 查找第一行非空内容作为标题
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('---'):
            # 移除可能的markdown格式
            title = line.strip('*# `')
            return title
    
    return None

def process_news_file(news_file_path, api_key=None, api_url=None, model=None, use_local=False):
    """处理新闻文件，生成总结和投资建议"""
    print(f"📖 正在处理新闻文件: {news_file_path.name}")
    
    # 读取新闻内容
    try:
        with open(news_file_path, "r", encoding="utf-8") as f:
            news_content = f.read()
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return None
    
    # 构建提示词
    print(f"📝 新闻内容长度: {len(news_content)} 字符")
    print(f"📝 新闻内容预览: {news_content[:100]}...")
    print(f"📝 SUMMARY_PROMPT 长度: {len(SUMMARY_PROMPT)} 字符")
    
    prompt = SUMMARY_PROMPT.format(news_content=news_content)
    print(f"📝 最终提示词长度: {len(prompt)} 字符")
    print(f"📝 提示词预览: {prompt[:200]}...")
    
    # 选择调用方式
    if use_local:
        print("🏠 本地模式...")
        result = call_local_openai_compatible(prompt, api_url, model)
    else:
        print("☁️ 云端API模式...")
        if not api_key:
            print("❌ 云端模式需要设置OPENAI_API_KEY")
            return None
        result = call_openai_api(prompt, api_key, api_url, model)
    
    if result:
        return result
    else:
        return None

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='AI新闻总结工具 - 支持OpenAI API和本地部署')
    parser.add_argument('--timestamp', '-t', 
                       help='指定时间戳 (格式: YYYYMMDD-HHMM)，如果不指定则自动查找最新文件')
    parser.add_argument('--news-file', '-f',
                       help='指定新闻文件路径，如果不指定则自动查找最新文件')
    parser.add_argument('--output-dir', '-o',
                       help=f'输出目录 (默认: {OUTPUT_DIR})')
    parser.add_argument('--api-key', '-k',
                       help='OpenAI API密钥 (如果不指定，会尝试环境变量)')
    parser.add_argument('--api-url', '-u',
                       help=f'OpenAI API URL (默认: {DEFAULT_OPENAI_API_URL})')
    parser.add_argument('--model', '-m',
                       help=f'模型名称 (默认: {DEFAULT_MODEL})')
    parser.add_argument('--local', '-l', action='store_true',
                       help='使用本地OpenAI兼容服务')
    
    args = parser.parse_args()
    
    print("🚀 开始处理新闻文件...")
    
    # 获取API配置
    api_key = args.api_key or os.environ.get('OPENAI_API_KEY')
    api_url = args.api_url or os.environ.get('OPENAI_API_URL') or DEFAULT_OPENAI_API_URL
    model = args.model or os.environ.get('OPENAI_MODEL') or DEFAULT_MODEL
    
    # 检查配置
    if args.local:
        print("🏠 本地模式")
        if not api_url or api_url == DEFAULT_OPENAI_API_URL:
            print("⚠️  本地模式建议指定自定义API URL")
            print("💡 例如: --api-url http://localhost:8000/v1")
    else:
        print("☁️ 云端API模式")
        if not api_key:
            print("❌ 请设置OpenAI API密钥")
            print("💡 设置方法:")
            print("   1. 命令行参数: --api-key 'your_key'")
            print("   2. 环境变量: export OPENAI_API_KEY='your_key'")
            print("   3. 或者使用 --local 参数使用本地服务")
            return
    
    # 设置输出目录
    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    output_dir.mkdir(exist_ok=True)
    
    # 确定要处理的新闻文件
    news_file_path = None
    timestamp = None
    
    if args.news_file:
        # 使用指定的新闻文件
        news_file_path = Path(args.news_file)
        if not news_file_path.exists():
            print(f"❌ 指定的新闻文件不存在: {news_file_path}")
            return
        # 从文件名提取时间戳
        timestamp = news_file_path.stem
        print(f"📰 使用指定的新闻文件: {news_file_path.name}")
    elif args.timestamp:
        # 使用指定的时间戳查找文件
        timestamp = args.timestamp
        news_file_path = NEWS_DIR / f"{timestamp}.txt"
        if not news_file_path.exists():
            print(f"❌ 未找到时间戳为 {timestamp} 的新闻文件")
            return
        print(f"📰 使用指定时间戳的新闻文件: {news_file_path.name}")
    else:
        # 自动查找最新的新闻文件
        news_files = list(NEWS_DIR.glob("*.txt"))
        if not news_files:
            print("❌ 未找到新闻文件，请先运行mp3_2_txt.py")
            return
        
        # 按修改时间排序，获取最新的文件
        news_file_path = max(news_files, key=lambda x: x.stat().st_mtime)
        timestamp = news_file_path.stem  # 去掉.txt后缀
        print(f"📰 找到最新新闻文件: {news_file_path.name}")
    
    # 处理新闻文件
    summary_content = process_news_file(
        news_file_path, 
        api_key=api_key,
        api_url=api_url,
        model=model,
        use_local=args.local
    )
    
    if summary_content:
        # 从AI生成的内容中提取标题
        title = extract_title_from_summary(summary_content)
        if title:
            # 清理标题，移除特殊字符，用于文件名
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_')
            output_file = output_dir / f"{timestamp}_{safe_title}.md"
            print(f"📝 AI生成的标题: {title}")
            print(f"📁 安全文件名: {safe_title}")
        else:
            # 如果无法提取标题，使用默认名称
            output_file = output_dir / f"{timestamp}_AI总结.md"
            print(f"⚠️  无法提取标题，使用默认文件名")
        
        # 保存总结文件
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(summary_content)
            
            print(f"✅ 总结已保存到: {output_file}")
            
            # 显示文件大小
            file_size = output_file.stat().st_size
            print(f"📊 文件大小: {file_size} 字节")
            
            # 显示文件内容预览
            print("\n📋 总结内容预览:")
            print("=" * 50)
            preview = summary_content[:500]
            print(preview + "..." if len(summary_content) > 500 else summary_content)
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ 保存总结文件失败: {e}")
            return
    else:
        print("❌ 生成总结失败")

if __name__ == "__main__":
    main() 