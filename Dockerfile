FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="${PATH}:/usr/bin/chromium"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все скрипты
COPY fonbet_esports_parser_v2.py .
COPY polymarket_esports_parser_v2.py .
COPY bot_esports_v3.py .

CMD ["python", "-u", "bot_esports_v3.py"]