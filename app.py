# -*- coding: utf-8 -*-
import os
from flask import Flask, request, jsonify
from litellm import completion
import logging
from logging.config import dictConfig
from openai import OpenAI, APIError

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
    Endpoint para obtener la lista de modelos disponibles del servicio LiteLLM,
    utilizando la librería de OpenAI, el cliente estándar para endpoints compatibles.
    """
    app.logger.info("Solicitud recibida en el endpoint / (models).")
    api_base = os.environ.get("LITELLM_API_BASE")
    api_key = os.environ.get("LITELLM_API_KEY")
    timeout = float(os.environ.get("LITELLM_TIMEOUT", 60.0))

    if not api_base:
        error_msg = "La variable de entorno LITELLM_API_BASE es obligatoria para esta operación."
        app.logger.error(error_msg)
        return jsonify({"error": error_msg}), 500
    
    if not api_key:
        error_msg = "La variable de entorno LITELLM_API_KEY es obligatoria para esta operación."
        app.logger.error(error_msg)
        return jsonify({"error": error_msg}), 500

    try:
        app.logger.info(f"Consultando la lista de modelos en: {api_base} usando el cliente de OpenAI con un timeout de {timeout}s")
        
        # Inicializar el cliente de OpenAI apuntando al proxy de LiteLLM
        client = OpenAI(
            base_url=api_base,
            api_key=api_key,
            timeout=timeout,
        )

        # Obtener la lista de modelos
        models_response = client.models.list()

        # Convertir la respuesta a una lista de diccionarios para poder serializarla a JSON
        models_list = [model.model_dump() for model in models_response.data]
        
        app.logger.info("Lista de modelos obtenida exitosamente.")
        return jsonify(models_list)

    except APIError as api_err:
        app.logger.error(f"Error de API al consultar modelos: {api_err}", exc_info=True)
        # El cuerpo del error ya suele ser un JSON, así que lo pasamos directamente
        error_details = api_err.body or {"message": str(api_err)}
        return jsonify({"error": f"Error del servicio LiteLLM al obtener modelos: {api_err.status_code}", "details": error_details}), api_err.status_code
    except Exception as e:
        app.logger.error(f"Ocurrió un error inesperado al consultar modelos: {e}", exc_info=True)
        return jsonify({"error": "Ocurrió un error interno inesperado."}), 500

@app.route('/generate', methods=['POST'])
def generate_text():
    """
    Endpoint para generar texto usando la API de LiteLLM a través del cliente de OpenAI.
    Espera un payload JSON con 'system_prompt' y 'user_prompt'.
    La configuración se lee de variables de entorno.
    """
    app.logger.info("Solicitud recibida en el endpoint /generate.")
    
    # 1. Obtener la configuración desde las variables de entorno
    api_key = os.environ.get("LITELLM_API_KEY")
    api_base = os.environ.get("LITELLM_API_BASE")
    model_name = os.environ.get("LITELLM_MODEL", "claude-3-haiku-20240307")
    timeout = float(os.environ.get("LITELLM_TIMEOUT", 60.0))
    
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

    # 3. Construir el array de mensajes
    # Se añade la instrucción de responder en JSON al prompt del sistema.
    messages = [
        {"role": "system", "content": f"{system_prompt} Responde siempre con un objeto JSON válido."},
        {"role": "user", "content": user_prompt}
    ]

    # 4. Llamar a la API usando el cliente de OpenAI
    try:
        app.logger.info(f"Iniciando llamada a la API con un timeout de {timeout}s.")
        # Inicializar el cliente de OpenAI apuntando al proxy de LiteLLM
        client = OpenAI(
            base_url=api_base,
            api_key=api_key,
            timeout=timeout,
        )

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=True,
            response_format={"type": "json_object"}, # Se fuerza la salida a JSON
        )

        generated_content = response.choices[0].message.content
        
        app.logger.info("Respuesta recibida exitosamente de LiteLLM.")
        # Como la respuesta ya es un string JSON, lo parseamos para devolver un objeto JSON real
        return jsonify({"response": generated_content})

    except APIError as api_err:
        app.logger.error(f"Error de API al generar texto: {api_err}", exc_info=True)
        error_details = api_err.body or {"message": str(api_err)}
        return jsonify({"error": f"Error del servicio LiteLLM al generar texto: {api_err.status_code}", "details": error_details}), api_err.status_code
    except Exception as e:
        app.logger.error(f"Ocurrió un error inesperado al generar texto: {e}", exc_info=True)
        return jsonify({"error": "Ocurrió un error interno inesperado."}), 500


if __name__ == '__main__':
    # El servidor de desarrollo de Flask no debe usarse en producción.
    # Gunicorn se encargará de ejecutar la app en el Dockerfile.
    app.run(host='0.0.0.0', port=5000, debug=True)

