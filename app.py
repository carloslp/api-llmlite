# -*- coding: utf-8 -*-
import os
from flask import Flask, request, jsonify
from litellm import completion
import logging

# Configurar un logging básico para ver el estado en la consola
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Inicializar la aplicación Flask
app = Flask(__name__)

@app.route('/generate', methods=['POST'])
def generate_text():
    """
    Endpoint para generar texto usando la API de LiteLLM.
    Espera un payload JSON con 'system_prompt' y 'user_prompt'.
    La configuración se lee de variables de entorno.
    """
    # 1. Obtener la configuración desde las variables de entorno
    api_key = os.environ.get("LITELLM_API_KEY")
    api_base = os.environ.get("LITELLM_API_BASE") # Nueva variable para la URL del servicio

    # A menudo, los endpoints compatibles con OpenAI residen en una ruta `/v1`.
    # Esta lógica ayuda a corregir URLs base que podrían haber omitido esta parte crucial,
    # que es una causa común del error "Method Not Allowed".
    if api_base:
        api_base = api_base.rstrip('/')
        if not api_base.endswith("/v1"):
            logging.warning("La URL base de LiteLLM no parece terminar en '/v1'. "
                            "Añadiendo '/v1' para compatibilidad con el estándar de OpenAI. "
                            "Si esto es incorrecto, ajusta la variable de entorno LITELLM_API_BASE para que incluya la ruta correcta.")
            api_base += "/v1"

    if not api_key:
        logging.error("La variable de entorno LITELLM_API_KEY no está configurada.")
        return jsonify({
            "error": "La clave de la API no está configurada. Por favor, establece la variable de entorno LITELLM_API_KEY."
        }), 500

    # 2. Validar y obtener los datos de la solicitud POST
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Payload JSON inválido o vacío."}), 400
            
        system_prompt = data.get('system_prompt')
        user_prompt = data.get('user_prompt')

        if not user_prompt:
            return jsonify({"error": "El campo 'user_prompt' es obligatorio en el cuerpo de la solicitud."}), 400
        
        if not system_prompt:
            system_prompt = "Eres un asistente servicial y conciso."

    except Exception as e:
        logging.error(f"Error al procesar el JSON de la solicitud: {e}")
        return jsonify({"error": "No se pudo procesar el cuerpo de la solicitud. Asegúrate de que sea un JSON válido."}), 400

    # 3. Construir el array de mensajes para la API de LiteLLM
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # 4. Llamar a la API de LiteLLM
    try:
        if api_base:
            logging.info(f"Enviando solicitud a la API de LiteLLM en la URL base: {api_base}")
        else:
            logging.info("Enviando solicitud a la API de LiteLLM (URL por defecto)...")

        response = completion(
            model="gemini/gemini-2.5-pro",
            messages=messages,
            api_key=api_key,
            api_base=api_base  # Se pasa la URL base a litellm
        )

        generated_content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        logging.info("Respuesta recibida exitosamente de LiteLLM.")
        return jsonify({"response": generated_content})

    except Exception as e:
        logging.error(f"Ocurrió un error al llamar a la API de LiteLLM: {e}")
        return jsonify({"error": "Ocurrió un error interno al comunicarse con el servicio del LLM."}), 502


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

