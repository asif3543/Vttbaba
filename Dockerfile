# Python 3.10 slim version for fast building
FROM python:3.10-slim

# Setup Working Directory
WORKDIR /app

# Requirements file copy karna aur install karna
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baaki saari files ko container me copy karna
COPY . .

# Render free tier port
EXPOSE 10000

# Bot run karne ka command
CMD ["python", "main.py"]
