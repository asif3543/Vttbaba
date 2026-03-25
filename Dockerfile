FROM python:3.11-slim

# System dependencies install kar rahe hain
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements pehle copy aur install (cache optimization ke liye)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Baaki saara code copy
COPY . .

CMD ["python", "main.py"]
