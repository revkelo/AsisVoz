import tkinter as tk
from tkinter import filedialog, messagebox
from cryptography.fernet import Fernet
import json

class CifradorDeClaves:
    CLAVE_FIJA = b'K9TOUzAY5sQWnrsMfSrSWS9MD9KTv6c_Btf5n65_1Lc='

    def __init__(self):
        self.fernet = Fernet(self.CLAVE_FIJA)

    def cifrar_archivo(self, ruta_archivo):
        try:
            with open(ruta_archivo, "rb") as file:
                datos = file.read()

            datos_cifrados = self.fernet.encrypt(datos)
            ruta_salida = ruta_archivo + ".cif"

            with open(ruta_salida, "wb") as file:
                file.write(datos_cifrados)

            messagebox.showinfo("Éxito", f"✅ Archivo cifrado:\n{ruta_salida}")
        except Exception as e:
            messagebox.showerror("Error", f"❌ Error al cifrar:\n{e}")

    def descifrar_y_extraer_claves(self, ruta_cifrado):
        try:
            with open(ruta_cifrado, "rb") as file:
                datos_cifrados = file.read()

            datos = self.fernet.decrypt(datos_cifrados)

            try:
                texto = datos.decode("utf-8")
                json_data = json.loads(texto)

                openrouter_api_key = json_data.get("openrouter_api_key")
                deepgram_api_key = json_data.get("deepgram_api_key")

                print("🔐 Claves extraídas del archivo JSON:")
                print(f"🔑 OpenRouter API Key: {openrouter_api_key}")
                print(f"🔑 Deepgram API Key:   {deepgram_api_key}")

                messagebox.showinfo("Éxito", "✅ Claves extraídas y mostradas en consola.")
            except Exception as e:
                messagebox.showerror("Error", f"⚠️ No se pudo leer como JSON:\n{e}")
                print("❌ Error al interpretar el contenido como JSON:", e)

        except Exception as e:
            messagebox.showerror("Error", f"❌ Error al descifrar:\n{e}")

    def seleccionar_y_cifrar(self):
        ruta = filedialog.askopenfilename(title="Selecciona el archivo a cifrar")
        if ruta:
            self.cifrar_archivo(ruta)

    def seleccionar_y_descifrar_extraer(self):
        ruta = filedialog.askopenfilename(title="Selecciona el archivo .cif")
        if ruta:
            self.descifrar_y_extraer_claves(ruta)

    def iniciar_app(self):
        ventana = tk.Tk()
        ventana.title("Cifrado y Lectura de Claves")
        ventana.geometry("350x200")
        ventana.resizable(False, False)

        tk.Label(ventana, text="Cifra y extrae claves desde JSON cifrado", font=("Arial", 12)).pack(pady=15)

        tk.Button(ventana, text="Cifrar archivo", command=self.seleccionar_y_cifrar,
                  bg="#4CAF50", fg="white", font=("Arial", 10), padx=10, pady=5).pack(pady=5)

        tk.Button(ventana, text="Descifrar y mostrar claves", command=self.seleccionar_y_descifrar_extraer,
                  bg="#2196F3", fg="white", font=("Arial", 10), padx=10, pady=5).pack(pady=5)

        ventana.mainloop()

if __name__ == "__main__":
    app = CifradorDeClaves()
    app.iniciar_app()
