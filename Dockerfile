
FROM python:3.9-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/models

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE $PORT

CMD ["supervisord","-c","./supervisor.conf"]
