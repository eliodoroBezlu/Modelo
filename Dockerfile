# Usar Python 3.11 slim
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar LibreOffice + dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libreoffice \
    libreoffice-calc \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Verificar LibreOffice instalado
RUN libreoffice --version

# Copiar requirements primero (para cache de Docker)
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código
COPY . .

# Crear directorios necesarios
RUN mkdir -p /app/models /app/data /tmp/excel-to-pdf

# Dar permisos al directorio temporal
RUN chmod 777 /tmp/excel-to-pdf

# Exponer puerto (Railway lo sobreescribe con $PORT)
EXPOSE 8000

# Iniciar aplicación
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
