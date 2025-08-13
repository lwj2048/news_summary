#!/usr/bin/env python3
"""
OpenAI新闻总结独立运行脚本
配置从config.py读取，支持指定原文档和输出文档
"""

import argparse
import sys
from pathlib import Path
import subprocess

def run_openai_summary(input_file, output_file=None, timestamp=None):
    """运行OpenAI新闻总结"""
    
    # 检查输入文件是否存在
    if not Path(input_file).exists():
        print(f"❌ 输入文件不存在: {input_file}")
        return False
    
    # 如果没有指定输出文件，自动生成
    if not output_file:
        input_path = Path(input_file)
        if timestamp:
            output_file = f"news/{timestamp}_AI总结.md"
        else:
            # 从输入文件名生成输出文件名
            output_name = input_path.stem
            output_file = f"news/{output_name}_AI总结.md"
    
    # 确保输出目录存在
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    # 构建命令参数
    script_path = Path("scripts/openai_news_summary.py")
    
    if not script_path.exists():
        print(f"❌ 脚本不存在: {script_path}")
        return False
    
    # 基础参数
    args = [
        sys.executable, str(script_path),
        "--news-file", input_file,
        "--output-dir", str(Path(output_file).parent)
    ]
    
    # 如果指定了时间戳，添加时间戳参数
    if timestamp:
        args.extend(["--timestamp", timestamp])
    
    # 根据配置添加其他参数
    try:
        from config import AI_MODEL_TYPE, LOCAL_API_URL, LOCAL_MODEL_NAME
        
        if AI_MODEL_TYPE == "local":
            # 本地模式
            args.extend(["--local", "--api-url", LOCAL_API_URL])
            # 总是传递模型名称，确保使用正确的模型
            if LOCAL_MODEL_NAME:
                args.extend(["--model", LOCAL_MODEL_NAME])
            print(f"🤖 使用本地模型: {LOCAL_MODEL_NAME}")
        else:
            # 云端模式
            print("☁️ 使用云端OpenAI API")
            
    except ImportError:
        print("⚠️  无法导入配置文件，使用默认参数")
    
    print(f"\n🚀 开始运行OpenAI新闻总结...")
    print(f"📥 输入文件: {input_file}")
    print(f"📤 输出文件: {output_file}")
    print(f"🔧 执行命令: {' '.join(args)}")
    
    try:
        # 运行脚本
        result = subprocess.run(args, check=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 新闻总结完成！")
            print(f"📁 输出文件: {output_file}")
            
            # 检查输出文件是否生成
            if Path(output_file).exists():
                file_size = Path(output_file).stat().st_size
                print(f"📊 文件大小: {file_size} 字节")
                
                # 显示文件内容预览
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        print(f"\n📝 内容预览:")
                        for i, line in enumerate(lines[:10]):  # 显示前10行
                            if line.strip():
                                print(f"   {i+1:2d}: {line}")
                        if len(lines) > 10:
                            print(f"   ... (共 {len(lines)} 行)")
                except Exception as e:
                    print(f"⚠️  无法读取输出文件内容: {e}")
            else:
                # 尝试查找实际生成的文件
                output_dir = Path(output_file).parent
                if output_dir.exists():
                    # 查找以时间戳开头的markdown文件
                    timestamp = Path(input_file).stem.split('_')[0] if '_' in Path(input_file).stem else Path(input_file).stem
                    generated_files = list(output_dir.glob(f"{timestamp}*.md"))
                    
                    if generated_files:
                        actual_file = generated_files[0]
                        print(f"🔍 找到实际生成的文件: {actual_file.name}")
                        file_size = actual_file.stat().st_size
                        print(f"📊 文件大小: {file_size} 字节")
                        
                        # 显示文件内容预览
                        try:
                            with open(actual_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                lines = content.split('\n')
                                print(f"\n📝 内容预览:")
                                for i, line in enumerate(lines[:10]):  # 显示前10行
                                    if line.strip():
                                        print(f"   {i+1:2d}: {line}")
                                if len(lines) > 10:
                                    print(f"   ... (共 {len(lines)} 行)")
                        except Exception as e:
                            print(f"⚠️  无法读取生成文件内容: {e}")
                    else:
                        print(f"⚠️  输出文件未找到: {output_file}")
                        print(f"🔍 在目录 {output_dir} 中未找到以 {timestamp} 开头的markdown文件")
                else:
                    print(f"⚠️  输出目录不存在: {output_dir}")
            
            return True
        else:
            print(f"❌ 脚本执行失败，返回码: {result.returncode}")
            if result.stderr:
                print(f"🔍 错误信息: {result.stderr}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 脚本执行异常: {e}")
        if e.stderr:
            print(f"🔍 错误信息: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="OpenAI新闻总结独立运行脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基本使用
  python run_openai_summary.py news/20250813-1200.txt
  
  # 指定输出文件
  python run_openai_summary.py news/20250813-1200.txt -o news/总结报告.md
  
  # 指定时间戳
  python run_openai_summary.py news/20250813-1200.txt -t 20250813-1200
  
  # 使用配置文件中的设置
  python run_openai_summary.py news/input.txt
        """
    )
    
    parser.add_argument('input_file', help='输入新闻文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径（可选，自动生成）')
    parser.add_argument('-t', '--timestamp', help='时间戳（可选）')
    
    args = parser.parse_args()
    
    print("🎯 OpenAI新闻总结独立运行脚本")
    print("=" * 60)
    
    # 检查配置文件
    try:
        from config import AI_MODEL_TYPE
        print(f"📋 当前配置: AI模型类型 = {AI_MODEL_TYPE}")
    except ImportError:
        print("⚠️  警告: 无法导入配置文件，使用默认设置")
    
    # 运行总结
    success = run_openai_summary(
        input_file=args.input_file,
        output_file=args.output,
        timestamp=args.timestamp
    )
    
    if success:
        print("\n🎉 任务完成！")
    else:
        print("\n❌ 任务失败！")
        sys.exit(1)

if __name__ == "__main__":
    main() 