FROM python:3.10-alpine
WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . .

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS} --timeout ${GUNICORN_TIMEOUT} rso_backend.wsgi"]
