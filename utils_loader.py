import json
from cryptography.fernet import Fernet
import utils


def load_deepgram_key() -> bool:
    """
    Descifra `config.json.cif` y carga la clave de Deepgram en utils.DEEPGRAM_API_KEY.
    Acepta tanto "deepgram_api_key" como "deepgram_key" en el JSON.
    Devuelve True si cargó una clave válida; False en caso contrario.
    """
    try:
        with open(utils.RUTA_ARCHIVO, "rb") as f:
            data = f.read()
        # Usa la misma clave fija y fernet que en utils
        fernet = Fernet(utils.CLAVE_FIJA)
        decrypted = fernet.decrypt(data)
        payload = json.loads(decrypted.decode("utf-8"))
        key = payload.get("deepgram_api_key") or payload.get("deepgram_key")
        if not key:
            return False
        utils.DEEPGRAM_API_KEY = key
        return True
    except Exception:
        return False

