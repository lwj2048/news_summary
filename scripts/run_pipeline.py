#!/usr/bin/env python3
"""
新闻处理流水线主控制脚本
按顺序执行：下载抖音视频 -> 转MP3 -> 转文字 -> AI总结 -> Git提交
"""

import subprocess
import sys
from pathlib import Path
import time
from datetime import datetime

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
        "git_commit.py"
    ]
    
    for script in required_scripts:
        script_path = Path(__file__).parent / script
        if not script_path.exists():
            print(f"❌ 缺少必要脚本: {script}")
            return False
    
    print("✅ 所有前置条件检查通过")
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
                print(f"❌ 转换失败: {mp4_file.name}")
                print(f"错误: {result.stderr}")
                
        except Exception as e:
            print(f"❌ 转换异常 {mp4_file.name}: {e}")
    
    if success_count > 0:
        print(f"✅ 成功转换 {success_count} 个文件")
        return True
    else:
        print("❌ 没有成功转换任何文件")
        return False

def main():
    """主函数"""
    print("🎯 新闻处理流水线启动")
    print("📋 流程：下载抖音视频 -> MP4转MP3 -> 转文字 -> AI总结 -> Git提交")
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("❌ 请提供抖音视频链接")
        print("使用方法: python run_pipeline.py <抖音视频链接>")
        print("示例: python run_pipeline.py 'https://v.douyin.com/xxx/'")
        return
    
    douyin_url = sys.argv[1]
    print(f"🎬 目标视频: {douyin_url}")
    
    # 生成统一的时间戳
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    print(f"📅 本次流水线时间戳: {timestamp}")
    
    # 检查前置条件
    if not check_prerequisites():
        print("❌ 前置条件检查失败，请检查脚本文件")
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
    
    # 步骤3: AI总结（使用相同时间戳）
    summary_args = ["--timestamp", timestamp]
    if not run_script("qwen_news_summary.py", "步骤3: AI总结和投资建议", summary_args):
        print("❌ 第三步失败，停止执行")
        return
    
    # 等待一下确保文件写入完成
    time.sleep(2)
    
    # 步骤4: Git提交
    if not run_script("git_commit.py", "步骤4: Git提交和推送"):
        print("❌ 第四步失败")
        return
    
    print("\n🎉 所有步骤完成！")
    print(f"📅 本次流水线时间戳: {timestamp}")
    print("📁 生成的文件:")
    
    # 显示生成的文件
    news_dir = Path("news")
    if news_dir.exists():
        files = list(news_dir.glob(f"{timestamp}*"))
        for file in files:
            print(f"   📄 {file.name}")
    
    print("🔗 文件已自动提交到Git仓库")

if __name__ == "__main__":
    main() 