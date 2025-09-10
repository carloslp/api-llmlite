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
    La clave de la API de LiteLLM se lee de la variable de entorno 'LITELLM_API_KEY'.
    """
    # 1. Obtener la clave de la API desde las variables de entorno
    # Esta es la forma segura de manejar credenciales.
    api_key = os.environ.get("LITELLM_API_KEY")
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
        
        # El prompt del sistema es opcional. Si no se proporciona, se usa uno por defecto.
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
        logging.info("Enviando solicitud a la API de LiteLLM...")
        response = completion(
            model="claude-3-haiku-20240307",  # Un modelo rápido y eficiente como ejemplo
            messages=messages,
            api_key=api_key
        )

        # Extraer el contenido de la respuesta. La estructura puede variar ligeramente.
        # Usamos .get() para evitar errores si una clave no existe.
        generated_content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        logging.info("Respuesta recibida exitosamente de LiteLLM.")
        return jsonify({"response": generated_content})

    except Exception as e:
        logging.error(f"Ocurrió un error al llamar a la API de LiteLLM: {e}")
        # Es una buena práctica no exponer los detalles del error al cliente
        return jsonify({"error": "Ocurrió un error interno al comunicarse con el servicio del LLM."}), 502


if __name__ == '__main__':
    # El servidor se ejecuta en el puerto 5000 y es accesible desde cualquier IP (0.0.0.0)
    # debug=True es útil para desarrollo, ya que reinicia el servidor con cada cambio.
    app.run(host='0.0.0.0', port=5000, debug=True)
