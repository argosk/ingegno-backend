# Usa un'immagine base di Python
FROM python:3.11-slim

# Imposta la directory di lavoro
WORKDIR /app

# Copia i file requirements
COPY requirements.txt /app/

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto del progetto
COPY . /app/

# Imposta una variabile temporanea per ALLOWED_HOSTS
ENV DJANGO_SETTINGS_MODULE=ingegno.settings
ENV ALLOWED_HOSTS=localhost
ENV CORS_ALLOWED_ORIGINS=http://localhost,http://127.0.0.1
ENV CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1
ENV EMAIL_PASSWORD=abcdesdfgh
ENV DEBUG=False

# Raccogli i file statici
RUN python manage.py collectstatic --noinput

# Esponi la porta su cui il server Gunicorn ascolterà
EXPOSE 8000

# Comando per avviare l'applicazione
CMD ["sh", "-c", "python manage.py migrate && gunicorn ingegno.wsgi:application --bind 0.0.0.0:8000"]

