import os
import tempfile
import threading
import customtkinter as ctk
from moviepy import AudioFileClip
import requests
from DeepGramClient import DeepgramPDFTranscriber
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import tkinter as tk
import platform
import subprocess
from PIL import Image, ImageTk
import ctypes
import utils


def obtener_area_trabajo():
    SPI_GETWORKAREA = 0x0030
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
    return rect.left, rect.top, rect.right, rect.bottom


def aplicar_pantalla_completa_sin_barra(ventana):
    left, top, right, bottom = obtener_area_trabajo()
    ancho_visible = right - left
    alto_visible = bottom - top
    offset_x = -9
    offset_y = 0
    ventana.resizable(False, False)
    ventana.geometry(f"{ancho_visible}x{alto_visible-50}+{left + offset_x}+{top + offset_y}")


class AsisVozApp(TkinterDnD.Tk):
    def __init__(self, deepgram_key):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.title("AsisVoz")
        aplicar_pantalla_completa_sin_barra(self)
        self.minsize(800, 600)

        ico_path = utils.ruta_absoluta("media/logo.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        self.selected_files = []
        self.deepgram_api_key = deepgram_key
        self.transcriptor = DeepgramPDFTranscriber(self.deepgram_api_key)

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        left_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        left_frame.pack(side="left", anchor="n", padx=(0, 20), fill="y")
        left_frame.configure(width=350)

        ctk.CTkLabel(left_frame, text="Audio", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(left_frame, text="Agrega tus archivos de audio aquí", font=ctk.CTkFont(size=12), wraplength=300, justify="left").pack(anchor="w", pady=(0, 15))

        upload_border = ctk.CTkFrame(left_frame, height=160, border_width=1, border_color="#aaaaaa")
        upload_border.pack(pady=(0, 10), fill="x")
        upload_border.pack_propagate(False)
        self._crear_area_upload(upload_border)

        self.archivos_frame = ctk.CTkFrame(left_frame, fg_color="white", corner_radius=10)
        self.archivos_frame.pack(pady=(5, 20), fill="both", expand=True)

        self.btn_transcribir = ctk.CTkButton(left_frame, text="Transcribir", height=35, command=self._on_transcribir)
        self.btn_transcribir.pack(pady=(10, 5), fill="x")
        self.btn_transcribir.pack_forget()

        self.btn_abrir_transcripcion = ctk.CTkButton(left_frame, text="Abrir transcripción generada", height=35, command=self._on_open_transcripcion)
        self.btn_abrir_transcripcion.pack(side="bottom", anchor="w", pady=(0, 5), padx=5)
        self.btn_abrir_transcripcion.pack_forget()

        self.status_label = ctk.CTkLabel(left_frame, text="", text_color="black")
        self.status_label.pack(anchor="w", pady=(0, 5))

        self.lbl_saldo = ctk.CTkLabel(self, text=self.obtener_balance_deepgram(), font=ctk.CTkFont(size=13, weight="bold"), text_color="black", fg_color="#aaaaaa", corner_radius=10, padx=5, pady=15)
        self.lbl_saldo.place(relx=0.96, rely=0.01, anchor="ne")

        self.historial_archivo = "historial.txt"
        self.historial_transcripciones = self._cargar_historial()
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        self.historial_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Historial", menu=self.historial_menu)
        self._actualizar_menu_historial()
        utils.reproducir_sonido("inicio")

        self.gif_path = "media/cargando.gif"
        self.gif_frames = []
        self.current_frame = 0
        if os.path.exists(self.gif_path):
            self._cargar_frames_gif()

    def _set_status(self, texto: str):
        try:
            self.status_label.configure(text=texto)
        except Exception:
            pass

    def _cargar_frames_gif(self):
        imagen = Image.open(self.gif_path)
        try:
            while True:
                frame = imagen.copy().convert("RGBA").resize((100, 100), Image.LANCZOS)
                self.gif_frames.append(ImageTk.PhotoImage(frame))
                imagen.seek(len(self.gif_frames))
        except EOFError:
            pass
        self.gif_label = ctk.CTkLabel(self, text="")

    def _mostrar_gif_cargando(self):
        if not self.gif_frames:
            return
        self.gif_label.place(relx=0.05, rely=0.9, x=15, anchor="sw")
        self._gif_frame_index = 0
        self._reproducir_gif()

    def _reproducir_gif(self):
        frame = self.gif_frames[self._gif_frame_index]
        self.gif_label.configure(image=frame)
        self.gif_label.image = frame
        self._gif_frame_index = (self._gif_frame_index + 1) % len(self.gif_frames)
        self._gif_job = self.after(100, self._reproducir_gif)

    def _ocultar_gif_cargando(self):
        if hasattr(self, 'gif_label'):
            self.gif_label.place_forget()
        if hasattr(self, '_gif_job'):
            self.after_cancel(self._gif_job)

    def _crear_area_upload(self, contenedor):
        ctk.CTkLabel(contenedor, text="⬆", font=ctk.CTkFont(size=32)).pack(pady=(10, 5))
        ctk.CTkLabel(contenedor, text="Arrastra tus archivos de audio\npara comenzar la carga", font=ctk.CTkFont(size=11), wraplength=280, justify="center").pack()
        ctk.CTkLabel(contenedor, text="O", font=ctk.CTkFont(size=11)).pack(pady=5)
        ctk.CTkButton(contenedor, text="Buscar archivos de audio", command=self._on_browse_files).pack()
        contenedor.drop_target_register(DND_FILES)
        contenedor.dnd_bind('<<Drop>>', self._on_drop_files)

    def _on_drop_files(self, event):
        archivos = self.tk.splitlist(event.data)
        extensiones_validas = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.webm', '.opus')
        archivo_valido = next((archivo for archivo in archivos if archivo.lower().endswith(extensiones_validas)), None)
        if not archivo_valido:
            messagebox.showerror("Error", "Por favor arrastra un archivo de audio válido.")
            return
        self.selected_files = [archivo_valido]
        self.archivos_frame.pack_forget()
        self.archivos_frame.pack(pady=(5, 20), fill="x")
        self.btn_transcribir.pack(pady=(10, 5), fill="x")
        self._actualizar_lista_archivos()
        nombre_base = os.path.splitext(os.path.basename(self.selected_files[0]))[0]
        self.nombre_word = f"{nombre_base}.docx"
        self._set_status("✔ Archivo cargado correctamente")

    def _on_browse_files(self):
        tipos_permitidos = [("Audio files", "*.mp3 *.wav *.m4a *.flac *.ogg *.aac *.webm *.opus *.mp4")]
        ruta = filedialog.askopenfilename(title="Selecciona un archivo de audio", filetypes=tipos_permitidos)
        if not ruta:
            return
        extensiones_validas = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.webm', '.opus', '.mp4')
        if not ruta.lower().endswith(extensiones_validas):
            messagebox.showerror("Error", "Por favor selecciona un archivo de audio válido.")
            return
        self.btn_transcribir.pack_forget()
        try:
            if ruta.lower().endswith('.mp4'):
                nombre_base = os.path.splitext(os.path.basename(ruta))[0]
                self._set_status("📼 Archivo .mp4 detectado. Convirtiendo a .mp3...")
                tmp_dir = tempfile.gettempdir()
                ruta_convertida = os.path.join(tmp_dir, f"{nombre_base}.mp3")
                audio_clip = AudioFileClip(ruta)
                audio_clip.write_audiofile(ruta_convertida, logger=None)
                audio_clip.close()
                self.selected_files = [ruta_convertida]
                self._set_status("🔁 Conversión a .mp3 completada con éxito ✅")
            else:
                self.selected_files = [ruta]
        except Exception as e:
            messagebox.showerror("Error al procesar", f"Ocurrió un problema al cargar el archivo:\n{e}")
            return
        self._actualizar_lista_archivos()
        self.archivos_frame.pack_forget()
        self.archivos_frame.pack(pady=(5, 20), fill="x")
        try:
            nombre_base = os.path.splitext(os.path.basename(self.selected_files[0]))[0]
            self.nombre_word = f"{nombre_base}.docx"
        except Exception:
            self.nombre_word = "transcripcion.docx"
        self._set_status("✔ Archivo cargado correctamente")
        self.btn_transcribir.pack(pady=(10, 5), fill="x")

    def _actualizar_lista_archivos(self):
        for widget in self.archivos_frame.winfo_children():
            widget.destroy()
        for ruta in self.selected_files:
            nombre = os.path.basename(ruta)
            fila = ctk.CTkFrame(self.archivos_frame, fg_color="transparent")
            fila.pack(anchor="w", fill="x", padx=5, pady=2)
            ctk.CTkLabel(fila, text=nombre, anchor="w", wraplength=250).pack(side="left", padx=(5, 0), fill="x", expand=True)
            ctk.CTkButton(fila, text="🗑", width=30, fg_color="#d9534f", hover_color="#c9302c", command=lambda r=ruta: self._eliminar_archivo(r)).pack(side="right", padx=5)

    def _eliminar_archivo(self, ruta):
        respuesta = messagebox.askyesno("Confirmar eliminación", "¿Estás seguro de eliminar el audio? Se eliminará la transcripción generada.")
        if respuesta and ruta in self.selected_files:
            self.selected_files.remove(ruta)
            self.btn_abrir_transcripcion.pack_forget()
            self.btn_transcribir.pack_forget()
            self.archivos_frame.pack_forget()
            self.archivos_frame.pack(pady=(5, 20), fill="both", expand=True)
            self._actualizar_lista_archivos()

    def _on_transcribir(self):
        if not self.selected_files:
            messagebox.showinfo("Sin archivos", "Primero selecciona archivos.")
            return
        self.btn_transcribir.configure(text="Transcribiendo...", state="disabled")
        self.btn_abrir_transcripcion.pack_forget()
        carpeta_destino = filedialog.askdirectory(title="Selecciona una carpeta para guardar el Word")
        if not carpeta_destino:
            messagebox.showinfo("Cancelado", "No se seleccionó ninguna carpeta.")
            self.btn_transcribir.configure(text="Transcribir", state="normal")
            return
        nombre_base = os.path.splitext(os.path.basename(self.selected_files[0]))[0]
        nombre_base = (nombre_base[:70] + '...') if len(nombre_base) > 50 else nombre_base
        self.nombre_word = os.path.join(carpeta_destino, f"{nombre_base}.docx")
        def tarea():
            try:
                ruta = self.selected_files[0]
                self.after(0, self._mostrar_gif_cargando)
                self.btn_transcribir.configure(text="Transcribiendo...", state="disabled")
                self.transcriptor.transcribir_audio(ruta, self.nombre_word)
                self.after(0, self._transcripcion_exitosa)
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                self.after(0, self._ocultar_gif_cargando)
                self.after(0, lambda: self.btn_transcribir.configure(text="Transcribir", state="normal"))
        threading.Thread(target=tarea, daemon=True).start()

    def _transcripcion_exitosa(self):
        self._guardar_en_historial(self.nombre_word)
        try:
            self.calcular_costo_transcripcion()
        except Exception:
            pass
        self._set_status(f"✔ Transcripción completada: {self.nombre_word}")
        utils.reproducir_sonido("inicio")
        self.btn_abrir_transcripcion.pack(pady=(5, 0))
        self.lbl_saldo.configure(text=self.obtener_balance_deepgram())

    def _on_open_transcripcion(self):
        if not hasattr(self, "nombre_word"):
            messagebox.showerror("Error", "No se ha generado ningún Word.")
            return
        ruta_word = self.nombre_word
        if not os.path.exists(ruta_word):
            messagebox.showerror("Archivo no encontrado", f"No se encontró el archivo {ruta_word}.")
            return
        sistema = platform.system()
        if sistema == "Windows":
            os.startfile(ruta_word)
        elif sistema == "Darwin":
            subprocess.call(["open", ruta_word])
        else:
            subprocess.call(["xdg-open", ruta_word])

    def _cargar_historial(self):
        if not os.path.exists(self.historial_archivo):
            return []
        with open(self.historial_archivo, "r", encoding="utf-8") as f:
            lineas = [line.strip() for line in f.readlines() if line.strip()]
        return lineas[-20:]

    def _guardar_en_historial(self, ruta_word):
        self.historial_transcripciones.append(ruta_word)
        self.historial_transcripciones = self.historial_transcripciones[-20:]
        with open(self.historial_archivo, "a", encoding="utf-8") as f:
            f.write(ruta_word + "\n")
        self._actualizar_menu_historial()

    def _actualizar_menu_historial(self):
        if not hasattr(self, 'historial_menu'):
            return
        self.historial_menu.delete(0, tk.END)
        if not self.historial_transcripciones:
            self.historial_menu.add_command(label="(Sin historial)", state="disabled")
        else:
            for ruta in reversed(self.historial_transcripciones):
                nombre = os.path.basename(ruta)
                self.historial_menu.add_command(label=nombre, command=lambda r=ruta: self._abrir_transcripcion_desde_historial(r))

    def _abrir_transcripcion_desde_historial(self, ruta_word):
        if not os.path.exists(ruta_word):
            messagebox.showerror("Error", f"No se encontró el archivo:\n{ruta_word}")
            return
        try:
            sistema = platform.system()
            if sistema == "Windows":
                os.startfile(ruta_word)
            elif sistema == "Darwin":
                subprocess.call(["open", ruta_word])
            else:
                subprocess.call(["xdg-open", ruta_word])
        except Exception as e:
            messagebox.showerror("Error al abrir archivo", f"No se pudo abrir:\n{ruta_word}\n\n{e}")

    def obtener_balance_deepgram(self) -> str:
        try:
            project_id = utils.obtener_project_id_deepgram(self.deepgram_api_key)
            if not project_id:
                return "❗ No se encontró ningún balance disponible."
            url = f"https://api.deepgram.com/v1/projects/{project_id}/balances"
            headers = {"Authorization": f"Token {self.deepgram_api_key}"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            balances = data.get("balances", [])
            if balances:
                amount = balances[0].get("amount")
                self.balance_actual = amount
                return f"Saldo Deepgram: ${amount:.2f} USD"
            return "❗ No se encontró ningún balance disponible."
        except Exception as e:
            print(f"❌ Error al obtener balance de Deepgram: {e}")
            return "❌ Error al obtener balance."

    def calcular_costo_transcripcion(self) -> str:
        try:
            balance_previo = getattr(self, 'balance_actual', None)
            self.obtener_balance_deepgram()
            balance_nuevo = getattr(self, 'balance_actual', None)
            if balance_previo is None or balance_nuevo is None:
                return "No hay datos suficientes para calcular el costo."
            costo_usd = balance_previo - balance_nuevo
            return f"🧾 Costo de la transcripción: {costo_usd:.2f} USD"
        except Exception:
            return ""

