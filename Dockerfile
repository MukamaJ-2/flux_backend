FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app

RUN python manage.py collectstatic --noinput || true

COPY start.sh /app/
RUN chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]
