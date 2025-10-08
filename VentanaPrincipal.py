# ---------- VentanaPrincipal.py (sin tkinterdnd2: Transcriptor + Grabadora) ----------
import os
import time
import tempfile
import threading
import platform
import subprocess
import ctypes
from ctypes import wintypes

# UI
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# Audio (grabadora)
import numpy as np
import soundcard as sc
import soundfile as sf
import warnings
warnings.filterwarnings("ignore", category=sc.SoundcardRuntimeWarning)

# Media
from moviepy import AudioFileClip

# Red / API
import requests

# App
import utils
from DeepGramClient import DeepgramPDFTranscriber


# -------------------- Utilidades de ventana --------------------
def _obtener_area_trabajo():
    """Devuelve el área de trabajo sin incluir la barra de tareas (en Windows)"""
    SPI_GETWORKAREA = 0x0030
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
    return rect.left, rect.top, rect.right, rect.bottom


def _aplicar_pantalla_completa_sin_barra(ventana: tk.Tk):
    """Ajusta la ventana al área visible de la pantalla (sin cubrir la barra de tareas)"""
    left, top, right, bottom = _obtener_area_trabajo()
    ancho_visible = right - left
    alto_visible = bottom - top
    offset_x = -9  # corrección típica borde izq
    offset_y = 0
    ventana.resizable(False, False)
    ventana.geometry(f"{ancho_visible}x{alto_visible-50}+{left + offset_x}+{top + offset_y}")


