FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERD=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

# Run collectstatic command to gather static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# CMD [ "python", "manage.py", "runserver", "0.0.0.0:8000"]

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]