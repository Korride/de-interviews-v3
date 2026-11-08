FROM python:3.11-slim

WORKDIR /app

# psql client is used by the one-shot entrypoint (docker/run_all.sh)
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/docker/run_all.sh
