FROM python:3.12-slim

# iputils-ping : necessaire pour le controle ICMP depuis le conteneur
RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "-b", "0.0.0.0:8000", "--worker-class", "gthread", "--workers", "2", "--threads", "4", "wsgi:app"]
