FROM python:3.11-slim

# Установка Chromium и драйвера
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Указываем путь к Chromium
ENV PATH="${PATH}:/usr/bin/chromium"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

CMD ["python", "-u", "bot_esports_v3.py"]