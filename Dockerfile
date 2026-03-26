FROM python:3.10-slim

# System dependencies + ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && apt-get clean

WORKDIR /app

COPY . /app

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Port for Render free-tier
EXPOSE 8080

CMD ["python", "main.py"]
