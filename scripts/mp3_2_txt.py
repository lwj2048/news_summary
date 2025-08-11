import whisper
model = whisper.load_model("base")  # 可选 tiny, base, small, medium, large
result = model.transcribe("downloads/audio.mp3")
print(result["text"])

