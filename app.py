# -*- coding: utf-8 -*-
import os
from flask import Flask, request, jsonify
from litellm import completion
import logging
from logging.config import dictConfig
import requests

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

@app.route('/', methods=['GET'])
def get_models():
    """
    Endpoint para obtener la lista de modelos disponibles del servicio LiteLLM.
    """
    app.logger.info("Solicitud recibida en el endpoint / (models).")
    api_base = os.environ.get("LITELLM_API_BASE")
    api_key = os.environ.get("LITELLM_API_KEY")

    if not api_base:
        error_msg = "La variable de entorno LITELLM_API_BASE es obligatoria para esta operación."
        app.logger.error(error_msg)
        return jsonify({"error": error_msg}), 500
    
    if not api_key:
        error_msg = "La variable de entorno LITELLM_API_KEY es obligatoria para esta operación."
        app.logger.error(error_msg)
        return jsonify({"error": error_msg}), 500

    models_url = f"{api_base.rstrip('/')}/models"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    try:
        app.logger.info(f"Consultando la lista de modelos en: {models_url}")
        response = requests.get(models_url, headers=headers)
        response.raise_for_status() # Lanza una excepción para códigos de estado de error
        
        models_data = response.json()
        app.logger.info("Lista de modelos obtenida exitosamente.")
        return jsonify(models_data)

    except requests.exceptions.HTTPError as http_err:
        app.logger.error(f"Error HTTP al consultar modelos: {http_err} - Respuesta: {response.text}", exc_info=True)
        return jsonify({"error": f"Error del servicio LiteLLM al obtener modelos: {response.status_code}", "details": response.text}), 502
    except requests.exceptions.RequestException as req_err:
        app.logger.error(f"Error de conexión al consultar modelos: {req_err}", exc_info=True)
        return jsonify({"error": "No se pudo conectar con el servicio de LiteLLM."}), 503
    except Exception as e:
        app.logger.error(f"Ocurrió un error inesperado al consultar modelos: {e}", exc_info=True)
        return jsonify({"error": "Ocurrió un error interno inesperado."}), 500

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
    model_name = os.environ.get("LITELLM_MODEL", "claude-3-haiku-20240307")
    
    # MEJORA: Añadido un log explícito para depurar la configuración de la URL base
    if not api_base:
        app.logger.warning("La variable de entorno LITELLM_API_BASE no está configurada o está vacía. La solicitud se enviará a la API por defecto de LiteLLM, no a tu servicio autoalojado.")
    else:
        app.logger.info(f"URL base de LiteLLM configurada explícitamente: '{api_base}'")

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

