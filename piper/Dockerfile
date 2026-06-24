FROM python:3.12-slim

WORKDIR /app

# piper-tts (CLI + runtime onnx) + serveur HTTP minimal
RUN pip install --no-cache-dir piper-tts fastapi "uvicorn[standard]"

COPY server.py .

# Cache des voix téléchargées (monté en volume par docker-compose)
ENV PIPER_DATA_DIR=/data
RUN mkdir -p /data

EXPOSE 5000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5000"]
