#!/usr/bin/env python3
"""
新闻处理流水线主控制脚本
按顺序执行：下载抖音视频 -> 转MP3 -> 转文字 -> AI总结 -> Git提交
支持多种AI模型：通义千问、OpenAI、本地模型
"""

import subprocess
import sys
from pathlib import Path
import time
from datetime import datetime
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from config import AI_MODEL_TYPE, QWEN_API_KEY, OPENAI_API_KEY, LOCAL_API_URL, LOCAL_MODEL_NAME
except ImportError:
    print("❌ 无法导入配置文件，请确保config.py存在")
    sys.exit(1)

def run_script(script_name, description, args=None):
    """运行指定的Python脚本"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        print(f"❌ 脚本不存在: {script_path}")
        return False
    
    try:
        # 构建命令
        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)
        
        print(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        print(f"✅ {description} 完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失败: {e}")
        return False

def check_prerequisites():
    """检查前置条件"""
    print("🔍 检查前置条件...")
    
    # 检查必要的目录
    required_dirs = ["downloads", "segments", "news"]
    for dir_name in required_dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"✅ 目录 {dir_name} 已准备")
    
    # 检查必要的脚本
    required_scripts = [
        "douyin_download.py",
        "mp3_2_txt.py", 
        "qwen_news_summary.py",
        "openai_news_summary.py",
        "git_commit.py"
    ]
    
    for script in required_scripts:
        script_path = Path(__file__).parent / script
        if not script_path.exists():
            print(f"❌ 缺少必要脚本: {script}")
            return False
    
    print("✅ 所有前置条件检查通过")
    return True

def check_ai_model_config():
    """检查AI模型配置"""
    print(f"🤖 检查AI模型配置...")
    print(f"当前配置的模型类型: {AI_MODEL_TYPE}")
    
    if AI_MODEL_TYPE == "qwen":
        if QWEN_API_KEY == "your_qwen_api_key_here":
            print("⚠️  警告: 通义千问API密钥未配置，请修改config.py")
        else:
            print("✅ 通义千问配置正常")
    elif AI_MODEL_TYPE == "openai":
        if OPENAI_API_KEY == "your_openai_api_key_here":
            print("⚠️  警告: OpenAI API密钥未配置，请修改config.py")
        else:
            print("✅ OpenAI配置正常")
    elif AI_MODEL_TYPE == "local":
        print(f"✅ 本地模型配置: {LOCAL_API_URL}")
    else:
        print(f"❌ 不支持的模型类型: {AI_MODEL_TYPE}")
        return False
    
    return True

def convert_mp4_to_mp3():
    """将MP4文件转换为MP3"""
    print("🎵 开始转换MP4为MP3...")
    
    downloads_dir = Path("downloads")
    if not downloads_dir.exists():
        print("❌ downloads目录不存在")
        return False
    
    # 查找MP4文件
    mp4_files = list(downloads_dir.glob("*.mp4"))
    if not mp4_files:
        print("❌ 未找到MP4文件")
        return False
    
    print(f"找到 {len(mp4_files)} 个MP4文件")
    
    success_count = 0
    for mp4_file in mp4_files:
        try:
            mp3_file = mp4_file.with_suffix('.mp3')
            print(f"转换: {mp4_file.name} -> {mp3_file.name}")
            
            # 使用ffmpeg转换
            cmd = [
                "ffmpeg", "-i", str(mp4_file),
                "-vn",  # 不包含视频
                "-acodec", "libmp3lame",  # 使用MP3编码器
                "-ar", "16000",  # 采样率16kHz
                "-ac", "1",  # 单声道
                "-q:a", "2",  # 音频质量
                "-y",  # 覆盖输出文件
                str(mp3_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ 转换成功: {mp3_file.name}")
                # 删除原始MP4文件
                mp4_file.unlink()
                print(f"🧹 已删除: {mp4_file.name}")
                success_count += 1
            else:
                print(f"❌ 转换失败: {mp3_file.name}")
                print(f"错误: {result.stderr}")
                
        except Exception as e:
            print(f"❌ 转换异常 {mp4_file.name}: {e}")
    
    if success_count > 0:
        print(f"✅ 成功转换 {success_count} 个文件")
        return True
    else:
        print("❌ 没有成功转换任何文件")
        return False

def get_ai_summary_script_and_args(timestamp):
    """根据配置获取AI总结脚本和参数"""
    if AI_MODEL_TYPE == "qwen":
        script_name = "qwen_news_summary.py"
        args = ["--timestamp", timestamp]
        print(f"🤖 使用通义千问模型进行AI总结")
    elif AI_MODEL_TYPE == "openai":
        script_name = "openai_news_summary.py"
        args = ["--timestamp", timestamp]
        print(f"🤖 使用OpenAI模型进行AI总结")
    elif AI_MODEL_TYPE == "local":
        # 根据本地模型类型选择脚本
        if LOCAL_MODEL_NAME and "qwen" in LOCAL_MODEL_NAME.lower():
            script_name = "qwen_news_summary.py"
            args = ["--timestamp", timestamp, "--local"]
            if LOCAL_MODEL_PATH and LOCAL_MODEL_PATH != "/path/to/your/local/model":
                args.extend(["--model-path", LOCAL_MODEL_PATH])
        else:
            # 使用OpenAI兼容的本地服务
            script_name = "openai_news_summary.py"
            args = ["--timestamp", timestamp, "--local", "--api-url", LOCAL_API_URL]
            if LOCAL_MODEL_NAME and LOCAL_MODEL_NAME != "qwen2.5:7b":
                args.extend(["--model", LOCAL_MODEL_NAME])
        print(f"🤖 使用本地模型进行AI总结: {LOCAL_MODEL_NAME}")
    else:
        print(f"❌ 不支持的模型类型: {AI_MODEL_TYPE}")
        return None, None
    
    return script_name, args

def main():
    """主函数"""
    print("🎯 新闻处理流水线启动")
    print("📋 流程：下载抖音视频 -> MP4转MP3 -> 转文字 -> AI总结 -> Git提交")

    parser = argparse.ArgumentParser(description="执行单个抖音视频文档流水线")
    parser.add_argument("douyin_url", help="抖音视频链接")
    parser.add_argument("--timestamp", help="输出命名使用的时间戳，格式 YYYYMMDD-HHMM")
    args = parser.parse_args()

    douyin_url = args.douyin_url
    print(f"🎬 目标视频: {douyin_url}")

    timestamp = args.timestamp or datetime.now().strftime("%Y%m%d-%H%M")
    print(f"📅 本次流水线时间戳: {timestamp}")
    
    # 检查前置条件
    if not check_prerequisites():
        print("❌ 前置条件检查失败，请检查脚本文件")
        return
    
    # 检查AI模型配置
    if not check_ai_model_config():
        print("❌ AI模型配置检查失败，请检查config.py")
        return
    
    # 步骤1: 下载抖音视频
    download_args = ["--url", douyin_url]
    if not run_script("douyin_download.py", "步骤1: 下载抖音视频", download_args):
        print("❌ 第一步失败，停止执行")
        return
    
    # 等待一下确保文件写入完成
    time.sleep(2)
    
    # 步骤1.5: MP4转MP3
    if not convert_mp4_to_mp3():
        print("❌ MP4转MP3失败，停止执行")
        return
    
    # 等待一下确保文件写入完成
    time.sleep(2)
    
    # 步骤2: MP3转文字（使用统一时间戳）
    mp3_args = ["--timestamp", timestamp]
    if not run_script("mp3_2_txt.py", "步骤2: MP3转文字", mp3_args):
        print("❌ 第二步失败，停止执行")
        return
    
    # 等待一下确保文件写入完成
    time.sleep(2)
    
    # 步骤3: AI总结（根据配置选择模型）
    script_name, summary_args = get_ai_summary_script_and_args(timestamp)
    if not script_name or not summary_args:
        print("❌ AI模型配置错误，停止执行")
        return
    
    if not run_script(script_name, "步骤3: AI总结和投资建议", summary_args):
        print("❌ 第三步失败，停止执行")
        return
    
    # 等待一下确保文件写入完成
    time.sleep(2)
    
    # 步骤4: Git提交
    # if not run_script("git_commit.py", "步骤4: Git提交和推送"):
    #     print("❌ 第四步失败")
    #     return
    
    print("\n🎉 所有步骤完成！")
    print(f"📅 本次流水线时间戳: {timestamp}")
    print(f"🤖 使用的AI模型: {AI_MODEL_TYPE}")
    print("📁 生成的文件:")
    
    # 显示生成的文件
    news_dir = Path("news")
    if news_dir.exists():
        files = list(news_dir.glob(f"{timestamp}*"))
        for file in files:
            print(f"   📄 {file.name}")
    
    # print("🔗 文件已自动提交到Git仓库")

if __name__ == "__main__":
    main() 
