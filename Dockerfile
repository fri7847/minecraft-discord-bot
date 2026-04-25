FROM python:3.11-slim

WORKDIR /app

# docker.io 제거 - 소켓 마운트로 충분함
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /docker/minecraft

CMD ["python", "-m", "bot.main"]
