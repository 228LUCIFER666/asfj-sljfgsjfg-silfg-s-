FROM python:3.11-slim
RUN apt-get update && apt-get install -y chromium chromium-driver xvfb
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py .
# Важно: не используйте CMD, код должен быть в main()