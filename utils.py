import json
import requests
from cryptography.fernet import Fernet

# ------------------ CONSTANTES ------------------
CLAVE_FIJA = b'K9TOUzAY5sQWnrsMfSrSWS9MD9KTv6c_Btf5n65_1Lc='
fernet = Fernet(CLAVE_FIJA)
RUTA_ARCHIVO = "config.json.cif"
# ------------------ VARIABLES GLOBALES ------------------
OPENROUTER_API_KEY = None
DEEPGRAM_API_KEY = None

# ------------------ FUNCIONES API KEYS ------------------

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
        print(f"🔍 OpenRouter status: {response.status_code}")
        print(response.json())
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error al conectar con OpenRouter: {e}")
        return False



def descifrar_y_extraer_claves():
    """
    Descifra un archivo .cif y extrae claves API desde JSON.
    Las guarda en variables globales OPENROUTER_API_KEY y DEEPGRAM_API_KEY.
    """
    global OPENROUTER_API_KEY, DEEPGRAM_API_KEY

    try:
        with open(RUTA_ARCHIVO, "rb") as f:
            datos_cifrados = f.read()
        descifrado = fernet.decrypt(datos_cifrados)
        datos_json = json.loads(descifrado.decode("utf-8"))

        OPENROUTER_API_KEY = datos_json.get("openrouter_api_key")
        DEEPGRAM_API_KEY = datos_json.get("deepgram_api_key")

        return {
            "openrouter_api_key": OPENROUTER_API_KEY,
            "deepgram_api_key": DEEPGRAM_API_KEY
        }
    except Exception as e:
        print(f"❌ Error al descifrar o extraer claves: {e}")
        return None

def guardar_claves_cifradas( openrouter_key, deepgram_key):
    """
    Cifra las claves API y las guarda como un archivo .cif
    """
    try:
        claves_dict = {
            "openrouter_api_key": openrouter_key,
            "deepgram_api_key": deepgram_key
        }
        datos_json = json.dumps(claves_dict).encode("utf-8")
        datos_cifrados = fernet.encrypt(datos_json)

        with open(RUTA_ARCHIVO, "wb") as f:
            f.write(datos_cifrados)

        print(f"✅ Claves cifradas guardadas en: {RUTA_ARCHIVO}")
        return True
    except Exception as e:
        print(f"❌ Error al guardar claves cifradas: {e}")
        return False

def guardar_claves_cifradas( openrouter_key, deepgram_key):
    try:
        # Construimos el diccionario que queremos guardar
        datos = {
            "openrouter_api_key": openrouter_key,
            "deepgram_api_key": deepgram_key
        }

        # Serializamos y ciframos con la CLAVE_FIJA
        datos_json = json.dumps(datos).encode("utf-8")
        datos_cifrados = fernet.encrypt(datos_json)

        # Sobrescribimos el archivo original cifrado
        with open(RUTA_ARCHIVO, "wb") as f:
            f.write(datos_cifrados)

        return True
    except Exception as e:
        print(f"❌ Error al guardar claves cifradas: {e}")
        return False