import json
import os
import requests
import customtkinter as ctk
from tkinter import messagebox
from utils import validar_api_key_deepgram, verificar_openrouter_key

CONFIG_FILE = "config2.json"
keys_data = {
    "deepgram_api_key": "",
    "openrouter_api_key": ""
}


# Obtener variable de interes
def obtener_project_id_deepgram(api_key):
    try:
        headers = {
            "Authorization": f"Token {api_key}"
        }
        response = requests.get("https://api.deepgram.com/v1/projects", headers=headers)
        if response.status_code == 200:
            data = response.json()
            # Tomamos el primer proyecto (o puedes ajustar para seleccionar uno específico)
            project_id = data["projects"][0]["project_id"]
            return project_id
        else:
            print(f"Error al obtener project_id: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Excepción al obtener project_id: {e}")
    return None

# Cargar claves desde el archivo
def cargar_keys():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                keys_data.update(data)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo de configuración:\n{e}")

# Guardar claves en el archivo
def guardar_keys_en_archivo():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(keys_data, f, indent=4)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo guardar el archivo de configuración:\n{e}")


    
# Ventana para registrar licencias
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

        # Validar claves antes de guardar
        if not validar_api_key_deepgram(deepgram_key):
            messagebox.showerror("Clave inválida", "La clave de Deepgram no es válida o ha sido rechazada.")
            return

        if not verificar_openrouter_key(openrouter_key):
            messagebox.showerror("Clave inválida", "La clave de OpenRouter no es válida o ha sido rechazada.")
            return


        # Si es válida, guardamos
        keys_data["deepgram_api_key"] = deepgram_key
        keys_data["openrouter_api_key"] = openrouter_key
        guardar_keys_en_archivo()
        messagebox.showinfo("Guardado", "Las claves han sido guardadas correctamente.")
        self.destroy()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
