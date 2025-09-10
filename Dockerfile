# Usa una imagen oficial de Python delgada como imagen base
FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de dependencias primero para aprovechar el cache de Docker
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de la aplicación al directorio de trabajo
COPY . .

# Expone el puerto en el que la aplicación se ejecuta
EXPOSE 5000

# Variable de entorno para la clave de API.
# IMPORTANTE: Esta clave debe ser proporcionada al ejecutar el contenedor
# usando el flag '-e', no debe ser codificada directamente en la imagen.
# Ejemplo: docker run -e LITELLM_API_KEY="tu_clave_aqui" ...
ENV LITELLM_API_KEY=""

# Comando para ejecutar la aplicación usando un servidor WSGI de producción (gunicorn)
# Esto es más robusto y seguro que el servidor de desarrollo de Flask.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
