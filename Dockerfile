# Base Python image
FROM python:3.10-slim

# Install system dependencies + ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy all files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Render free-tier web service port (optional env, fallback 8080)
ENV PORT=8080

# Command to run bot
CMD ["python", "main.py"]
