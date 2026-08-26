FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY app /app/app

CMD ["sh", "-lc", "python3 -m app.wait_for_db && exec gunicorn -w ${WEB_CONCURRENCY:-4} -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${LICENSE_PORT:-4349} app.main:app"]
