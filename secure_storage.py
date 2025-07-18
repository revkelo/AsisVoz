# secure_storage.py
from cryptography.fernet import Fernet
import os

CLAVES_FILE = "claves_cifradas.dat"
KEY_FILE = "clave_secreta.key"

# Generar una clave secreta una vez y guardarla
def generar_clave_secreta():
    if not os.path.exists(KEY_FILE):
        with open(KEY_FILE, "wb") as f:
            f.write(Fernet.generate_key())

def obtener_fernet():
    with open(KEY_FILE, "rb") as f:
        clave = f.read()
    return Fernet(clave)

# Guardar las claves cifradas
def guardar_claves(deepgram_key, openrouter_key):
    fernet = obtener_fernet()
    texto = f"{deepgram_key}||{openrouter_key}"
    datos_cifrados = fernet.encrypt(texto.encode())
    with open(CLAVES_FILE, "wb") as f:
        f.write(datos_cifrados)

# Leer y descifrar las claves
def cargar_claves():
    if not os.path.exists(CLAVES_FILE) or not os.path.exists(KEY_FILE):
        return "", ""
    fernet = obtener_fernet()
    with open(CLAVES_FILE, "rb") as f:
        datos_cifrados = f.read()
    try:
        texto = fernet.decrypt(datos_cifrados).decode()
        deepgram, openrouter = texto.split("||")
        return deepgram, openrouter
    except:
        return "", ""
