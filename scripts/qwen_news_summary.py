#!/usr/bin/env python3
"""
AI新闻总结工具 - 支持通义千问API和本地模型
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
    from config import QWEN_API_KEY, QWEN_API_URL, NEWS_DIR, OUTPUT_DIR, SUMMARY_PROMPT
    NEWS_DIR = Path(NEWS_DIR)
    OUTPUT_DIR = Path(OUTPUT_DIR)
except ImportError:
    print("❌ 无法导入配置文件，请确保config.py存在")
    sys.exit(1)

def call_qwen_api(prompt, api_key):
    """调用通义千问API"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "qwen-turbo",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        },
        "parameters": {
            "max_tokens": 2000,
            "temperature": 0.7
        }
    }
    
    try:
        response = requests.post(QWEN_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        # 添加调试信息
        print(f"🔍 API响应状态码: {response.status_code}")
        print(f"🔍 API响应内容: {result}")
        
        # 检查响应结构 - 支持通义千问API格式
        print(f"🔍 响应键: {list(result.keys())}")
        
        # 通义千问API格式：result["output"]["text"]
        if "output" in result and "text" in result["output"]:
            print(f"✅ 找到通义千问API响应格式")
            return result["output"]["text"]
        
        # 备用格式：result["output"]["choices"][0]["message"]["content"]
        elif "output" in result and "choices" in result["output"]:
            if len(result["output"]["choices"]) > 0:
                if "message" in result["output"]["choices"][0]:
                    return result["output"]["choices"][0]["message"]["content"]
                else:
                    print(f"❌ 响应中缺少 'message' 字段")
                    print(f"🔍 choices[0] 内容: {result['output']['choices'][0]}")
                    return None
            else:
                print(f"❌ 响应中 'choices' 数组为空")
                return None
        
        # 其他可能的格式
        elif "choices" in result:
            if len(result["choices"]) > 0:
                if "message" in result["choices"][0]:
                    return result["choices"][0]["message"]["content"]
                elif "text" in result["choices"][0]:
                    return result["choices"][0]["text"]
                else:
                    print(f"❌ 响应中缺少 'message' 或 'text' 字段")
                    print(f"🔍 choices[0] 内容: {result['choices'][0]}")
                    return None
            else:
                print(f"❌ 响应中 'choices' 数组为空")
                return None
        
        # 直接文本格式
        elif "text" in result:
            return result["text"]
        elif "content" in result:
            return result["content"]
        elif "message" in result:
            return result["message"]
        
        else:
            print(f"❌ 响应结构不符合预期")
            print(f"🔍 完整响应内容: {result}")
            return None
            
    except Exception as e:
        print(f"❌ API调用失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"🔍 错误响应内容: {e.response.text}")
        return None

def call_local_model(prompt, model_path=None):
    """调用本地模型（支持多种格式）"""
    print("🏠 正在使用本地模型...")
    
    try:
        # 尝试导入transformers
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
        except ImportError:
            print("❌ 请安装transformers: pip install transformers torch")
            return None
        
        # 如果没有指定模型路径，使用默认的Qwen模型
        if not model_path:
            model_path = "Qwen/Qwen-1_8B-Chat"  # 默认使用较小的模型
        
        print(f"🤖 加载本地模型: {model_path}")
        
        # 加载tokenizer和模型
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_path, 
            trust_remote_code=True,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        
        # 构建对话格式
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
        # 生成回复
        print("🔄 正在生成回复...")
        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=2048,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # 解码回复
        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        
        print("✅ 本地模型生成完成")
        return response.strip()
        
    except Exception as e:
        print(f"❌ 本地模型调用失败: {e}")
        print("💡 请确保已安装必要的依赖包")
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

def process_news_file(news_file_path, api_key=None, use_local=False, local_model_path=None):
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
        print("🏠 使用本地模型...")
        result = call_local_model(prompt, local_model_path)
    else:
        print("☁️ 使用通义千问API...")
        if not api_key:
            print("❌ 使用API模式需要设置QWEN_API_KEY")
            return None
        result = call_qwen_api(prompt, api_key)
    
    if result:
        return result
    else:
        return None

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='AI新闻总结工具 - 支持API和本地模型')
    parser.add_argument('--timestamp', '-t', 
                       help='指定时间戳 (格式: YYYYMMDD-HHMM)，如果不指定则自动查找最新文件')
    parser.add_argument('--news-file', '-f',
                       help='指定新闻文件路径，如果不指定则自动查找最新文件')
    parser.add_argument('--output-dir', '-o',
                       help=f'输出目录 (默认: {OUTPUT_DIR})')
    parser.add_argument('--local', '-l', action='store_true',
                       help='使用本地模型而不是API')
    parser.add_argument('--model-path', '-m',
                       help='本地模型路径 (默认: Qwen/Qwen-1_8B-Chat)')
    
    args = parser.parse_args()
    
    print("🚀 开始处理新闻文件...")
    
    # 检查配置
    if args.local:
        print("🏠 本地模型模式")
        api_key = None
    else:
        print("☁️ API模式")
        # 检查API密钥（优先从环境变量读取）
        api_key = os.environ.get('QWEN_API_KEY') or QWEN_API_KEY
        if api_key == "your_qwen_api_key_here":
            print("❌ 请设置QWEN_API_KEY环境变量或在config.py中配置")
            print("💡 设置方法:")
            print("   1. 环境变量: export QWEN_API_KEY='your_key_here'")
            print("   2. 配置文件: 编辑config.py中的QWEN_API_KEY")
            print("   3. 或者使用 --local 参数使用本地模型")
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
        use_local=args.local, 
        local_model_path=args.model_path
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