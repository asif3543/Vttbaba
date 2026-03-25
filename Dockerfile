FROM python:3.11-slim   # 3.11 better hai Groq SDK ke liye

# System dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements pehle copy + install (cache better rahega)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Baaki code
COPY . .

CMD ["python", "main.py"]
