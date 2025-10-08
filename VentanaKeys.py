import json
import os
import customtkinter as ctk
from tkinter import messagebox
from cryptography.fernet import Fernet
from utils import (
    guardar_clave_deepgram_cifrada,
    validar_api_key_deepgram,
)
import utils


def validar_claves(deepgram_key):
    return validar_api_key_deepgram(deepgram_key)


class VentanaLicencia(ctk.CTkToplevel):
    def __init__(self, root, deepgram_key):
        super().__init__(root)

        self.center_window()
        self.title("Registrar Licencia")
        self.geometry("500x200")
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
            text="Mostrar",
            command=self.toggle_deepgram_visibility,
            width=30
        )
        self.show_deepgram.pack(side="left")

        # Botón guardar
        ctk.CTkButton(self, text="Guardar Claves", command=self.guardar_keys, width=200).pack(pady=25)

        self.protocol("WM_DELETE_WINDOW", lambda: self.withdraw())

    def toggle_deepgram_visibility(self):
        self.entry_deepgram.configure(show="" if self.show_deepgram.get() else "*")

    def guardar_keys(self):
        deepgram_key = self.entry_deepgram.get().strip()

        if not deepgram_key:
            messagebox.showerror("Error", "Por favor ingresa la clave de Deepgram.")
            return

        if not validar_claves(deepgram_key):
            messagebox.showerror("Error", "La clave de Deepgram no es válida.")
            return

        if not os.path.exists("config.json.cif") or os.path.getsize("config.json.cif") == 0:
            claves = {
                "deepgram_key": deepgram_key
            }

            try:
                with open("config.json", "w") as f:
                    json.dump(claves, f)

                utils.cifrar_archivo("config.json", "config.json.cif")
                os.remove("config.json")
            except Exception as e:
                print(f"Error al crear el archivo cifrado desde ventana: {e}")
                messagebox.showerror("Error", f"No se pudo crear el archivo cifrado: {e}")
                return

        utils.DEEPGRAM_API_KEY = deepgram_key

        exito = guardar_clave_deepgram_cifrada(deepgram_key)
        if exito:
            messagebox.showinfo("Guardado", "La clave ha sido guardada correctamente.")
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



