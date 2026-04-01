FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render ke liye port 10000 expose karna zaroori hai
EXPOSE 10000

CMD ["python", "main.py"]