# -------------------- Clase principal --------------------
class AsisVozApp(ctk.CTk):
    """
    Aplicación sin chatbot y sin tkinterdnd2.
    - IZQ: carga por botón, conversión .mp4 → .mp3, transcripción Deepgram a .docx,
           historial y abrir transcripción.
    - DER: grabadora (micrófono + sistema) con medidores de nivel, volúmenes y guardado .wav.
    """
    def __init__(self, deepgram_key: str):
        super().__init__()

        # Tema
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Básicos de ventana
        self.title("AsisVoz")
        _aplicar_pantalla_completa_sin_barra(self)
        self.minsize(900, 600)

        # Icono
        ico_path = utils.ruta_absoluta("media/logo.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        # ---------- Estado de transcriptor ----------
        self.selected_files = []
        self.deepgram_api_key = deepgram_key
        self.transcriptor = DeepgramPDFTranscriber(self.deepgram_api_key)

        # Historial transcripciones
        self.historial_archivo = "historial.txt"
        self.historial_transcripciones = self._cargar_historial()

        # ---------- Estado de grabadora ----------
        self.fs = 44100
        self.recording = False

        self.mic_enabled = True
        self.sys_enabled = True
        self.mic_device = None
        self.sys_device = None

        self.mic_data = []
        self.sys_data = []
        self.mic_volume = 0.3
        self.sys_volume = 0.5

        self.niveles_activos = {}     # {"mic": True/False, "sys": True/False}
        self._nivel_threads = {}
        self._inicio_grab = None

        # ---------- Layout principal ----------
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # IZQUIERDA: Transcripción
        left_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        left_frame.pack(side="left", anchor="n", padx=(0, 20), fill="y")
        left_frame.configure(width=360)

        ctk.CTkLabel(left_frame, text="Audio", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(
            left_frame, text="Agrega tus archivos de audio aquí",
            font=ctk.CTkFont(size=12), wraplength=300, justify="left"
        ).pack(anchor="w", pady=(0, 15))

        upload = ctk.CTkFrame(left_frame, height=160, border_width=1, border_color="#aaaaaa")
        upload.pack(pady=(0, 10), fill="x")
        upload.pack_propagate(False)
        self._crear_area_upload(upload)  # solo botón (sin DnD)

        # Lista de archivos
        self.archivos_frame = ctk.CTkFrame(left_frame, fg_color="white", corner_radius=10)
        self.archivos_frame.pack(pady=(5, 20), fill="both", expand=True)

        # Botones de transcripción
        self.btn_transcribir = ctk.CTkButton(left_frame, text="Transcribir", height=35, command=self._on_transcribir)
        self.btn_transcribir.pack(pady=(10, 5), fill="x")
        self.btn_transcribir.pack_forget()

        self.btn_abrir_transcripcion = ctk.CTkButton(
            left_frame, text="Abrir transcripción generada", height=35, command=self._on_open_transcripcion
        )
        self.btn_abrir_transcripcion.pack(side="bottom", anchor="w", pady=(0, 5), padx=5)
        self.btn_abrir_transcripcion.pack_forget()

        # MENÚ Historial
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        self.historial_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Historial", menu=self.historial_menu)
        self._actualizar_menu_historial()

        # SALDO (esquina superior derecha)
        self.lbl_saldo = ctk.CTkLabel(
            self,
            text=self._obtener_balance_deepgram(),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="black",
            fg_color="#aaaaaa",
            corner_radius=10,
            padx=5,
            pady=15
        )
        self.lbl_saldo.place(relx=0.965, rely=0.015, anchor="ne")

        # GIF cargando (opcional)
        self.gif_path = "media/cargando.gif"
        self.gif_frames = []
        self.current_frame = 0
        if os.path.exists(self.gif_path):
            self._cargar_frames_gif()

        # DERECHA: Grabadora
        self._build_grabadora_panel(main_parent=main_frame)

        # Sonido de inicio
        utils.reproducir_sonido("inicio")

        # Cerrar ordenado
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -------------------- Upload (solo botón) --------------------
    def _crear_area_upload(self, contenedor: ctk.CTkFrame):
        ctk.CTkLabel(contenedor, text="🎵", font=ctk.CTkFont(size=32)).pack(pady=(10, 5))
        ctk.CTkLabel(
            contenedor, text="Usa el botón para seleccionar tu audio",
            font=ctk.CTkFont(size=11), wraplength=280, justify="center"
        ).pack()
        ctk.CTkButton(contenedor, text="Buscar archivos de audio", command=self._on_browse_files).pack(pady=10)

    def _on_browse_files(self):
        tipos_permitidos = [("Audio files", "*.mp3 *.wav *.m4a *.flac *.ogg *.aac *.webm *.opus *.mp4")]
        try:
            ruta = filedialog.askopenfilename(title="Selecciona un archivo de audio", filetypes=tipos_permitidos)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el diálogo de archivos:\n{e}")
            return

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
                tmp_dir = tempfile.gettempdir()
                ruta_convertida = os.path.join(tmp_dir, f"{nombre_base}.mp3")

                self._reproducir_gif()
                clip = AudioFileClip(ruta)
                clip.write_audiofile(ruta_convertida, logger=None)
                clip.close()
                self._ocultar_gif_cargando()

                self.selected_files = [ruta_convertida]
            else:
                self.selected_files = [ruta]
        except Exception as e:
            self._ocultar_gif_cargando()
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

        self.btn_transcribir.pack(pady=(10, 5), fill="x")

    def _actualizar_lista_archivos(self):
        for w in self.archivos_frame.winfo_children():
            w.destroy()

        extensiones_validas = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.webm', '.opus', '.mp4')
        for ruta in self.selected_files:
            if not ruta.lower().endswith(extensiones_validas):
                continue
            nombre = os.path.basename(ruta)
            fila = ctk.CTkFrame(self.archivos_frame, fg_color="transparent")
            fila.pack(anchor="w", fill="x", padx=5, pady=2)

            ctk.CTkLabel(fila, text=nombre, anchor="w", wraplength=250).pack(side="left", padx=(5, 0), fill="x", expand=True)
            ctk.CTkButton(
                fila, text="❌", width=30, fg_color="#d9534f", hover_color="#c9302c",
                command=lambda r=ruta: self._eliminar_archivo(r)
            ).pack(side="right", padx=5)

    def _eliminar_archivo(self, ruta):
        respuesta = messagebox.askyesno(
            "Confirmar eliminación", "¿Estás seguro de eliminar el audio? Se eliminará la transcripción generada."
        )
        if respuesta:
            if ruta in self.selected_files:
                self.selected_files.remove(ruta)
                self.btn_abrir_transcripcion.pack_forget()
                self.btn_transcribir.pack_forget()
                self.archivos_frame.pack_forget()
                self.archivos_frame.pack(pady=(5, 20), fill="both", expand=True)
            self._actualizar_lista_archivos()

    # -------------------- Transcripción --------------------
    def _on_transcribir(self):
        if not self.selected_files:
            messagebox.showinfo("Sin archivos", "Primero selecciona archivos.")
            return

        self.btn_transcribir.configure(text="Transcribir", state="normal")
        self.btn_abrir_transcripcion.pack_forget()

        carpeta_destino = filedialog.askdirectory(title="Selecciona una carpeta para guardar el Word")
        if not carpeta_destino:
            messagebox.showinfo("Cancelado", "No se seleccionó ninguna carpeta.")
            self.btn_transcribir.configure(text="Transcribir", state="normal")
            return

        nombre_base = os.path.splitext(os.path.basename(self.selected_files[0]))[0]
        nombre_base = (nombre_base[:70] + '...') if len(nombre_base) > 50 else nombre_base
        self.nombre_word = os.path.join(carpeta_destino, f"{nombre_base}.docx")

        self.btn_transcribir.configure(text="Transcribir", state="enable")

        def tarea():
            try:
                ruta = self.selected_files[0]
                self.after(0, self._reproducir_gif)
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

        # Mostrar costo si se puede (cuando tenemos balance válido)
        if getattr(self, "balance_anterior", None) is not None and getattr(self, "balance_actual", None) is not None:
            _ = self._calcular_costo_transcripcion()

        messagebox.showinfo("Transcripción", f"✔ Transcripción completada:\n{self.nombre_word}")
        utils.reproducir_sonido("inicio")
        self.btn_abrir_transcripcion.pack(pady=(5, 0))
        self.lbl_saldo.configure(text=self._obtener_balance_deepgram())

    def _on_open_transcripcion(self):
        if not hasattr(self, "nombre_word"):
            messagebox.showerror("Error", "No se ha generado ningún Word.")
            return

        ruta_word = self.nombre_word
        if not os.path.exists(ruta_word):
            messagebox.showerror("Archivo no encontrado", f"No se encontró el archivo {ruta_word}.")
            return

        sistema = platform.system()
        try:
            if sistema == "Windows":
                os.startfile(ruta_word)
            elif sistema == "Darwin":
                subprocess.call(["open", ruta_word])
            else:
                subprocess.call(["xdg-open", ruta_word])
        except Exception as e:
            messagebox.showerror("Error al abrir archivo", f"No se pudo abrir:\n{ruta_word}\n\n{e}")

    # -------------------- Historial --------------------
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
                self.historial_menu.add_command(
                    label=nombre,
                    command=lambda r=ruta: self._abrir_transcripcion_desde_historial(r)
                )

    def _abrir_transcripcion_desde_historial(self, ruta_word):
        if not os.path.exists(ruta_word):
            messagebox.showerror("Error", f"No se encontró el archivo:\n{ruta_word}")
            return
        sistema = platform.system()
        try:
            if sistema == "Windows":
                os.startfile(ruta_word)
            elif sistema == "Darwin":
                subprocess.call(["open", ruta_word])
            else:
                subprocess.call(["xdg-open", ruta_word])
        except Exception as e:
            messagebox.showerror("Error al abrir archivo", f"No se pudo abrir:\n{ruta_word}\n\n{e}")

    # -------------------- Balance / Costos Deepgram --------------------
    def _obtener_balance_deepgram(self) -> str:
        """Obtiene balance si el token tiene permisos; si no, devuelve texto amigable."""
        try:
            project_id = utils.obtener_project_id_deepgram(self.deepgram_api_key)
            if not project_id:
                self.balance_anterior = None
                self.balance_actual = None
                return "Balance no disponible"

            url = f"https://api.deepgram.com/v1/projects/{project_id}/balances"
            headers = {"Authorization": f"Token {self.deepgram_api_key}"}
            tasa_dolar_a_cop = 4000

            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code in (401, 403) or resp.status_code >= 400:
                self.balance_anterior = None
                self.balance_actual = None
                return "Balance no disponible"

            data = resp.json()
            balances = data.get("balances", [])
            if not balances:
                self.balance_anterior = None
                self.balance_actual = None
                return "Balance no disponible"

            amount = balances[0].get("amount")
            units = balances[0].get("units", "usd")

            if getattr(self, "balance_actual", None) is not None:
                self.balance_anterior = self.balance_actual
            else:
                self.balance_anterior = amount

            self.balance_actual = amount
            amount_cop = round((amount or 0) * tasa_dolar_a_cop)
            return f"${amount:.2f} {units.upper()} / ${amount_cop:,} COP"
        except Exception:
            self.balance_anterior = None
            self.balance_actual = None
            return "Balance no disponible"

    def _calcular_costo_transcripcion(self) -> str:
        tasa_dolar_a_cop = 4000
        if getattr(self, "balance_actual", None) is None:
            self._obtener_balance_deepgram()
        if getattr(self, "balance_anterior", None) is None:
            self.balance_anterior = self.balance_actual
            return "No hay datos anteriores para calcular el costo (primer registro tomado)."

        balance_previo = self.balance_anterior
        self._obtener_balance_deepgram()
        balance_nuevo = self.balance_actual

        costo_usd = balance_previo - balance_nuevo
        costo_cop = round(costo_usd * tasa_dolar_a_cop)

        if costo_usd < 0:
            return "Error: el costo calculado es negativo. Verifica el flujo de llamadas."

        messagebox.showinfo(
            "Costo de la transcripción",
            f"El costo de esta transcripción fue de: {costo_usd:.2f} USD / ${costo_cop:,} COP"
        )
        return f"🧾 Costo: {costo_usd:.2f} USD / ${costo_cop:,} COP"

    # -------------------- GIF Cargando --------------------
    def _cargar_frames_gif(self):
        try:
            imagen = Image.open(self.gif_path)
            while True:
                frame = imagen.copy().convert("RGBA").resize((90, 90), Image.LANCZOS)
                self.gif_frames.append(ImageTk.PhotoImage(frame))
                imagen.seek(len(self.gif_frames))
        except EOFError:
            pass
        if not hasattr(self, 'gif_label'):
            self.gif_label = ctk.CTkLabel(self, text="")
        self.gif_label.place(relx=0.05, rely=0.9, x=15, anchor="sw")

    def _reproducir_gif(self):
        if hasattr(self, 'gif_frames') and hasattr(self, 'gif_label') and self.gif_frames:
            frame = self.gif_frames[self.current_frame]
            self.gif_label.configure(image=frame)
            self.gif_label.image = frame
            self.current_frame = (self.current_frame + 1) % len(self.gif_frames)
            self._gif_job = self.after(100, self._reproducir_gif)

    def _ocultar_gif_cargando(self):
        if hasattr(self, '_gif_job'):
            try:
                self.after_cancel(self._gif_job)
            except Exception:
                pass
        if hasattr(self, 'gif_label'):
            self.gif_label.place_forget()

    # -------------------- Panel Grabadora --------------------
    def _build_grabadora_panel(self, main_parent: ctk.CTkFrame):
        right_frame = ctk.CTkFrame(main_parent, fg_color="transparent")
        right_frame.pack(side="left", fill="both", expand=True)

        panel_frame = ctk.CTkFrame(right_frame, border_width=1, border_color="#aaaaaa", corner_radius=15)
        panel_frame.pack(anchor="n", padx=10, pady=(40, 10), fill="both", expand=True)

        ctk.CTkLabel(panel_frame, text="🔴 Grabadora", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 0))

        # Header
        header = ctk.CTkFrame(panel_frame, height=60)
        header.pack(fill="x", padx=10, pady=(10, 5))

        self.crono_label = ctk.CTkLabel(header, text="00:00", font=("Arial", 24, "bold"))
        self.crono_label.pack(side="left", padx=10, pady=15)

        self.btn_grabar = ctk.CTkButton(
            header, text="🎙️ Grabar", fg_color="#2fa572",
            command=self._toggle_grabacion, width=120, height=40, font=("Arial", 14, "bold")
        )
        self.btn_grabar.pack(side="right", padx=10, pady=10)

        # Cuerpo
        body = ctk.CTkFrame(panel_frame)
        body.pack(fill="both", expand=True, padx=10, pady=5)

        # --- MIC ---
        mic_frame = ctk.CTkFrame(body)
        mic_frame.pack(fill="x", padx=10, pady=(10, 5))

        mic_header = ctk.CTkFrame(mic_frame)
        mic_header.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(mic_header, text="🎤", font=("Arial", 16)).pack(side="left", padx=(5, 10))
        self.switch_mic = ctk.CTkSwitch(mic_header, text="Micrófono", command=self._toggle_mic, width=50)
        self.switch_mic.pack(side="left")
        self.switch_mic.select()

        self.barra_mic = ctk.CTkProgressBar(mic_header, width=120, height=10, progress_color="#00ff00")
        self.barra_mic.pack(side="right", padx=5)
        self.barra_mic.set(0)

        # --- SYS ---
        sys_frame = ctk.CTkFrame(body)
        sys_frame.pack(fill="x", padx=10, pady=5)

        sys_header = ctk.CTkFrame(sys_frame)
        sys_header.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(sys_header, text="🔊", font=("Arial", 16)).pack(side="left", padx=(5, 10))
        self.switch_sys = ctk.CTkSwitch(sys_header, text="Sistema", command=self._toggle_sys, width=50)
        self.switch_sys.pack(side="left")
        self.switch_sys.select()

        self.barra_sys = ctk.CTkProgressBar(sys_header, width=120, height=10, progress_color="#00ff00")
        self.barra_sys.pack(side="right", padx=5)
        self.barra_sys.set(0)

        # Dispositivos
        dispositivos_mic, dispositivos_sys, self._dispositivos_dict = self._listar_dispositivos()

        self.combo_mic = ctk.CTkComboBox(
            mic_frame, values=dispositivos_mic, command=self._seleccionar_mic, width=500, height=28, font=("Arial", 11)
        )
        self.combo_mic.pack(padx=10, pady=(0, 5))

        self.combo_sys = ctk.CTkComboBox(
            sys_frame, values=dispositivos_sys, command=self._seleccionar_sys, width=500, height=28, font=("Arial", 11)
        )
        self.combo_sys.pack(padx=10, pady=(0, 5))

        # Volúmenes
        vol_frame_mic = ctk.CTkFrame(mic_frame)
        vol_frame_mic.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(vol_frame_mic, text="Vol:", font=("Arial", 10)).pack(side="left", padx=(5, 5))
        self.slider_mic = ctk.CTkSlider(vol_frame_mic, from_=0, to=1, number_of_steps=100, width=300)
        self.slider_mic.pack(side="left", padx=5)
        self.slider_mic.set(self.mic_volume)
        self.vol_label_mic = ctk.CTkLabel(vol_frame_mic, text=f"{int(self.mic_volume*100)}%", font=("Arial", 10), width=40)
        self.vol_label_mic.pack(side="left", padx=5)
        self.slider_mic.configure(command=lambda v: self._set_mic_volume(float(v)))

        vol_frame_sys = ctk.CTkFrame(sys_frame)
        vol_frame_sys.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(vol_frame_sys, text="Vol:", font=("Arial", 10)).pack(side="left", padx=(5, 5))
        self.slider_sys = ctk.CTkSlider(vol_frame_sys, from_=0, to=1, number_of_steps=100, width=300)
        self.slider_sys.pack(side="left", padx=5)
        self.slider_sys.set(self.sys_volume)
        self.vol_label_sys = ctk.CTkLabel(vol_frame_sys, text=f"{int(self.sys_volume*100)}%", font=("Arial", 10), width=40)
        self.vol_label_sys.pack(side="left", padx=5)
        self.slider_sys.configure(command=lambda v: self._set_sys_volume(float(v)))

        # Selección inicial segura
        if dispositivos_mic:
            self.combo_mic.set(dispositivos_mic[0])
            self._seleccionar_mic(dispositivos_mic[0])
        else:
            self.switch_mic.deselect()
            self.switch_mic.configure(state="disabled")
            self.combo_mic.configure(values=["(sin micrófonos)"], state="disabled")

        if dispositivos_sys:
            self.combo_sys.set(dispositivos_sys[0])
            self._seleccionar_sys(dispositivos_sys[0])
        else:
            self.switch_sys.deselect()
            self.switch_sys.configure(state="disabled")
            self.combo_sys.configure(values=["(sin audio del sistema)"], state="disabled")

    # -------------------- Grabadora: helpers --------------------
    def _listar_dispositivos(self):
        try:
            dispositivos = sc.all_microphones(include_loopback=True)
            dispositivos_dict = {}
            dispositivos_mic = []
            dispositivos_sys = []
            for d in dispositivos:
                nombre = d.name[:60] + ("..." if len(d.name) > 60 else "")
                dispositivos_dict[nombre] = d
                if getattr(d, "isloopback", False):
                    dispositivos_sys.append(nombre)
                else:
                    dispositivos_mic.append(nombre)
            return dispositivos_mic, dispositivos_sys, dispositivos_dict
        except Exception as e:
            print(f"Error obteniendo dispositivos: {e}")
            return [], [], {}

    def _set_mic_volume(self, v: float):
        self.mic_volume = v
        self.vol_label_mic.configure(text=f"{int(v*100)}%")

    def _set_sys_volume(self, v: float):
        self.sys_volume = v
        self.vol_label_sys.configure(text=f"{int(v*100)}%")

    def _toggle_mic(self):
        self.mic_enabled = self.switch_mic.get()
        if self.mic_enabled and self.mic_device:
            self._actualizar_nivel("mic", self.barra_mic, self.mic_device)
        else:
            self._detener_nivel("mic", self.barra_mic)

    def _toggle_sys(self):
        self.sys_enabled = self.switch_sys.get()
        if self.sys_enabled and self.sys_device:
            self._actualizar_nivel("sys", self.barra_sys, self.sys_device)
        else:
            self._detener_nivel("sys", self.barra_sys)

    def _seleccionar_mic(self, nombre):
        self._detener_nivel("mic", self.barra_mic)
        self.mic_device = self._dispositivos_dict.get(nombre, None)
        if self.mic_enabled and self.mic_device:
            self._actualizar_nivel("mic", self.barra_mic, self.mic_device)

    def _seleccionar_sys(self, nombre):
        self._detener_nivel("sys", self.barra_sys)
        self.sys_device = self._dispositivos_dict.get(nombre, None)
        if self.sys_enabled and self.sys_device:
            self._actualizar_nivel("sys", self.barra_sys, self.sys_device)

    def _actualizar_nivel(self, nombre, barra, device):
        self.niveles_activos[nombre] = True

        def task():
            while self.niveles_activos.get(nombre, False):
                try:
                    mic = sc.get_microphone(id=device.id, include_loopback=getattr(device, "isloopback", False))
                    with mic.recorder(samplerate=self.fs, channels=1) as rec:
                        while self.niveles_activos.get(nombre, False):
                            audio = rec.record(numframes=1024)
                            if audio is not None and len(audio) > 0:
                                if audio.ndim > 1:
                                    audio = np.mean(audio, axis=1)
                                rms = np.sqrt(np.mean(audio ** 2))
                                nivel = float(min(rms * 50.0, 1.0))
                                try:
                                    self.after(0, lambda v=nivel: barra.set(v))
                                except Exception:
                                    pass
                            time.sleep(0.05)
                except Exception:
                    try:
                        self.after(0, lambda: barra.set(0))
                    except Exception:
                        pass
                    time.sleep(0.2)

        t = threading.Thread(target=task, daemon=True)
        t.start()
        self._nivel_threads[nombre] = t

    def _detener_nivel(self, nombre, barra):
        self.niveles_activos[nombre] = False
        try:
            barra.set(0)
        except Exception:
            pass

    def _toggle_grabacion(self):
        if not self.recording:
            if not self.mic_enabled and not self.sys_enabled:
                return

            self.mic_data.clear()
            self.sys_data.clear()

            self.recording = True
            self._inicio_grab = time.time()
            self.btn_grabar.configure(text="⏹️ Detener", fg_color="red")

            # Desactivar controles
            for w in (self.switch_mic, self.switch_sys, self.combo_mic, self.combo_sys, self.slider_mic, self.slider_sys):
                try:
                    w.configure(state="disabled")
                except Exception:
                    pass

            self._actualizar_cronometro()

            if self.mic_enabled and self.mic_device:
                threading.Thread(
                    target=self._grabar_fuente, args=(self.mic_device, self.mic_data, "Mic"), daemon=True
                ).start()
            if self.sys_enabled and self.sys_device:
                threading.Thread(
                    target=self._grabar_fuente, args=(self.sys_device, self.sys_data, "Sys"), daemon=True
                ).start()
        else:
            self.recording = False
            self.btn_grabar.configure(text="🎙️ Grabar", fg_color="#2fa572")

            # Reactivar
            for w in (self.switch_mic, self.switch_sys, self.combo_mic, self.combo_sys, self.slider_mic, self.slider_sys):
                try:
                    w.configure(state="normal")
                except Exception:
                    pass

            time.sleep(0.1)
            threading.Thread(target=self._guardar_archivo_mixto, daemon=True).start()

    def _grabar_fuente(self, device, data_buffer, nombre):
        try:
            mic = sc.get_microphone(id=device.id, include_loopback=getattr(device, "isloopback", False))
            with mic.recorder(samplerate=self.fs, channels=1) as rec:
                while self.recording:
                    try:
                        audio = rec.record(numframes=2048)
                        if audio is not None and len(audio) > 0:
                            if audio.ndim > 1:
                                audio = np.mean(audio, axis=1)
                            data_buffer.append(audio)
                    except Exception:
                        break
        except Exception as e:
            print(f"Error inicializando grabación {nombre}: {e}")

    def _guardar_archivo_mixto(self):
        try:
            mic_audio = np.concatenate(self.mic_data) if self.mic_data else np.array([])
            sys_audio = np.concatenate(self.sys_data) if self.sys_data else np.array([])
            maxlen = max(len(mic_audio), len(sys_audio))
            if maxlen == 0:
                print("No se grabó audio.")
                return

            if len(mic_audio) == 0:
                mic_audio = np.zeros(maxlen)
            elif len(mic_audio) < maxlen:
                mic_audio = np.pad(mic_audio, (0, maxlen - len(mic_audio)))

            if len(sys_audio) == 0:
                sys_audio = np.zeros(maxlen)
            elif len(sys_audio) < maxlen:
                sys_audio = np.pad(sys_audio, (0, maxlen - len(sys_audio)))

            mix = mic_audio * self.mic_volume + sys_audio * self.sys_volume
            if np.max(np.abs(mix)) > 0:
                mix = mix / np.max(np.abs(mix)) * 0.95

            default_name = time.strftime("grabacion_%Y%m%d_%H%M%S.wav")
            filepath = filedialog.asksaveasfilename(
                defaultextension=".wav",
                filetypes=[("Archivo de audio WAV", "*.wav")],
                initialfile=default_name,
                title="Guardar grabación como..."
            )
            if filepath:
                sf.write(filepath, mix, self.fs)
                messagebox.showinfo("Grabación", f"Guardado en:\n{filepath}")
        except Exception as e:
            print(f"Error guardando: {e}")

    def _actualizar_cronometro(self):
        def task():
            while self.recording:
                try:
                    elapsed = int(time.time() - self._inicio_grab)
                    mins, secs = divmod(elapsed, 60)
                    horas, mins = divmod(mins, 60)
                    tiempo = f"{horas:02}:{mins:02}:{secs:02}" if horas > 0 else f"{mins:02}:{secs:02}"
                    self.after(0, lambda: self.crono_label.configure(text=tiempo))
                    time.sleep(1)
                except Exception:
                    break
        threading.Thread(target=task, daemon=True).start()

    # -------------------- Cierre --------------------
    def _on_close(self):
        # detener grabación y medidores
        self.recording = False
        for k in list(self.niveles_activos.keys()):
            self.niveles_activos[k] = False
        self.destroy()
