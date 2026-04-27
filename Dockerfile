FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN python -m pip install --upgrade pip
RUN python -m pip install --no-cache-dir -r requirements.txt
RUN cat requirements.txt
RUN python -m pip list

CMD ["python", "-u", "bot_esports_v3.py"]