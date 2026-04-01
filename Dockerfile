FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Render free tier port
EXPOSE 10000

CMD ["python", "main.py"]
