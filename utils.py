import requests

def validar_api_key_deepgram(api_key):
    """
    Verifica si la clave API de Deepgram es válida.
    """
    url = "https://api.deepgram.com/v1/projects"
    headers = {
        "Authorization": f"Token {api_key}"
    }

    try:
        response = requests.get(url, headers=headers)
        print(f"🔍 Deepgram status: {response.status_code}")
        print(response.json())
        print("✅ API key válida Deepgram.")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al conectar con Deepgram: {e}")
        return False


def verificar_openrouter_key(api_key: str) -> bool:
    """
    Verifica si la clave API de OpenRouter es válida.
    """
    url = "https://openrouter.ai/api/v1/key"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}"
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print("✅ API key válida OPENROUTER.")
            print("Detalles:", response.json())
            return True
        else:
            print(f"❌ API key no válida. Código: {response.status_code}")
            print("Respuesta:", response.text)
            return False
    except Exception as e:
        print("⚠️ Error al intentar conectar con OpenRouter:", e)
        return False
