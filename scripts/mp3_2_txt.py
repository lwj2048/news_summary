import whisper
import subprocess
import argparse
import sys
import re
from pathlib import Path
from tqdm import tqdm
from opencc import OpenCC
from datetime import datetime

# ===== 配置 =====
# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from config import AUDIO_PATH, SEGMENT_DIR, OUTPUT_DIR, SEGMENT_SECONDS, MODEL_NAME
    SEGMENT_DIR = Path(SEGMENT_DIR)
    OUTPUT_DIR = Path(OUTPUT_DIR)
except ImportError:
    print("❌ 无法导入配置文件，请确保config.py存在")
    sys.exit(1)

def check_text_errors(text):
    """免费错别字校验函数"""
    print("🔍 开始错别字校验...")
    
    # 常见同音字错误映射
    common_errors = {
        "已救换心": "以旧换新",
        "已救": "以旧",
        "换心": "换新",
        "真金白银": "真金白银",  # 这个是对的
        "梳里": "梳理",
        "力卷": "力卷",  # 需要上下文判断
        "政策梳里": "政策梳理",
        "更加的有智慧": "更加有智慧",
        "好像拿出了": "好像拿出了",  # 这个是对的
        "1500亿": "1500亿",  # 这个是对的
        "加了一倍": "加了一倍",  # 这个是对的
    }
    
    # 专业术语检查
    professional_terms = [
        "以旧换新", "产能过剩", "价格竞争", "供需失衡", "财政机制",
        "制造业", "投资增速", "需求增长", "政策优化", "产能出清"
    ]
    
    corrected_text = text
    corrections = []
    
    # 检查同音字错误
    for error, correct in common_errors.items():
        if error in corrected_text and error != correct:
            corrected_text = corrected_text.replace(error, correct)
            corrections.append(f"'{error}' → '{correct}'")
    
    # 检查专业术语（简单检查）
    for term in professional_terms:
        if term in corrected_text:
            print(f"✅ 发现专业术语: {term}")
    
    # 检查数字格式
    number_pattern = r'\d+亿|\d+万|\d+%'
    numbers = re.findall(number_pattern, corrected_text)
    if numbers:
        print(f"✅ 发现数字信息: {', '.join(numbers)}")
    
    if corrections:
        print(f"🔧 自动纠正: {', '.join(corrections)}")
        print(f"📝 纠正后的文本长度: {len(corrected_text)} 字符")
    else:
        print("✅ 未发现明显错别字")
    
    return corrected_text, corrections

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='MP3转文字工具')
    parser.add_argument('--timestamp', '-t', 
                       help='指定时间戳 (格式: YYYYMMDD-HHMM)，如果不指定则自动生成')
    parser.add_argument('--audio-path', '-a',
                       help=f'音频文件路径 (如果不指定，会自动查找downloads目录中的MP3文件)')
    parser.add_argument('--output-dir', '-o',
                       help=f'输出目录 (默认: {OUTPUT_DIR})')
    
    args = parser.parse_args()
    
    # 获取时间戳
    if args.timestamp:
        timestamp = args.timestamp
        print(f"📅 使用指定时间戳: {timestamp}")
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        print(f"📅 自动生成时间戳: {timestamp}")
    
    # 获取音频路径
    if args.audio_path:
        audio_path = args.audio_path
    else:
        # 自动查找下载目录中的MP3文件
        downloads_dir = Path("downloads")
        if downloads_dir.exists():
            mp3_files = list(downloads_dir.glob("*.mp3"))
            if mp3_files:
                audio_path = str(mp3_files[0])  # 使用第一个MP3文件
                print(f"🔍 自动找到MP3文件: {audio_path}")
            else:
                audio_path = AUDIO_PATH
        else:
            audio_path = AUDIO_PATH
    
    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    
    print(f"🎵 音频文件: {audio_path}")
    print(f"📁 输出目录: {output_dir}")
    
    # 检查音频文件是否存在
    if not Path(audio_path).exists():
        print(f"❌ 音频文件不存在: {audio_path}")
        print("💡 请检查以下位置:")
        if Path("downloads").exists():
            mp3_files = list(Path("downloads").glob("*.mp3"))
            if mp3_files:
                print("   下载目录中的MP3文件:")
                for f in mp3_files:
                    print(f"   - {f}")
            else:
                print("   下载目录中没有MP3文件")
        else:
            print("   下载目录不存在")
        sys.exit(1)
    
    # ===== 1. 切片 =====
    print("🎬 正在切片音频...")
    SEGMENT_DIR.mkdir(exist_ok=True)
    
    try:
        subprocess.run([
            "ffmpeg", "-i", audio_path, "-f", "segment",
            "-segment_time", str(SEGMENT_SECONDS),
            "-c", "copy", f"{SEGMENT_DIR}/part_%03d.mp3"
        ], check=True, capture_output=True, text=True)
        print("✅ 音频切片完成")
    except subprocess.CalledProcessError as e:
        print(f"❌ 音频切片失败: {e}")
        print(f"错误输出: {e.stderr}")
        sys.exit(1)
    
    # ===== 2. 加载模型 =====
    print("🤖 正在加载 Whisper 模型...")
    try:
        model = whisper.load_model(MODEL_NAME)
        cc = OpenCC('t2s')  # 繁体转简体
        print(f"✅ 模型加载完成: {MODEL_NAME}")
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        sys.exit(1)
    
    # ===== 3. 循环转写 + 进度条 =====
    all_text = []
    parts = sorted(SEGMENT_DIR.glob("part_*.mp3"))
    
    if not parts:
        print("❌ 没有找到音频切片文件")
        sys.exit(1)
    
    print(f"📝 共 {len(parts)} 段音频，开始转写...")
    
    for part in tqdm(parts, desc="Transcribing", unit="segment"):
        try:
            result = model.transcribe(str(part), language="zh")
            text = cc.convert(result["text"])  # 转简体
            all_text.append(text)
        except Exception as e:
            print(f"⚠️  转写失败 {part.name}: {e}")
            all_text.append(f"[转写失败: {e}]")
    
    if not all_text:
        print("❌ 没有成功转写任何音频")
        sys.exit(1)
    
    # ===== 4. 错别字校验 =====
    full_text = "\n".join(all_text)
    corrected_text, corrections = check_text_errors(full_text)
    
    # ===== 5. 保存结果 =====
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{timestamp}.txt"
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(corrected_text)
        print(f"✅ 转换完成，已保存到 {output_file}")
        
        if corrections:
            print(f"🔧 已自动纠正 {len(corrections)} 处错别字")
            print(f"📝 原始文本长度: {len(full_text)} 字符")
            print(f"📝 纠正后长度: {len(corrected_text)} 字符")
        
        # 显示文件大小
        file_size = output_file.stat().st_size
        print(f"📊 文件大小: {file_size} 字节")
        
        # 显示内容预览
        print(f"📋 内容预览 (前200字符):")
        preview = corrected_text[:200]
        print(f"    {preview}{'...' if len(corrected_text) > 200 else ''}")
        
    except Exception as e:
        print(f"❌ 保存文件失败: {e}")
        sys.exit(1)
    
    # 清理临时文件
    try:
        for part in parts:
            part.unlink()
        print("🧹 临时文件清理完成")
    except Exception as e:
        print(f"⚠️  临时文件清理失败: {e}")

if __name__ == "__main__":
    main()

