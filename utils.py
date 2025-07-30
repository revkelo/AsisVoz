import json
import os
import sys
import requests
from cryptography.fernet import Fernet

# ------------------ CONSTANTES ------------------
CLAVE_FIJA = b'K9TOUzAY5sQWnrsMfSrSWS9MD9KTv6c_Btf5n65_1Lc='
fernet = Fernet(CLAVE_FIJA)
RUTA_ARCHIVO = "config.json.cif"
# ------------------ VARIABLES GLOBALES ------------------
OPENROUTER_API_KEY = ""
DEEPGRAM_API_KEY = ""

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



"""Devuelve ruta absoluta para ejecución directa"""
def ruta_absoluta(relative_path):
  
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def cifrar_archivo(path_entrada, path_salida=None):
    """
    Cifra un archivo con Fernet y lo guarda con extensión .cif.
    """
    try:
        with open(path_entrada, "rb") as f:
            datos = f.read()
        cifrado = fernet.encrypt(datos)
        if not path_salida:
            path_salida = path_entrada + ".cif"
        with open(path_salida, "wb") as f:
            f.write(cifrado)
        print(f"✅ Archivo cifrado guardado en: {path_salida}")
    except Exception as e:
        print(f"❌ Error al cifrar: {e}")

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

        openrouter = datos_json.get("openrouter_api_key")
        deepgram = datos_json.get("deepgram_api_key")

    # Validar que no estén vacías
        if not openrouter or not deepgram:
            print("⚠️ Las claves están vacías o incompletas.")
            return None

        OPENROUTER_API_KEY = openrouter
        DEEPGRAM_API_KEY = deepgram

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

# ✅ Obtener project_id (no se usa ahora, pero útil si lo necesitas después)
def obtener_project_id_deepgram(api_key):
    try:
        headers = {"Authorization": f"Token {api_key}"}
        response = requests.get("https://api.deepgram.com/v1/projects", headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data["projects"][0]["project_id"]
        else:
            print(f"Error al obtener project_id: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Excepción al obtener project_id: {e}")
    return None