FROM python:3.13-slim

# Instalar dependencias del sistema para Cairo
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto
COPY . .

# Recolectar archivos estáticos (si los tienes)
RUN python manage.py collectstatic --noinput || true

# Exponer el puerto
EXPOSE 8000

# Comando para iniciar la aplicación
CMD gunicorn core.wsgi --bind 0.0.0.0:$PORT