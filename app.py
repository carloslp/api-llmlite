# -*- coding: utf-8 -*-
import os
from flask import Flask, request, jsonify
from litellm import completion
import logging
from logging.config import dictConfig

# Configuración de logging robusta y centralizada.
# Esto permite un formato detallado y la salida tanto a consola como a un archivo.
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s.%(funcName)s (line %(lineno)d): %(message)s',
    }},
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'app.log', # Guarda los logs en un archivo
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'default',
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file'] # Envía logs a ambos handlers
    }
})

# Inicializar la aplicación Flask
app = Flask(__name__)

@app.route('/generate', methods=['POST'])
def generate_text():
    """
    Endpoint para generar texto usando la API de LiteLLM.
    Espera un payload JSON con 'system_prompt' y 'user_prompt'.
    La configuración se lee de variables de entorno.
    """
    app.logger.info("Solicitud recibida en el endpoint /generate.")
    
    # 1. Obtener la configuración desde las variables de entorno
    api_key = os.environ.get("LITELLM_API_KEY")
    api_base = os.environ.get("LITELLM_API_BASE")
    model_name = os.environ.get("LITELLM_MODEL")
    
    app.logger.info(f"Modelo a utilizar: {model_name}")

    if not api_key:
        app.logger.error("La variable de entorno LITELLM_API_KEY no está configurada.")
        return jsonify({
            "error": "La clave de la API no está configurada. Por favor, establece la variable de entorno LITELLM_API_KEY."
        }), 500

    # 2. Validar y obtener los datos de la solicitud POST
    try:
        data = request.get_json()
        if not data:
            app.logger.warning("La solicitud contenía un payload JSON inválido o vacío.")
            return jsonify({"error": "Payload JSON inválido o vacío."}), 400
        
        app.logger.info(f"Datos recibidos: {data}")
            
        system_prompt = data.get('system_prompt')
        user_prompt = data.get('user_prompt')

        if not user_prompt:
            app.logger.warning("El campo 'user_prompt' no fue proporcionado en la solicitud.")
            return jsonify({"error": "El campo 'user_prompt' es obligatorio en el cuerpo de la solicitud."}), 400
        
        if not system_prompt:
            system_prompt = "Eres un asistente servicial y conciso."
            app.logger.info("No se proporcionó 'system_prompt', usando el valor por defecto.")

    except Exception as e:
        app.logger.error(f"Error al procesar el JSON de la solicitud: {e}", exc_info=True)
        return jsonify({"error": "No se pudo procesar el cuerpo de la solicitud. Asegúrate de que sea un JSON válido."}), 400

    # 3. Construir el array de mensajes para la API de LiteLLM
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # 4. Llamar a la API de LiteLLM
    try:
        if api_base:
            app.logger.info(f"Enviando solicitud a la API de LiteLLM en la URL base: {api_base}")
        else:
            app.logger.info("Enviando solicitud a la API de LiteLLM (URL por defecto)...")

        response = completion(
            model=model_name,
            messages=messages,
            api_key=api_key,
            api_base=api_base
        )

        generated_content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        app.logger.info("Respuesta recibida exitosamente de LiteLLM.")
        return jsonify({"response": generated_content})

    except Exception as e:
        # Usar exc_info=True para registrar el traceback completo de la excepción
        app.logger.error(f"Ocurrió un error al llamar a la API de LiteLLM: {e}", exc_info=True)
        return jsonify({"error": "Ocurrió un error interno al comunicarse con el servicio del LLM."}), 502


if __name__ == '__main__':
    # El servidor de desarrollo de Flask no debe usarse en producción.
    # Gunicorn se encargará de ejecutar la app en el Dockerfile.
    app.run(host='0.0.0.0', port=5000, debug=True)

