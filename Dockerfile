FROM python:3.10-slim

# System tools aur FFmpeg install karna
# libgomp1 AI model (Faster-Whisper) ko CPU par chalane ke liye zaroori hai
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Sabse pehle requirements copy karke install karna
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Baaki saara code copy karna
COPY . .

CMD ["python", "main.py"]
