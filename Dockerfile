# Cuentas de Cobro - Flask + Waitress + WeasyPrint
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV PORT=5000

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ARG APP_BUILD_ID=unknown
ENV APP_BUILD_ID=${APP_BUILD_ID}

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, json; r=urllib.request.urlopen('http://127.0.0.1:${PORT:-5000}/health'); d=json.load(r); assert d.get('build'), 'missing build'" || exit 1

CMD ["sh", "-c", "echo \"Starting build=${APP_BUILD_ID}\" && exec waitress-serve --host=0.0.0.0 --port=${PORT:-5000} run:app"]
