import json
import os
import requests
import customtkinter as ctk
from tkinter import messagebox
from cryptography.fernet import Fernet
from utils import (
    guardar_claves_cifradas,
    validar_api_key_deepgram,
    verificar_openrouter_key,

    
)
import utils




# ✅ Valida ambas claves
def validar_claves(deepgram_key, openrouter_key):
    return validar_api_key_deepgram(deepgram_key) and verificar_openrouter_key(openrouter_key)



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


class VentanaLicencia(ctk.CTkToplevel):
    def __init__(self, root, openrouter_key, deepgram_key):
        super().__init__(root)

        self.center_window()
        self.title("Registrar Licencia")
        self.geometry("500x250")
        ico_path = utils.ruta_absoluta("media/logo.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass
        self.resizable(False, False)

        ctk.set_appearance_mode("light")  
        ctk.set_default_color_theme("blue")

        # Deepgram API Key
        ctk.CTkLabel(self, text="Deepgram API Key:").pack(pady=(15, 5))
        frame_deepgram = ctk.CTkFrame(self, fg_color="transparent")
        frame_deepgram.pack(pady=5, padx=10, fill="x")

        self.entry_deepgram = ctk.CTkEntry(frame_deepgram, show="*", width=360)
        if deepgram_key:
            self.entry_deepgram.insert(0, deepgram_key)
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
        if openrouter_key:
            self.entry_openrouter.insert(0, openrouter_key)
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

        if not os.path.exists("config.json.cif") or os.path.getsize("config.json.cif") == 0:
            claves = {
                "openrouter_key": openrouter_key,
                "deepgram_key": deepgram_key
            }

            try:
                with open("config.json", "w") as f:
                    json.dump(claves, f)

                utils.cifrar_archivo("config.json", "config.json.cif")
                os.remove("config.json")
            except Exception as e:
                print(f"❌ Error al crear el archivo cifrado desde ventana: {e}")
                messagebox.showerror("Error", f"No se pudo crear el archivo cifrado: {e}")
                return
        
        utils.DEEPGRAM_API_KEY = deepgram_key
        utils.OPENROUTER_API_KEY = openrouter_key

        # ✅ Guardar cifrado
        exito = guardar_claves_cifradas(openrouter_key, deepgram_key)
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


