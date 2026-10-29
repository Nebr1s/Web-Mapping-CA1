FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# GeoDjango needs GDAL/GEOS/PROJ system libraries
RUN apt-get update \
    && apt-get install --yes --no-install-recommends binutils gdal-bin libgdal-dev libgeos-dev libproj-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user
RUN useradd --create-home appuser && mkdir -p /app/staticfiles && chown -R appuser /app
USER appuser
