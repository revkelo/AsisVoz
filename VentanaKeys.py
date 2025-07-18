import json
import os
import requests
import customtkinter as ctk
from tkinter import messagebox
from cryptography.fernet import Fernet
from utils import (
    CLAVE_FIJA,
    validar_api_key_deepgram,
    verificar_openrouter_key,
    descifrar_y_extraer_claves
    
)

FERNET = Fernet(CLAVE_FIJA)

# Constantes
ARCHIVO_CLAVES = "config.json.cif"
keys_data = {}

# ✅ Valida ambas claves
def validar_claves(deepgram_key, openrouter_key):
    return validar_api_key_deepgram(deepgram_key) and verificar_openrouter_key(openrouter_key)

def cargar_keys():
        from utils import descifrar_y_extraer_claves
        return descifrar_y_extraer_claves("config.json.cif")

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

# ✅ Carga las claves descifradas al iniciar
claves_temp = descifrar_y_extraer_claves(ARCHIVO_CLAVES)
if claves_temp:
    keys_data["deepgram_api_key"] = claves_temp.get("deepgram_api_key", "")
    keys_data["openrouter_api_key"] = claves_temp.get("openrouter_api_key", "")

# ✅ Ventana principal para ingresar claves
class VentanaLicencia(ctk.CTkToplevel):
    def __init__(self, root):
        super().__init__(root)

        self.title("Registrar Licencia")
        self.geometry("500x250")
        self.resizable(False, False)
        self.center_window()

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # Deepgram API Key
        ctk.CTkLabel(self, text="Deepgram API Key:").pack(pady=(15, 5))
        frame_deepgram = ctk.CTkFrame(self, fg_color="transparent")
        frame_deepgram.pack(pady=5, padx=10, fill="x")

        self.entry_deepgram = ctk.CTkEntry(frame_deepgram, show="*", width=360)
        self.entry_deepgram.insert(0, keys_data.get("deepgram_api_key", ""))
        self.entry_deepgram.pack(side="left", padx=(0, 10), expand=True, fill="x")

        self.show_deepgram = ctk.CTkCheckBox(
            frame_deepgram,
            text="👁",
            command=self.toggle_deepgram_visibility,
            width=30
        )
        self.show_deepgram.pack(side="left")

        # OpenRouter API Key
        ctk.CTkLabel(self, text="OpenRouter API Key:").pack(pady=(10, 5))
        frame_openrouter = ctk.CTkFrame(self, fg_color="transparent")
        frame_openrouter.pack(pady=5, padx=10, fill="x")

        self.entry_openrouter = ctk.CTkEntry(frame_openrouter, show="*", width=360)
        self.entry_openrouter.insert(0, keys_data.get("openrouter_api_key", ""))
        self.entry_openrouter.pack(side="left", padx=(0, 10), expand=True, fill="x")

        self.show_openrouter = ctk.CTkCheckBox(
            frame_openrouter,
            text="👁",
            command=self.toggle_openrouter_visibility,
            width=30
        )
        self.show_openrouter.pack(side="left")

        # Botón guardar
        ctk.CTkButton(self, text="Guardar Claves", command=self.guardar_keys, width=200).pack(pady=25)

        self.protocol("WM_DELETE_WINDOW", lambda: self.withdraw())

    def toggle_deepgram_visibility(self):
        self.entry_deepgram.configure(show="" if self.show_deepgram.get() else "*")

    def toggle_openrouter_visibility(self):
        self.entry_openrouter.configure(show="" if self.show_openrouter.get() else "*")

    def guardar_keys(self):
        deepgram_key = self.entry_deepgram.get().strip()
        openrouter_key = self.entry_openrouter.get().strip()

        if not deepgram_key or not openrouter_key:
            messagebox.showerror("Error", "Por favor ingresa ambas claves.")
            return

        if not validar_claves(deepgram_key, openrouter_key):
            messagebox.showerror("Error", "Alguna de las claves no es válida.")
            return

        # Guardar en memoria
        keys_data["deepgram_api_key"] = deepgram_key
        keys_data["openrouter_api_key"] = openrouter_key

        # ✅ Guardar cifrado
        exito = guardar_claves_cifradas(ARCHIVO_CLAVES, openrouter_key, deepgram_key)
        if exito:
            messagebox.showinfo("Guardado", "Las claves han sido guardadas correctamente.")
            self.destroy()
        else:
            messagebox.showerror("Error", "No se pudo guardar el archivo cifrado.")


    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

def guardar_claves_cifradas(path_salida, openrouter_key, deepgram_key):
    try:
        # Construimos el diccionario que queremos guardar
        datos = {
            "openrouter_api_key": openrouter_key,
            "deepgram_api_key": deepgram_key
        }

        # Serializamos y ciframos con la CLAVE_FIJA
        datos_json = json.dumps(datos).encode("utf-8")
        datos_cifrados = FERNET.encrypt(datos_json)

        # Sobrescribimos el archivo original cifrado
        with open(path_salida, "wb") as f:
            f.write(datos_cifrados)

        return True
    except Exception as e:
        print(f"❌ Error al guardar claves cifradas: {e}")
        return False
