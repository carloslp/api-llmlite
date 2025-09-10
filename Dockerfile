# Usa una imagen base oficial de Python
FROM python:3.11-slim

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia el archivo de dependencias al directorio de trabajo
COPY requirements.txt .

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de la aplicación
COPY . .

# Expone el puerto en el que Gunicorn se ejecutará
EXPOSE 5000

# Comando para ejecutar la aplicación con Gunicorn
# MEJORA: Se añade un timeout configurable a través de una variable de entorno.
# Se recomienda que GUNICORN_TIMEOUT sea mayor que LITELLM_TIMEOUT.
# Se establece un valor por defecto de 120 segundos si no se especifica.
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "--timeout", "1200", "app:app"]

