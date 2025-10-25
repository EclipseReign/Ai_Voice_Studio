FROM python:3.11-slim

# Системные пакеты: ffmpeg (для pydub), espeak-ng (часто нужен piper-tts), build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg espeak-ng git curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Ускоряем установку зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Railway пробрасывает PORT, FastAPI/uvicorn должны слушать его
ENV PYTHONUNBUFFERED=1
CMD ["python","-m","uvicorn","server:app","--host","0.0.0.0","--port","${PORT}"]
