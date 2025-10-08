#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AsisVoz – TODO en UNA sola clase (ventana centrada, sin pantalla completa)

Cambios clave:
- Ventana principal con tamaño fijo inicial (980x680) y centrada en pantalla.
- Toplevels (licencia / equipo) también centrados.
- Eliminado el modo pantalla completa / área de trabajo (Windows).
- Enter envía el mensaje (sin salto); Shift+Enter sí inserta salto.
"""

import os
import json
import time
import tempfile
import threading
import platform
import subprocess
import ctypes
from ctypes import wintypes

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk
from tkinterdnd2 import DND_FILES, TkinterDnD
from screeninfo import get_monitors
import requests

# Dependencias internas del proyecto
from OpenRouterClient import OpenRouterClient
from DeepGramClient import DeepgramPDFTranscriber
import utils

# Opcional (conversión de mp4->mp3)
try:
    from moviepy import AudioFileClip
    _MOVIEPY_OK = True
except Exception:
    _MOVIEPY_OK = False


# ========================= Utilidades de centrado =========================
def center_window(win: tk.Misc, w: int, h: int):
    """Centra una ventana (Tk o Toplevel) con tamaño w x h."""
    try:
        mon = get_monitors()[0]
        sw, sh = mon.width, mon.height
    except Exception:
        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()

    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")
    win.update_idletasks()


class AsisVozAllInOne(TkinterDnD.Tk):
    """Aplicación completa en una sola clase (centrada, sin pantalla completa)."""

    LICENCIAS_VALIDAS = [
        "A7X4D9-KLM3Q2-Z8N6YP",
        "P3W9XK-8JDLQ1-R2M4VT",
        "QZ8C1B-MN4V7E-5TPR6X",
    ]
    ARCHIVO_ESTADO_LICENCIA = "estado_licencia.json"

    def __init__(self):
        super().__init__()
        # Tema inicial
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("AsisVoz – Una clase")
        # Tamaño inicial razonable y centrado
        self._base_w = 980
        self._base_h = 680
        center_window(self, self._base_w, self._base_h)
        # Permite redimensionar, pero sin forzar pantalla completa
        self.minsize(820, 560)

        # Variables de estado globales
        self.selected_files = []
        self.word_path = None
        self.nombre_word = None

        # Saldos Deepgram
        self.balance_actual = None
        self.balance_anterior = None

        # Clientes (se instancian al entrar a la app principal)
        self.router_client = None
        self.transcriptor = None

        # Widgets dinámicos de la app principal
        self.lbl_saldo = None
        self.chat_area = None
        self.chat_row = 0
        self.archivo_frame = None
        self.archivos_frame = None
        self.btn_transcribir = None
        self.btn_abrir_transcripcion = None
        self.entry_message = None
        self.tooltip_label = None
        self._mensaje_cargando_label = None

        # GIF loading
        self.gif_frames = []
        self._gif_job = None
        self.gif_label = None

        # Historial
        self.historial_archivo = "historial.txt"
        self.historial_transcripciones = []
        self.historial_menu = None

        # Construir la ventana de lanzamiento
        utils.descifrar_y_extraer_claves()
        utils.reproducir_sonido("inicio")
        self._build_launcher()
        # asegurar centrado por si el gestor de ventanas reacomoda
        self.after(100, lambda: center_window(self, self._base_w, self._base_h))

    # ------------------------------------------------------------------
    # --------------------- Construcción VENTANA 1 ----------------------
    # ------------------------------------------------------------------
    def _build_launcher(self):
        # Menú
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        menu_opciones = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Opciones", menu=menu_opciones)
        menu_opciones.add_command(label="Registrar Licencia", command=self._show_license_window)
        menu_opciones.add_command(label="Registrar Equipo", command=self._show_register_machine)
        menu_opciones.add_separator()
        menu_opciones.add_command(label="Salir", command=self.quit)

        # Contenido
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Icono
        try:
            ruta_imagen = os.path.join("media", "icono.png")
            image = Image.open(ruta_imagen).resize((110, 110))
            ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=(110, 110))
            label_img = ctk.CTkLabel(main_frame, image=ctk_img, text="")
            label_img.image = ctk_img
            label_img.pack(pady=(50, 15))
        except Exception as e:
            print(f"❌ Error al cargar imagen: {e}")

        btn_iniciar = ctk.CTkButton(
            main_frame,
            text="Iniciar Aplicación",
            font=ctk.CTkFont(size=18, weight="bold"),
            width=250,
            height=60,
            command=self._start_if_ready
        )
        btn_iniciar.pack(pady=18)

        info_label = ctk.CTkLabel(
            main_frame,
            text="Asegúrese de tener una licencia válida antes de iniciar la aplicación",
            font=ctk.CTkFont(size=10),
            text_color="black",
        )
        info_label.pack(pady=(10, 20))

        # Icono de ventana
        ico_path = utils.ruta_absoluta("media/logo.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

    def _start_if_ready(self):
        if not self._licencia_ya_registrada():
            messagebox.showwarning("Licencia Requerida", "⚠️ Debe ingresar una licencia válida.")
            self._show_register_machine()
            return
        if not self._validar_keys_presentes():
            messagebox.showerror("Claves API inválidas", "❌ Las claves API no están correctamente configuradas.")
            self._show_license_window()
            return
        # Pasar a la app principal
        self._build_main_app()

    # ------------------------------------------------------------------
    # -------------------- Ventanas secundarias (modales) ---------------
    # ------------------------------------------------------------------
    def _show_license_window(self):
        """Ventana para guardar/validar claves Deepgram + OpenRouter."""
        win = ctk.CTkToplevel(self)
        win.title("Registrar Licencia / Claves API")
        win.resizable(False, False)
        center_window(win, 500, 260)
        win.transient(self)

        # Icono
        ico_path = utils.ruta_absoluta("media/logo.ico")
        if os.path.exists(ico_path):
            try:
                win.iconbitmap(ico_path)
            except Exception:
                pass

        # Deepgram
        ctk.CTkLabel(win, text="Deepgram API Key:").pack(pady=(15, 5))
        frm_dg = ctk.CTkFrame(win, fg_color="transparent")
        frm_dg.pack(pady=5, padx=10, fill="x")
        ent_dg = ctk.CTkEntry(frm_dg, show="*", width=360)
        if utils.DEEPGRAM_API_KEY:
            ent_dg.insert(0, utils.DEEPGRAM_API_KEY)
        ent_dg.pack(side="left", padx=(0, 10), expand=True, fill="x")
        var_show_dg = tk.IntVar(value=0)
        chk_dg = ctk.CTkCheckBox(
            frm_dg, text="👁", variable=var_show_dg,
            command=lambda: ent_dg.configure(show="" if var_show_dg.get() else "*"),
            width=30
        )
        chk_dg.pack(side="left")

        # OpenRouter
        ctk.CTkLabel(win, text="OpenRouter API Key:").pack(pady=(10, 5))
        frm_or = ctk.CTkFrame(win, fg_color="transparent")
        frm_or.pack(pady=5, padx=10, fill="x")
        ent_or = ctk.CTkEntry(frm_or, show="*", width=360)
        if utils.OPENROUTER_API_KEY:
            ent_or.insert(0, utils.OPENROUTER_API_KEY)
        ent_or.pack(side="left", padx=(0, 10), expand=True, fill="x")
        var_show_or = tk.IntVar(value=0)
        chk_or = ctk.CTkCheckBox(
            frm_or, text="👁", variable=var_show_or,
            command=lambda: ent_or.configure(show="" if var_show_or.get() else "*"),
            width=30
        )
        chk_or.pack(side="left")

        def guardar():
            dg = ent_dg.get().strip()
            orkey = ent_or.get().strip()
            if not dg or not orkey:
                messagebox.showerror("Error", "Por favor ingresa ambas claves.")
                return
            if not self._validar_claves(dg, orkey):
                messagebox.showerror("Error", "Alguna de las claves no es válida.")
                return
            ok = utils.guardar_claves_cifradas(orkey, dg)
            if ok:
                utils.DEEPGRAM_API_KEY = dg
                utils.OPENROUTER_API_KEY = orkey
                messagebox.showinfo("Guardado", "Las claves han sido guardadas correctamente.")
                win.destroy()
            else:
                messagebox.showerror("Error", "No se pudo guardar el archivo cifrado.")

        ctk.CTkButton(win, text="Guardar Claves", command=guardar, width=200).pack(pady=25)

    def _show_register_machine(self):
        """Ventana modal para introducir la licencia (equipo)."""
        win = ctk.CTkToplevel(self)
        win.title("Registrar Equipo")
        win.resizable(False, False)
        center_window(win, 420, 200)
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(
            win, text="Ingrese su clave de licencia:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=20)
        entry = ctk.CTkEntry(
            win, font=ctk.CTkFont(size=12),
            width=300, height=35, placeholder_text="Clave de licencia"
        )
        entry.pack(pady=10)

        def registrar():
            clave = entry.get().strip()
            if clave in self.LICENCIAS_VALIDAS:
                self._guardar_licencia_valida()
                messagebox.showinfo("Licencia válida", "✅ Licencia válida. Equipo registrado.")
                try:
                    win.grab_release()
                except Exception:
                    pass
                win.destroy()
            else:
                messagebox.showerror("Licencia inválida", "❌ La clave de licencia no es válida.")

        def cerrar():
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()

        ctk.CTkButton(win, text="Registrar", width=150, height=35, command=registrar).pack(pady=20)
        win.protocol("WM_DELETE_WINDOW", cerrar)

    # ------------------------------------------------------------------
    # ------------------------- App principal ---------------------------
    # ------------------------------------------------------------------
    def _build_main_app(self):
        """Reemplaza el contenido de la ventana con la UI principal."""
        for w in self.winfo_children():
            if isinstance(w, (ctk.CTkFrame, tk.Menu, tk.Frame)):
                try:
                    w.destroy()
                except Exception:
                    pass

        # Mantén tamaño moderado y centrado (sin pantalla completa)
        center_window(self, self._base_w, self._base_h)

        # Clientes
        self.router_client = OpenRouterClient(utils.OPENROUTER_API_KEY)
        self.transcriptor = DeepgramPDFTranscriber(utils.DEEPGRAM_API_KEY)

        # Marco principal (dos columnas)
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # ---- Columna izquierda: Audio + Transcripción ----
        left_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        left_frame.pack(side="left", anchor="n", padx=(0, 18), fill="y")
        left_frame.configure(width=350)

        ctk.CTkLabel(left_frame, text="Audio", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(
            left_frame,
            text="Agrega tus archivos de audio aquí",
            font=ctk.CTkFont(size=12),
            wraplength=300, justify="left"
        ).pack(anchor="w", pady=(0, 12))

        upload_border = ctk.CTkFrame(left_frame, height=150, border_width=1, border_color="#aaaaaa")
        upload_border.pack(pady=(0, 8), fill="x")
        upload_border.pack_propagate(False)
        self._crear_area_upload(upload_border)  # DnD + botón buscar

        self.archivos_frame = ctk.CTkFrame(left_frame, fg_color="white", corner_radius=10)
        self.archivos_frame.pack(pady=(5, 14), fill="both", expand=True)

        self.btn_transcribir = ctk.CTkButton(left_frame, text="Transcribir", height=35, command=self._on_transcribir)
        self.btn_transcribir.pack_forget()

        self.btn_abrir_transcripcion = ctk.CTkButton(
            left_frame, text="Abrir transcripción generada", height=35,
            command=self._on_open_transcripcion
        )
        self.btn_abrir_transcripcion.pack(side="bottom", anchor="w", pady=(0, 5), padx=5)
        self.btn_abrir_transcripcion.pack_forget()

        # ---- Columna derecha: Chat ----
        right_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        right_frame.pack(side="left", fill="both", expand=True)

        chat_frame = ctk.CTkFrame(right_frame, border_width=1, border_color="#aaaaaa", corner_radius=15)
        chat_frame.pack(anchor="n", padx=10, pady=(16, 10), fill="both", expand=True)

        # Icono del chatbot
        try:
            image_path = os.path.join("media", "icono.png")
            chatbot_img = ctk.CTkImage(
                light_image=Image.open(image_path),
                dark_image=Image.open(image_path),
                size=(54, 54)
            )
            ctk.CTkLabel(chat_frame, image=chatbot_img, text="").pack(pady=(14, 8))
        except Exception:
            pass

        ctk.CTkLabel(chat_frame, text="Chatbot", font=ctk.CTkFont(size=16, weight="bold")).pack()
        ctk.CTkLabel(
            chat_frame, text="¡Hola! ¿Cómo puedo ayudarte hoy?",
            font=ctk.CTkFont(size=12), justify="center"
        ).pack(pady=(4, 0))

        # Saldo Deepgram
        self.lbl_saldo = ctk.CTkLabel(
            self, text=self.obtener_balance_deepgram(), font=ctk.CTkFont(size=13, weight="bold"),
            text_color="black", fg_color="#aaaaaa", corner_radius=10, padx=5, pady=10
        )
        # Ubicación discreta dentro del borde derecho superior
        self.lbl_saldo.place(relx=0.98, rely=0.02, anchor="ne")

        # Scrollable chat
        self.chat_area = ctk.CTkScrollableFrame(chat_frame, fg_color="white", corner_radius=10)
        self.chat_area.pack(padx=12, pady=(4, 10), fill="both", expand=True)
        self.chat_area.grid_columnconfigure(0, weight=1, minsize=300)
        self.chat_row = 0

        # Entrada + botones
        frame_contenedor = ctk.CTkFrame(chat_frame, fg_color="transparent")
        frame_contenedor.pack(padx=10, pady=(0, 10), fill="x")

        frame_entry = ctk.CTkFrame(frame_contenedor, fg_color="transparent")
        frame_entry.pack(fill="x")

        self.entry_message = ctk.CTkTextbox(frame_entry, height=30, text_color="black")
        self.entry_message.pack(side="left", fill="x", expand=True)

        # Enviar con Enter (sin salto). Shift+Enter conserva salto de línea.
        self.entry_message.bind("<Return>", self._return_envia_sin_salto)
        self.entry_message.bind("<Shift-Return>", lambda e: None)

        self.btn_adjuntar_word = ctk.CTkButton(
            frame_entry, text="📎", width=40, height=32,
            fg_color="transparent", hover_color="#e0e0e0", text_color="black",
            command=self._on_select_word
        )
        self.btn_adjuntar_word.pack(side="left", padx=(5, 10))
        self.btn_adjuntar_word.bind("<Enter>", lambda e: self._mostrar_tooltip("Adjuntar archivo Word", e))
        self.btn_adjuntar_word.bind("<Leave>", lambda e: self._ocultar_tooltip())

        ctk.CTkButton(frame_entry, text="Enviar", width=60, height=32, command=self._on_enviar_mensaje).pack(side="left")

        self.archivo_frame = ctk.CTkFrame(frame_contenedor, fg_color="#f5f5f5", corner_radius=10, height=30)
        self.archivo_frame.pack(fill="x", pady=(5, 0))
        self.archivo_frame.pack_forget()

        # Menú historial (ya en esta ventana)
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        self.historial_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Historial", menu=self.historial_menu)
        self.historial_transcripciones = self._cargar_historial()
        self._actualizar_menu_historial()

        # Sonido
        utils.reproducir_sonido("inicio")

    # ---------- Eventos de entrada ----------
    def _return_envia_sin_salto(self, event):
        self._on_enviar_mensaje()
        return "break"

    # ------------------------------------------------------------------
    # ------------------- Lógica de licencia / claves -------------------
    # ------------------------------------------------------------------
    def _guardar_licencia_valida(self):
        try:
            with open(self.ARCHIVO_ESTADO_LICENCIA, "w") as f:
                json.dump({"licencia_valida": True}, f)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el estado de licencia:\n{e}")

    def _licencia_ya_registrada(self):
        if os.path.exists(self.ARCHIVO_ESTADO_LICENCIA):
            try:
                with open(self.ARCHIVO_ESTADO_LICENCIA, "r") as f:
                    data = json.load(f)
                return data.get("licencia_valida", False)
            except Exception:
                return False
        return False

    def _validar_keys_presentes(self):
        return bool(utils.OPENROUTER_API_KEY and utils.DEEPGRAM_API_KEY)

    def _validar_claves(self, deepgram_key, openrouter_key):
        try:
            from utils import validar_api_key_deepgram, verificar_openrouter_key
            return validar_api_key_deepgram(deepgram_key) and verificar_openrouter_key(openrouter_key)
        except Exception:
            return len(deepgram_key) > 10 and len(openrouter_key) > 10

    # ------------------------------------------------------------------
    # ------------------------- BLOQUE: CHAT ----------------------------
    # ------------------------------------------------------------------
    def _on_enviar_mensaje(self):
        mensaje = self.entry_message.get("1.0", "end").strip()
        if not mensaje:
            messagebox.showwarning("Mensaje vacío", "Escribe un mensaje para enviar.")
            return

        mensaje_visual = mensaje
        if self.word_path:
            mensaje_visual += f"\n[Archivo: {os.path.basename(self.word_path)}]"

        self.agregar_mensaje(mensaje_visual, remitente="usuario")
        _, label_bot = self.agregar_mensaje("Cargando respuesta", remitente="bot")

        ruta_word_local = self.word_path
        self.entry_message.delete("1.0", "end")
        for widget in self.archivo_frame.winfo_children():
            widget.destroy()
        self.archivo_frame.pack_forget()
        self.word_path = None

        cargando_activo = True

        def animar():
            puntos = ["", ".", "..", "..."]
            idx = 0
            while cargando_activo:
                nuevo = f"Cargando respuesta{puntos[idx % len(puntos)]}"
                self.after(0, lambda t=nuevo: label_bot.configure(text=t))
                idx += 1
                time.sleep(0.5)

        threading.Thread(target=animar, daemon=True).start()

        def procesar():
            nonlocal cargando_activo
            try:
                if ruta_word_local:
                    respuesta, _ = self.router_client.preguntar_con_word(ruta_word_local, mensaje)
                else:
                    respuesta, _ = self.router_client.preguntar_texto(mensaje)
                respuesta = self._limpiar_respuesta_openrouter(respuesta)
                cargando_activo = False
                self.after(0, lambda: label_bot.configure(text=respuesta))
            except Exception as e:
                cargando_activo = False
                self.after(0, lambda: label_bot.configure(text="Error al obtener respuesta."))
                messagebox.showerror("Error", str(e))

        threading.Thread(target=procesar, daemon=True).start()

    def _limpiar_respuesta_openrouter(self, texto):
        if not texto:
            return ""
        texto_limpio = texto.replace("###", "")
        lineas = texto_limpio.split('\n')
        lineas_filtradas = []
        for linea in lineas:
            s = linea.strip()
            if s or (lineas_filtradas and lineas_filtradas[-1].strip()):
                lineas_filtradas.append(linea)
        return '\n'.join(lineas_filtradas).strip()

    def agregar_mensaje(self, texto, remitente="usuario"):
        bubble_fg = "#d9eaff" if remitente == "usuario" else "#f1f1f1"
        self.chat_area.update_idletasks()
        chat_width = self.chat_area.winfo_width()
        if chat_width <= 100:
            window_width = self.winfo_width()
            chat_width = max(300, window_width - 450)
        max_bubble_width = 500
        wraplength = min(max_bubble_width, max(200, chat_width - 150))

        container = ctk.CTkFrame(self.chat_area, fg_color="transparent")
        container.grid(row=self.chat_row, column=0, padx=15, pady=5, sticky="ew")
        if remitente == "usuario":
            container.grid_columnconfigure(0, weight=1)
            container.grid_columnconfigure(1, weight=0)
            bubble_column = 1
            bubble_sticky = "e"
        else:
            container.grid_columnconfigure(0, weight=0)
            container.grid_columnconfigure(1, weight=1)
            bubble_column = 0
            bubble_sticky = "w"

        bubble = ctk.CTkFrame(container, fg_color=bubble_fg, corner_radius=10)
        bubble.grid_propagate(True)
        bubble.configure(width=wraplength + 30)

        label = ctk.CTkLabel(
            bubble, text=texto, font=ctk.CTkFont(size=12),
            wraplength=wraplength, justify="left", anchor="w"
        )
        label.pack(padx=15, pady=10, fill="both", expand=True)

        btn_copiar = ctk.CTkButton(
            bubble, text="Copiar", width=50, height=24,
            fg_color="#e0e0e0", text_color="black",
            font=ctk.CTkFont(size=11), hover_color="#d0d0d0", corner_radius=8
        )

        def copiar():
            self.clipboard_clear()
            self.clipboard_append(label.cget("text"))
            btn_copiar.configure(text="¡Copiado!")
            self.after(3000, lambda: btn_copiar.configure(text="Copiar"))

        btn_copiar.configure(command=copiar)
        btn_copiar.pack(padx=10, pady=(0, 8), anchor="e")

        bubble.grid(row=0, column=bubble_column, sticky=bubble_sticky, padx=5)
        self.chat_row += 1
        self.after(50, lambda: self.chat_area._parent_canvas.yview_moveto(1.0))
        utils.reproducir_sonido("inicio")
        return bubble, label

    # ------------------------------------------------------------------
    # ----------------------- BLOQUE: UPLOAD ----------------------------
    # ------------------------------------------------------------------
    def _crear_area_upload(self, contenedor):
        ctk.CTkLabel(contenedor, text="🎵", font=ctk.CTkFont(size=32)).pack(pady=(10, 5))
        ctk.CTkLabel(
            contenedor, text="Arrastra tus archivos de audio\npara comenzar la carga",
            font=ctk.CTkFont(size=11), wraplength=280, justify="center"
        ).pack()
        ctk.CTkLabel(contenedor, text="O", font=ctk.CTkFont(size=11)).pack(pady=5)
        ctk.CTkButton(contenedor, text="Buscar archivos de audio", command=self._on_browse_files).pack()
        contenedor.drop_target_register(DND_FILES)
        contenedor.dnd_bind('<<Drop>>', self._on_drop_files)

    def _on_drop_files(self, event):
        archivos = self.tk.splitlist(event.data)
        valid = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.webm', '.opus')
        archivo = next((a for a in archivos if a.lower().endswith(valid)), None)
        if not archivo:
            messagebox.showerror("Error", "Por favor arrastra un archivo de audio válido.")
            return
        self.selected_files = [archivo]
        self.archivos_frame.pack_forget()
        self.archivos_frame.pack(pady=(5, 14), fill="x")
        self.btn_transcribir.pack(pady=(10, 5), fill="x")
        self._actualizar_lista_archivos()
        base = os.path.splitext(os.path.basename(self.selected_files[0]))[0]
        self.nombre_word = f"{base}.docx"
        self.agregar_mensaje("✔ Archivo cargado correctamente")

    def _on_browse_files(self):
        tipos = [("Audio files", "*.mp3 *.wav *.m4a *.flac *.ogg *.aac *.webm *.opus *.mp4")]
        try:
            ruta = filedialog.askopenfilename(title="Selecciona un archivo de audio", filetypes=tipos)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el diálogo de archivos:\n{e}")
            return
        if not ruta:
            return
        valid = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.webm', '.opus', '.mp4')
        if not ruta.lower().endswith(valid):
            messagebox.showerror("Error", "Por favor selecciona un archivo de audio válido.")
            return
        self.btn_transcribir.pack_forget()
        try:
            if ruta.lower().endswith('.mp4') and _MOVIEPY_OK:
                base = os.path.splitext(os.path.basename(ruta))[0]
                self.agregar_mensaje("📼 Archivo .mp4 detectado. Convirtiendo a .mp3...")
                tmp_dir = tempfile.gettempdir()
                ruta_convertida = os.path.join(tmp_dir, f"{base}.mp3")
                clip = AudioFileClip(ruta)
                clip.write_audiofile(ruta_convertida, logger=None)
                clip.close()
                self.selected_files = [ruta_convertida]
                self.agregar_mensaje("🔁 Conversión a .mp3 completada con éxito ✅")
            else:
                self.selected_files = [ruta]
        except Exception as e:
            messagebox.showerror("Error al procesar", f"Ocurrió un problema al cargar el archivo:\n{e}")
            return
        self._actualizar_lista_archivos()
        self.archivos_frame.pack_forget()
        self.archivos_frame.pack(pady=(5, 14), fill="x")
        try:
            base = os.path.splitext(os.path.basename(self.selected_files[0]))[0]
            self.nombre_word = f"{base}.docx"
        except Exception:
            self.nombre_word = "transcripcion.docx"
        self.agregar_mensaje("✔ Archivo cargado correctamente")
        self.btn_transcribir.pack(pady=(10, 5), fill="x")

    def _actualizar_lista_archivos(self):
        for w in self.archivos_frame.winfo_children():
            w.destroy()
        for ruta in self.selected_files:
            nombre = os.path.basename(ruta)
            fila = ctk.CTkFrame(self.archivos_frame, fg_color="transparent")
            fila.pack(anchor="w", fill="x", padx=5, pady=2)
            ctk.CTkLabel(fila, text=nombre, anchor="w", wraplength=250).pack(side="left", padx=(5, 0), fill="x", expand=True)
            ctk.CTkButton(
                fila, text="❌", width=30, fg_color="#d9534f", hover_color="#c9302c",
                command=lambda r=ruta: self._eliminar_archivo(r)
            ).pack(side="right", padx=5)

    def _eliminar_archivo(self, ruta):
        if messagebox.askyesno("Confirmar eliminación", "¿Estás seguro de eliminar el audio? Se eliminará la transcripción generada."):
            if ruta in self.selected_files:
                self.selected_files.remove(ruta)
                self.btn_abrir_transcripcion.pack_forget()
                self.btn_transcribir.pack_forget()
                self.archivos_frame.pack_forget()
                self.archivos_frame.pack(pady=(5, 14), fill="both", expand=True)
            self._actualizar_lista_archivos()

    # ------------------------------------------------------------------
    # ----------------------- BLOQUE: WORD/TOOLTIP ----------------------
    # ------------------------------------------------------------------
    def _on_select_word(self):
        ruta = filedialog.askopenfilename(title="Selecciona un archivo Word", filetypes=[("Archivos Word", "*.docx")])
        if ruta:
            ruta_abs = os.path.abspath(ruta)
            self.word_path = ruta_abs
            self._mostrar_archivo_seleccionado(ruta_abs)
            messagebox.showinfo("Archivo cargado", f"Word seleccionado:\n{os.path.basename(ruta_abs)}")
            self.selected_files.append(ruta_abs)
        else:
            self.word_path = None

    def _mostrar_archivo_seleccionado(self, ruta_archivo):
        ruta_norm = os.path.abspath(ruta_archivo)
        for w in self.archivo_frame.winfo_children():
            w.destroy()
        nombre_archivo = os.path.basename(ruta_norm)
        label = ctk.CTkLabel(self.archivo_frame, text=f"📄 {nombre_archivo}", anchor="w", text_color="#222")
        label.pack(side="left", padx=10, pady=5, fill="x", expand=True)
        boton = ctk.CTkButton(
            self.archivo_frame, text="❌", width=25, height=25,
            fg_color="transparent", hover_color="#eee", text_color="red",
            command=lambda r=ruta_norm: self._eliminar_archivito(r)
        )
        boton.pack(side="right", padx=10, pady=5)
        self.archivo_frame.pack(side="top", fill="x", pady=(0, 5))

    def _eliminar_archivito(self, ruta):
        if ruta in self.selected_files:
            self.selected_files.remove(ruta)
        if self.word_path == ruta:
            self.word_path = None
        self.archivo_frame.pack_forget()
        self.btn_transcribir.pack_forget()

    def _mostrar_tooltip(self, texto, evento=None):
        if hasattr(self, "tooltip_label") and self.tooltip_label:
            self.tooltip_label.destroy()
        x = self.btn_adjuntar_word.winfo_rootx()
        y = self.btn_adjuntar_word.winfo_rooty()
        self.tooltip_label = tk.Toplevel(self)
        self.tooltip_label.wm_overrideredirect(True)
        self.tooltip_label.configure(bg="#333")
        label = tk.Label(self.tooltip_label, text=texto, bg="#333", fg="white", font=("Arial", 10), padx=5, pady=2)
        label.pack()
        self.tooltip_label.wm_geometry(f"+{x}+{y - 30}")

    def _ocultar_tooltip(self):
        if hasattr(self, "tooltip_label") and self.tooltip_label:
            self.tooltip_label.destroy()
            self.tooltip_label = None

    # ------------------------------------------------------------------
    # --------------------- BLOQUE: TRANSCRIPCIÓN -----------------------
    # ------------------------------------------------------------------
    def _on_transcribir(self):
        if not self.selected_files:
            messagebox.showinfo("Sin archivos", "Primero selecciona archivos.")
            return
        self.btn_transcribir.configure(text="Transcribiendo...", state="disabled")
        self.btn_abrir_transcripcion.pack_forget()
        carpeta = filedialog.askdirectory(title="Selecciona una carpeta para guardar el Word")
        if not carpeta:
            messagebox.showinfo("Cancelado", "No se seleccionó ninguna carpeta.")
            self.btn_transcribir.configure(text="Transcribir", state="normal")
            return
        base = os.path.splitext(os.path.basename(self.selected_files[0]))[0]
        base = (base[:70] + '...') if len(base) > 50 else base
        self.nombre_word = os.path.join(carpeta, f"{base}.docx")

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
        costo = self.calcular_costo_transcripcion()
        self.agregar_mensaje(f"✔ Transcripción completada {self.nombre_word}", remitente="bot")
        utils.reproducir_sonido("inicio")
        self.btn_abrir_transcripcion.pack(pady=(5, 0))
        self.lbl_saldo.configure(text=self.obtener_balance_deepgram())
        if isinstance(costo, str) and costo.startswith("🧾"):
            self.agregar_mensaje(costo, remitente="bot")

    def _mostrar_gif_cargando(self):
        self.gif_frames = []
        try:
            imagen = Image.open("media/cargando.gif")
            while True:
                frame = imagen.copy().convert("RGBA").resize((90, 90), Image.LANCZOS)
                self.gif_frames.append(ImageTk.PhotoImage(frame))
                imagen.seek(len(self.gif_frames))
        except EOFError:
            pass
        if not self.gif_label:
            self.gif_label = ctk.CTkLabel(self, text="")
        self.gif_label.place(relx=0.03, rely=0.92, x=15, anchor="sw")
        self._gif_frame_index = 0
        self._reproducir_gif()

    def _reproducir_gif(self):
        if self.gif_frames and self.gif_label:
            frame = self.gif_frames[self._gif_frame_index]
            self.gif_label.configure(image=frame)
            self.gif_label.image = frame
            self._gif_frame_index = (self._gif_frame_index + 1) % len(self.gif_frames)
            self._gif_job = self.after(100, self._reproducir_gif)

    def _ocultar_gif_cargando(self):
        if self.gif_label:
            self.gif_label.place_forget()
        if self._gif_job:
            self.after_cancel(self._gif_job)

    def _on_open_transcripcion(self):
        if not self.nombre_word:
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

    # ------------------------------------------------------------------
    # ------------------- Balance y coste Deepgram ----------------------
    # ------------------------------------------------------------------
    def obtener_balance_deepgram(self) -> str:
        try:
            project_id = utils.obtener_project_id_deepgram(utils.DEEPGRAM_API_KEY)
            if not project_id:
                return "❗ No se pudo obtener project_id."
            url = f"https://api.deepgram.com/v1/projects/{project_id}/balances"
            headers = {"Authorization": f"Token {utils.DEEPGRAM_API_KEY}"}
            tasa = 4000
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            balances = data.get("balances", [])
            if balances:
                amount = balances[0].get("amount", 0.0)
                units = balances[0].get("units", "usd")
                if self.balance_actual is not None:
                    self.balance_anterior = self.balance_actual
                else:
                    self.balance_anterior = amount
                self.balance_actual = amount
                amount_cop = round(amount * tasa)
                return f"${amount:.2f} {units.upper()} / ${amount_cop:,} COP"
            else:
                return "❗ Balance no disponible."
        except requests.RequestException as e:
            print(f"❌ Error balance Deepgram: {e}")
            return "❌ Error al obtener balance."

    def calcular_costo_transcripcion(self) -> str:
        tasa = 4000
        if self.balance_actual is None:
            self.obtener_balance_deepgram()
        if self.balance_anterior is None:
            self.balance_anterior = self.balance_actual
            return "No hay datos anteriores para calcular el costo (primer registro tomado)."
        previo = self.balance_anterior
        self.obtener_balance_deepgram()
        nuevo = self.balance_actual
        try:
            costo_usd = float(previo) - float(nuevo)
        except Exception:
            return "No se pudo calcular el costo."
        costo_cop = round(costo_usd * tasa)
        if costo_usd < 0:
            return "Error: costo negativo calculado."
        messagebox.showinfo("Costo de la transcripción", f"El costo de esta transcripción fue de: {costo_usd:.2f} USD / ${costo_cop:,} COP")
        return f"🧾 Costo de la transcripción: {costo_usd:.2f} USD / ${costo_cop:,} COP"

    # ------------------------------------------------------------------
    # -------------------------- Historial ------------------------------
    # ------------------------------------------------------------------
    def _cargar_historial(self):
        if not os.path.exists(self.historial_archivo):
            return []
        with open(self.historial_archivo, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        return lines[-20:]

    def _guardar_en_historial(self, ruta_word):
        self.historial_transcripciones.append(ruta_word)
        self.historial_transcripciones = self.historial_transcripciones[-20:]
        with open(self.historial_archivo, "a", encoding="utf-8") as f:
            f.write(ruta_word + "\n")
        self._actualizar_menu_historial()

    def _actualizar_menu_historial(self):
        if not self.historial_menu:
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


if __name__ == "__main__":
    app = AsisVozAllInOne()
    app.mainloop()
