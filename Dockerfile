FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render ke liye important
EXPOSE 10000

# Dummy server (sleep fix optional)
CMD ["python3", "main.py"]
