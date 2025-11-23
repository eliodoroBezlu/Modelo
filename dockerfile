# Usar Python 3.11 slim
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (para cache de Docker)
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código
COPY . .

# Crear directorios necesarios
RUN mkdir -p /app/models /app/data

# Exponer puerto (Railway lo sobreescribe con $PORT)
EXPOSE 8000

# 🔥 IMPORTANTE: Usar variable de entorno PORT de Railway
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}