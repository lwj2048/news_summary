import whisper
import subprocess
from pathlib import Path
from tqdm import tqdm
from opencc import OpenCC
from datetime import datetime

# ===== 配置 =====
AUDIO_PATH = "downloads/audio.mp3"  # 输入 MP3
SEGMENT_DIR = Path("segments")
OUTPUT_DIR = Path("news")  # 输出目录
SEGMENT_SECONDS = 65  # 每段长度（秒）
MODEL_NAME = "base"   # whisper 模型，可换 small/medium

# ===== 1. 切片 =====
print("🎬 正在切片音频...")
SEGMENT_DIR.mkdir(exist_ok=True)
subprocess.run([
    "ffmpeg", "-i", AUDIO_PATH, "-f", "segment",
    "-segment_time", str(SEGMENT_SECONDS),
    "-c", "copy", f"{SEGMENT_DIR}/part_%03d.mp3"
], check=True)

# ===== 2. 加载模型 =====
print("🤖 正在加载 Whisper 模型...")
model = whisper.load_model(MODEL_NAME)
cc = OpenCC('t2s')  # 繁体转简体

# ===== 3. 循环转写 + 进度条 =====
all_text = []
parts = sorted(SEGMENT_DIR.glob("part_*.mp3"))

print(f"📝 共 {len(parts)} 段音频，开始转写...")
for part in tqdm(parts, desc="Transcribing", unit="segment"):
    result = model.transcribe(str(part), language="zh")
    text = cc.convert(result["text"])  # 转简体
    all_text.append(text)

# ===== 4. 保存结果 =====
OUTPUT_DIR.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d-%H%M")
output_file = OUTPUT_DIR / f"{timestamp}.txt"
with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(all_text))

print(f"✅ 转换完成，已保存到 {output_file}")

