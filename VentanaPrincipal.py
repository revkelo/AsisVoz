import os
import threading
import customtkinter as ctk
import requests
from DeepGramClient import DeepgramPDFTranscriber

from customtkinter import CTkImage

from OpenRouterClient import OpenRouterClient
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import tkinter as tk
import platform
import subprocess
from PIL import Image, ImageTk

import utils
import ctypes
from ctypes import windll, Structure, c_long, byref

balance_actual= None
balance_anterior = None


class RECT(Structure):
    _fields_ = [("left", c_long),
                ("top", c_long),
                ("right", c_long),
                ("bottom", c_long)]

def get_work_area():
    rect = RECT()
    SPI_GETWORKAREA = 0x0030
    windll.user32.SystemParametersInfoA(SPI_GETWORKAREA, 0, byref(rect), 0)
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    return width, height

class AsisVozApp(TkinterDnD.Tk):
    def __init__(self,openrouter_key, deepgram_key):
        
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.word_path = None
        
        # Obtener resoluciones física y lógica
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        res_fisica = (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))

        res_logica = (self.winfo_screenwidth(), self.winfo_screenheight())

        # Calcular escalado
        escala_x = int((res_fisica[0] / res_logica[0]) * 100)
        escala_y = int((res_fisica[1] / res_logica[1]) * 100)

        # Aplicar configuración de ventana según resolución y escala
        if res_fisica == (1366, 768) and escala_x <= 125 and escala_y <= 125:
            self.resizable(False, False)     # <- PRIMERO bloquear el tamaño
            self.update_idletasks()          # <- Forzar update antes de maximizar
                    # Obtener tamaño usable de pantalla
            usable_width, usable_height = get_work_area()

            # Establecer tamaño ventana igual al área usable
            self.geometry(f"{usable_width}x{usable_height}+0+0")           # <- Luego maximizar tipo ventana

        else:
            self.geometry("1000x850")
            self.minsize(800, 600)
            self.resizable(True, True)

        
        
        self.minsize(800, 600)  # Tamaño mínimo de ventana
        ico_path = utils.ruta_absoluta("media/logo.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass
        self.centrar_ventana()

        self.selected_files = []

        self.auxiliar = ""
        

        self.deepgram_api_key = deepgram_key
        self.openrouter_api_key = openrouter_key
    
        self.router_client = OpenRouterClient(self.openrouter_api_key)
        self.transcriptor = DeepgramPDFTranscriber(self.deepgram_api_key)
        
        # Marco principal
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # ─── LEFT (Audio + Transcripción) ───────────────────────────────────
        left_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        left_frame.pack(side="left", anchor="n", padx=(0, 20), fill="y")
        left_frame.configure(width=350)  # Ancho base pero flexible

        # Título "Audio"
        ctk.CTkLabel(
            left_frame,
            text="Audio",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w")

        # Subtítulo
        ctk.CTkLabel(
            left_frame,
            text="Agrega tus archivos de audio aquí",
            font=ctk.CTkFont(size=12),
            wraplength=300,
            justify="left"
        ).pack(anchor="w", pady=(0, 15))

        # Área punteada / contenedor para arrastrar o buscar
        upload_border = ctk.CTkFrame(
            left_frame,
            height=160,
            border_width=1,
            border_color="#aaaaaa"
        )
        upload_border.pack(pady=(0, 10), fill="x")  # fill="x" para que se adapte
        upload_border.pack_propagate(False)
        self._crear_area_upload(upload_border)

        # Lista de archivos seleccionados
        self.archivos_frame = ctk.CTkFrame(left_frame, fg_color="white", corner_radius=10)
        self.archivos_frame.pack(pady=(5, 20), fill="x")

        # Botón "Transcribir"
        self.btn_transcribir = ctk.CTkButton(
            left_frame,
            text="Transcribir",
            height=35,
            command=self._on_transcribir
        )
        self.btn_transcribir.pack(pady=(10, 5), fill="x")

        # Botón "Abrir transcripción" (oculto inicialmente)
        self.btn_abrir_transcripcion = ctk.CTkButton(
            left_frame,
            text="Abrir transcripción generada",
            height=35,
            command=self._on_open_transcripcion
        )
        self.btn_abrir_transcripcion.pack(pady=(5, 0), fill="x")
        self.btn_abrir_transcripcion.pack_forget()

        # ─── RIGHT (Chatbot) ────────────────────────────────────────────────
        right_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        right_frame.pack(side="left", fill="both", expand=True)

        # Frame del chat que se expande
        chat_frame = ctk.CTkFrame(
            right_frame,
            border_width=1,
            border_color="#aaaaaa",
            corner_radius=15
        )
        chat_frame.pack(anchor="n", padx=10, pady=(40, 10), fill="both", expand=True)

        image_path = os.path.join("media", "icono.png")  # Ruta relativa a la imagen
        chatbot_img = ctk.CTkImage(
            light_image=Image.open(image_path),
            dark_image=Image.open(image_path),
            size=(60, 60)  # Ajusta el tamaño de la imagen
        )

        # Mostrar la imagen
        ctk.CTkLabel(
            chat_frame,
            image=chatbot_img,
            text=""
        ).pack(pady=(20, 10))

        # Título del chatbot
        ctk.CTkLabel(
            chat_frame,
            text="Chatbot",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack()

        # Mensaje de bienvenida
        ctk.CTkLabel(
            chat_frame,
            text="¡Hola! ¿Cómo puedo ayudarte hoy?",
            font=ctk.CTkFont(size=12),
            justify="center"
        ).pack(pady=(5, 0))

        
        
        # ─── SALDO EN ESQUINA SUPERIOR DERECHA ──────────────────────────────
        self.lbl_saldo = ctk.CTkLabel(
            self,
            text= self.obtener_balance_deepgram(),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="black",
            fg_color="#aaaaaa",
            corner_radius=10,
            padx=5,
            pady=15
        )
        self.lbl_saldo.place(relx=0.96, rely=0.01, anchor="ne")

        # Área scrollable para los mensajes (se expande automáticamente)
        self.chat_area = ctk.CTkScrollableFrame(
            chat_frame,
            fg_color="white",
            corner_radius=10
        )
        self.chat_area.pack(padx=15, pady=(0, 10), fill="both", expand=True)
        self.chat_area.grid_columnconfigure(0, weight=1, minsize=300)  # Asegurar ancho mínimo
        self.chat_row = 0

        # === Contenedor para entrada y archivo ===
        frame_contenedor = ctk.CTkFrame(chat_frame, fg_color="transparent")
        frame_contenedor.pack(padx=10, pady=(0, 10), fill="x")

        # === Fila 1: Entrada de texto + botones ===
        frame_entry = ctk.CTkFrame(frame_contenedor, fg_color="transparent")
        frame_entry.pack(fill="x")

        # Campo de texto
        self.entry_message = ctk.CTkEntry(
            frame_entry,
            text_color="black",
            placeholder_text="Escribe un mensaje..."
        )
        self.entry_message.pack(side="left", fill="x", expand=True)
        self.entry_message.bind("<Return>", lambda event: self._on_enviar_mensaje())

        # Botón para adjuntar archivo Word
        self.btn_adjuntar_word = ctk.CTkButton(
            frame_entry,
            text="📎",
            width=40,
            height=32,
            fg_color="transparent",
            hover_color="#e0e0e0",
            text_color="black",
            command=self._on_select_word
        )
        self.btn_adjuntar_word.pack(side="left", padx=(5, 10))

        # Tooltip
        self.btn_adjuntar_word.bind("<Enter>", lambda e: self._mostrar_tooltip("Adjuntar archivo Word", e))
        self.btn_adjuntar_word.bind("<Leave>", lambda e: self._ocultar_tooltip())

        # Botón Enviar
        ctk.CTkButton(
            frame_entry,
            text="Enviar",
            width=60,
            height=32,
            command=self._on_enviar_mensaje
        ).pack(side="left")

        # === Fila 2: Visualización del archivo adjunto ===
        self.archivo_frame = ctk.CTkFrame(
            frame_contenedor,       # OJO: diferente frame contenedor (vertical)
            fg_color="#f5f5f5",
            corner_radius=10,
            height=30
        )
        self.archivo_frame.pack(fill="x", pady=(5, 0))
        self.archivo_frame.pack_forget()  # Se oculta hasta que se adjunte algo

        
        self.historial_archivo = "historial.txt"
        self.historial_transcripciones = self._cargar_historial()

        self.gif_path = "media/cargando.gif"
        self.gif_frames = []
        self.current_frame = 0

        if os.path.exists(self.gif_path):
            self._cargar_frames_gif()
            # ─── Menú superior ───────────────────────────────────────────────
            
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        self.historial_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Historial", menu=self.historial_menu)
        self._actualizar_menu_historial()  # <- Llamado después de definir historial_menu
        utils.reproducir_sonido("inicio")
        


    def _cargar_frames_gif(self):
        imagen = Image.open(self.gif_path)
        try:
            while True:
                frame = imagen.copy().convert("RGBA").resize((200, 200), Image.LANCZOS)
                frame_tk = ImageTk.PhotoImage(frame)
                self.gif_frames.append(frame_tk)
                imagen.seek(len(self.gif_frames))  # Siguiente frame
        except EOFError:
            pass  # Fin de los frames

        # Crear el label en la esquina inferior izquierda
        self.label = ctk.CTkLabel(self, text="")
        self.label.place(relx=0.0, rely=1.0, anchor="sw")  # Inferior izquierda

    def _mostrar_gif(self):
        if self.gif_frames:
            frame = self.gif_frames[self.current_frame]
            self.label.configure(image=frame)
            self.label.image = frame  # 🔒 Mantener referencia
            self.current_frame = (self.current_frame + 1) % len(self.gif_frames)
            self.after(100, self._mostrar_gif)  # Cambia frame cada 100 ms

    def _mostrar_gif_cargando(self):
        self.gif_frames = []
        imagen = Image.open("media/cargando.gif")
        try:
            while True:
                frame = imagen.copy().convert("RGBA").resize((180, 180), Image.LANCZOS)
                self.gif_frames.append(ImageTk.PhotoImage(frame))
                imagen.seek(len(self.gif_frames))
        except EOFError:
            pass

        if not hasattr(self, 'gif_label'):
            self.gif_label = ctk.CTkLabel(self, text="")
        
        self.gif_label.place(relx=0.0, rely=1.0, x=50, y=-120, anchor="sw")

        self._gif_frame_index = 0
        self._reproducir_gif()


        if not hasattr(self, 'gif_label'):
            self.gif_label = ctk.CTkLabel(self, text="")
            self.gif_label.place(relx=0.0, rely=1.0, x=50, y=-120, anchor="sw")

        self._gif_frame_index = 0
        self._reproducir_gif()

    def _reproducir_gif(self):
        if hasattr(self, 'gif_frames') and hasattr(self, 'gif_label'):
            frame = self.gif_frames[self._gif_frame_index]
            self.gif_label.configure(image=frame)
            self.gif_label.image = frame  # mantener referencia
            self._gif_frame_index = (self._gif_frame_index + 1) % len(self.gif_frames)
            self._gif_job = self.after(100, self._reproducir_gif)

    def _ocultar_gif_cargando(self):
        if hasattr(self, 'gif_label'):
            self.gif_label.place_forget()  # Oculta el GIF
        if hasattr(self, '_gif_job'):
            self.after_cancel(self._gif_job)


    def _mostrar_tooltip(self, texto, evento=None):
        if hasattr(self, "tooltip_label") and self.tooltip_label:
            self.tooltip_label.destroy()

        # Obtener posición del botón
        x = self.btn_adjuntar_word.winfo_rootx()
        y = self.btn_adjuntar_word.winfo_rooty()

        # Crear tooltip como un Toplevel sin borde
        self.tooltip_label = tk.Toplevel(self)
        self.tooltip_label.wm_overrideredirect(True)
        self.tooltip_label.configure(bg="#333")

        # Crear etiqueta dentro del tooltip
        label = tk.Label(
            self.tooltip_label,
            text=texto,
            bg="#333",
            fg="white",
            font=("Arial", 10),
            padx=5,
            pady=2
        )
        label.pack()

        # Posicionar sobre el botón (ajusta -20 si quieres más separación)
        self.tooltip_label.wm_geometry(f"+{x}+{y - 30}")

    def _ocultar_tooltip(self):
        if hasattr(self, "tooltip_label") and self.tooltip_label:
            self.tooltip_label.destroy()
            self.tooltip_label = None

    def _on_enviar_mensaje(self):
        mensaje = self.entry_message.get().strip()
        if not mensaje:
            messagebox.showwarning("Mensaje vacío", "Escribe un mensaje para enviar.")
            return

        # Si hay archivo adjunto, añadimos su nombre al mensaje visual
        mensaje_visual = mensaje
        if hasattr(self, "word_path") and self.word_path:
            nombre_archivo = os.path.basename(self.word_path)
            mensaje_visual += f"\n[Archivo: {nombre_archivo}]"

        # Mostrar mensaje del usuario
        self.agregar_mensaje(mensaje_visual, remitente="usuario")

        # Mostrar burbuja "cargando..."
        _, label_bot = self.agregar_mensaje("Cargando respuesta...", remitente="bot")

        # Guarda copia del path del archivo ANTES de borrarlo
        ruta_word_local = self.word_path if hasattr(self, "word_path") else None

        # Limpia UI
        self.entry_message.delete(0, "end")
        for widget in self.archivo_frame.winfo_children():
            widget.destroy()
        self.archivo_frame.pack_forget()
        self.word_path = None

        # Ejecuta hilo de procesamiento
        def procesar_respuesta():
            try:
                if ruta_word_local:
                    respuesta, duracion = self.router_client.preguntar_con_word(ruta_word_local, mensaje)
                else:
                    respuesta, duracion = self.router_client.preguntar_texto(mensaje)

                label_bot.configure(text=respuesta)

            except Exception as e:
                label_bot.configure(text="Error al obtener respuesta.")
                messagebox.showerror("Error", str(e))

        threading.Thread(target=procesar_respuesta, daemon=True).start()



    def _mostrar_archivo_seleccionado(self, ruta_archivo):
        ruta_normalizada = os.path.abspath(ruta_archivo)

        print(f"🔽 Mostrando archivo: {repr(ruta_normalizada)}")

        if ruta_normalizada not in self.selected_files:
            self.selected_files.append(ruta_normalizada)
            print(f"✅ Añadido a la lista: {repr(ruta_normalizada)}")
        else:
            print(f"🟡 Ya estaba en la lista.")

        # Limpia el contenido del frame antes de agregar nuevo
        for widget in self.archivo_frame.winfo_children():
            widget.destroy()

        # Nombre del archivo para mostrar
        nombre_archivo = os.path.basename(ruta_normalizada)

        # Etiqueta con el nombre del archivo
        label = ctk.CTkLabel(self.archivo_frame, text=f"📄 {nombre_archivo}", anchor="w", text_color="#222")
        label.pack(side="left", padx=10, pady=5, fill="x", expand=True)

        # Botón para eliminar el archivo
        boton = ctk.CTkButton(
            self.archivo_frame,
            text="❌",
            width=25,
            height=25,
            fg_color="transparent",
            hover_color="#eee",
            text_color="red",
            command=lambda ruta=ruta_normalizada: self._eliminar_archivito(ruta)
        )
        boton.pack(side="right", padx=10, pady=5)

        # Muestra el frame (por si estaba oculto)
        self.archivo_frame.pack(side="top", fill="x", pady=(0, 5))


    def _eliminar_archivito(self, ruta):
        if ruta in self.selected_files:
            self.selected_files.remove(ruta)
            print(f"🗑️ Archivo eliminado: {ruta}")
        else:
            print(f"⚠️ El archivo '{ruta}' no está en la lista.")

        if hasattr(self, "word_path") and self.word_path == ruta:
            self.word_path = None

        self.archivo_frame.pack_forget()





    def _limpiar_respuesta_openrouter(self, texto):
        """
        Limpia la respuesta de OpenRouter eliminando los caracteres "###"
        """
        if not texto:
            return ""
        
        # Eliminar todas las ocurrencias de "###"
        texto_limpio = texto.replace("###", "")
        
        # Eliminar líneas vacías adicionales que puedan quedar
        lineas = texto_limpio.split('\n')
        lineas_filtradas = []
        
        for linea in lineas:
            linea_stripped = linea.strip()
            # Solo agregar la línea si no está vacía o si es necesaria para el formato
            if linea_stripped or (lineas_filtradas and lineas_filtradas[-1].strip()):
                lineas_filtradas.append(linea)
        
        # Unir las líneas y eliminar espacios en blanco excesivos al inicio y final
        return '\n'.join(lineas_filtradas).strip()

    def _on_window_resize(self, event):
        """Actualiza el wraplength de los mensajes cuando se redimensiona la ventana"""
        if event.widget == self:
            # Usar un delay más largo para asegurar que el layout se haya actualizado
            self.after(100, self._update_message_wraplength)

    def _update_message_wraplength(self):
        """Actualiza el wraplength de todos los mensajes existentes"""
        try:
            # Forzar actualización del layout
            self.chat_area.update_idletasks()
            
            # Obtener el ancho real del área de chat
            chat_width = self.chat_area.winfo_width()
            
            # Si el ancho es muy pequeño, usar el ancho de la ventana como referencia
            if chat_width < 200:
                window_width = self.winfo_width()
                # Estimar el ancho del chat basado en el ancho de la ventana
                # Considerando que el panel izquierdo ocupa aproximadamente 370px
                chat_width = max(300, window_width - 450)
            
            # Calcular wraplength con margen más conservador
            new_wraplength = max(200, chat_width - 150)
            
            # Actualizar todos los labels existentes
            for widget in self.chat_area.winfo_children():
                if isinstance(widget, ctk.CTkFrame):
                    # Buscar el frame de la burbuja dentro del contenedor
                    for container_child in widget.winfo_children():
                        if isinstance(container_child, ctk.CTkFrame):
                            # Buscar el label dentro de la burbuja
                            for bubble_child in container_child.winfo_children():
                                if isinstance(bubble_child, ctk.CTkLabel):
                                    bubble_child.configure(wraplength=new_wraplength)
        except Exception as e:
            print(f"Error actualizando wraplength: {e}")
 

    def obtener_balance_deepgram(self) -> str:
        """
        Obtiene el balance de Deepgram en USD y COP y actualiza
        balance_actual y balance_anterior para cálculo de costos.
        """
        # Obtener project_id
        self.aux = utils.obtener_project_id_deepgram(self.deepgram_api_key)
        url = f"https://api.deepgram.com/v1/projects/{self.aux}/balances"
        headers = {"Authorization": f"Token {self.deepgram_api_key}"}

        tasa_dolar_a_cop = 4000  # Ajusta según la tasa actual

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            balances = data.get("balances", [])
            if balances:
                amount = balances[0].get("amount")  # USD
                units = balances[0].get("units")

                # Si ya había un balance, moverlo a balance_anterior
                if hasattr(self, "balance_actual") and self.balance_actual is not None:
                    self.balance_anterior = self.balance_actual
                else:
                    self.balance_anterior = amount  # Inicializa en primera llamada

                # Actualizar balance actual
                self.balance_actual = amount

                amount_cop = round(amount * tasa_dolar_a_cop)
                return f"💰 {amount:.2f} {units.upper()} / ${amount_cop:,} COP"
            else:
                return "❗ No se encontró ningún balance disponible."

        except requests.RequestException as e:
            print(f"❌ Error al obtener balance de Deepgram: {e}")
            return "❌ Error al obtener balance."


    def calcular_costo_transcripcion(self) -> str:
        """
        Calcula el costo de la transcripción comparando el balance anterior y el actual.
        Si no hay datos previos, intenta obtenerlos automáticamente.
        """
        tasa_dolar_a_cop = 4000

        # Si no hay balance actual, obtenerlo
        if self.balance_actual is None:
            self.obtener_balance_deepgram()

        # Si no había balance anterior, usar el balance actual como base inicial
        if self.balance_anterior is None:
            self.balance_anterior = self.balance_actual
            return "No hay datos anteriores para calcular el costo (primer registro tomado)."

        # Obtener balance nuevo y calcular costo
        balance_previo = self.balance_anterior
        self.obtener_balance_deepgram()
        balance_nuevo = self.balance_actual

        costo_usd = balance_previo - balance_nuevo
        costo_cop = round(costo_usd * tasa_dolar_a_cop)

        if costo_usd < 0:
            return "Error: el costo calculado es negativo. Verifica el flujo de llamadas."

        return f"🧾 Costo de la transcripción: {costo_usd:.2f} USD / ${costo_cop:,} COP"


    def _on_select_word(self):
        ruta = filedialog.askopenfilename(
            title="Selecciona un archivo Word",
            filetypes=[("Archivos Word", "*.docx")]
        )

        if ruta:
            ruta_abs = os.path.abspath(ruta)
            self.word_path = ruta_abs

            self._mostrar_archivo_seleccionado(ruta_abs)
            messagebox.showinfo("Archivo cargado", f"Word seleccionado:\n{os.path.basename(ruta_abs)}")
            self.selected_files.append(ruta_abs)
        else:
            self.word_path = None


    def _on_switch_toggle(self):
        if self.use_word_switch.get() == 0:
            self.word_path = None  # limpiar si desactiva


    def _cargar_historial(self):
        """
        Carga el historial desde historial.txt y devuelve una lista de rutas.
        """
        if not os.path.exists(self.historial_archivo):
            return []
        with open(self.historial_archivo, "r", encoding="utf-8") as f:
            lineas = [line.strip() for line in f.readlines() if line.strip()]
        return lineas[-20:]  # Solo las últimas 20

    def _guardar_en_historial(self, ruta_word):
        """
        Guarda una nueva transcripción y actualiza el menú.
        """
        # Añadir al historial en memoria
        self.historial_transcripciones.append(ruta_word)
        self.historial_transcripciones = self.historial_transcripciones[-20:]

        # Guardar todo en el archivo (manteniendo persistencia completa)
        with open(self.historial_archivo, "a", encoding="utf-8") as f:
            f.write(ruta_word + "\n")

        # Actualizar menú
        self._actualizar_menu_historial()

    def _actualizar_menu_historial(self):
        """
        Refresca el menú "Historial" con las últimas transcripciones.
        """
        if not hasattr(self, 'historial_menu'):
            print("⚠️ historial_menu no está definido aún.")
            return

        self.historial_menu.delete(0, tk.END)
        if not self.historial_transcripciones:
            self.historial_menu.add_command(label="(Sin historial)", state="disabled")
        else:
            for ruta in reversed(self.historial_transcripciones):  # Lo más reciente arriba
                nombre = os.path.basename(ruta)
                self.historial_menu.add_command(
                    label=nombre,
                    command=lambda r=ruta: self._abrir_transcripcion_desde_historial(r)
                )


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


    def _on_send_based_on_switch(self):
        if self.use_word_switch.get() == 1:
            ruta = filedialog.askopenfilename(
                title="Selecciona un archivo Word",
                filetypes=[("Archivos Word", "*.docx")]
            )
            if not ruta:
                messagebox.showwarning("Word no seleccionado", "No se seleccionó ningún archivo.")
                return

            self.word_path = ruta
            self._on_send_with_word()
        else:
            self._on_send_message()

  
    def _crear_area_upload(self, contenedor):
        ctk.CTkLabel(
            contenedor,
            text="🎵",
            font=ctk.CTkFont(size=32)
        ).pack(pady=(10, 5))
        ctk.CTkLabel(
            contenedor,
            text="Arrastra tus archivos de audio\npara comenzar la carga",
            font=ctk.CTkFont(size=11),
            wraplength=280,
            justify="center"
        ).pack()
        ctk.CTkLabel(
            contenedor,
            text="O",
            font=ctk.CTkFont(size=11)
        ).pack(pady=5)
        ctk.CTkButton(
            contenedor,
            text="Buscar archivos de audio",
            command=self._on_browse_files
        ).pack()

        # Habilitar drop de archivos
        contenedor.drop_target_register(DND_FILES)
        contenedor.dnd_bind('<<Drop>>', self._on_drop_files)

    def _on_drop_files(self, event):
        archivos = self.tk.splitlist(event.data)
        extensiones_validas = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.webm', '.opus')

        archivo_valido = next((archivo for archivo in archivos if archivo.lower().endswith(extensiones_validas)), None)

        if not archivo_valido:
            messagebox.showerror("Error", "Por favor arrastra un archivo de audio válido.")
            return

        self.selected_files = [archivo_valido]  # Solo uno
        self._actualizar_lista_archivos()
        nombre_base = os.path.splitext(os.path.basename(self.selected_files[0]))[0]

        self.nombre_word = f"{nombre_base}.docx"
        self._agregar_mensaje("✔ Archivo cargado correctamente")



    def _on_browse_files(self):
        tipos_permitidos = [("Audio files", "*.mp3 *.wav *.m4a *.flac *.ogg *.aac *.webm *.opus")]
        ruta = filedialog.askopenfilename(
            title="Selecciona un archivo de audio",
            filetypes=tipos_permitidos
        )

        if not ruta:
            return

        extensiones_validas = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.webm', '.opus')
        if not ruta.lower().endswith(extensiones_validas):
            messagebox.showerror("Error", "Por favor selecciona un archivo de audio válido.")
            return

        self.selected_files = [ruta]  # Sobrescribe con un solo archivo
        self._actualizar_lista_archivos()

        nombre_base = os.path.splitext(os.path.basename(self.selected_files[0]))[0]
        self.nombre_word = f"{nombre_base}.docx"

        print("Archivo seleccionado:", self.selected_files[0])
        self.agregar_mensaje("✔ Archivo cargado correctamente")

    def _actualizar_lista_archivos(self):
        for widget in self.archivos_frame.winfo_children():
            widget.destroy()

        for ruta in self.selected_files:
            nombre = os.path.basename(ruta)
            fila = ctk.CTkFrame(self.archivos_frame, fg_color="transparent")
            fila.pack(anchor="w", fill="x", padx=5, pady=2)

            ctk.CTkLabel(
                fila,
                text=nombre,
                anchor="w",
                wraplength=250
            ).pack(side="left", padx=(5, 0), fill="x", expand=True)
            ctk.CTkButton(
                fila,
                text="❌",
                width=30,
                fg_color="#d9534f",
                hover_color="#c9302c",
                command=lambda r=ruta: self._eliminar_archivo(r)
            ).pack(side="right", padx=5)

    def _eliminar_archivo(self, ruta):
        respuesta = messagebox.askyesno(
            "Confirmar eliminación",
            "¿Estás seguro de eliminar el audio? Se eliminará la transcripción generada."
        )

        if respuesta:  # Solo procede si el usuario hace clic en "Sí"
            if ruta in self.selected_files:
                self.selected_files.remove(ruta)

            self._actualizar_lista_archivos()

            # Oculta el botón si ya no hay archivos
            if not self.selected_files:
                if hasattr(self, "btn_abrir_transcripcion") and self.btn_abrir_transcripcion:
                    self.btn_abrir_transcripcion.pack_forget()



    def centrar_ventana(self):
        self.update_idletasks()  # Asegura que geometry() tenga valores actualizados
        ancho_ventana = self.winfo_width()
        alto_ventana = self.winfo_height()
        ancho_pantalla = self.winfo_screenwidth()
        alto_pantalla = self.winfo_screenheight()
        x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        y = (alto_pantalla // 2) - (alto_ventana // 2)
        self.geometry(f"+{x}+{y}")

    def _on_transcribir(self):
        if not self.selected_files:
            messagebox.showinfo("Sin archivos", "Primero selecciona archivos.")
            return

        # Solicitar al usuario una carpeta para guardar el PDF
        carpeta_destino = filedialog.askdirectory(
            title="Selecciona una carpeta para guardar el Word"
        )

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
   
        # Guardar en historial
        self._guardar_en_historial(self.nombre_word)

        # Calcular el costo
        costo = self.calcular_costo_transcripcion()

        # Mostrar banner
 

        # Mensaje en el chat

        self.agregar_mensaje(
        f"✔ Transcripción completada {self.nombre_word} ",

        remitente="bot"
        )

        # Botón para abrir PDF
        self.btn_abrir_transcripcion.pack(pady=(5, 0))

        # Actualizar saldo
        self.lbl_saldo.configure(
            text=self.obtener_balance_deepgram()
        )



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
            
    def _on_send_message(self):
        """
        Envía el contenido de la caja de texto como "solo texto" (sin PDF).
        """
        texto = self.entry_message.get().strip()
        if texto == "":
            return

        self.entry_message.delete(0, "end")
        self.agregar_mensaje(texto, remitente="usuario")

        hilo = threading.Thread(target=self._worker_llm, args=(texto,))
        hilo.daemon = True
        self._mensaje_cargando_id = self.agregar_mensaje("Cargando respuesta...", remitente="bot")
        hilo.start()

    def _worker_llm(self, prompt: str):
        """
        Este método se ejecuta en un hilo aparte para no bloquear la GUI.
        Llama a preguntar_texto(prompt) y, al recibir la respuesta,
        vuelve al hilo principal para actualizar el chat.
        """
        try:
            respuesta_texto, _ = self.router_client.preguntar_texto(prompt)
            # Limpiar la respuesta eliminando los "###"
            respuesta_texto = self._limpiar_respuesta_openrouter(respuesta_texto)
        except Exception as e:
            respuesta_texto = f"Error al conectar con OpenRouter:\n{e}"

        self.after(0, self._update_chat_with_response, respuesta_texto)

    def _on_send_with_word(self):
        """
        Envía el contenido de la caja de texto junto a un PDF previamente seleccionado.
        """
        prompt = self.entry_message.get().strip()
        if prompt == "":
            return

        word_path = self.word_path  # Usar el PDF previamente seleccionado con el botón 📎

        if not word_path:
            messagebox.showwarning("Word no seleccionado", "Por favor selecciona un archivo con el botón 📎.")
            return


        texto_usuario = f"{prompt}\n(Consulta con Word: {os.path.basename(word_path)})"
        self.agregar_mensaje(texto_usuario, remitente="usuario")

        self.entry_message.delete(0, "end")

        hilo = threading.Thread(target=self._worker_llm_word, args=(word_path, prompt))
        hilo.daemon = True
        self._mensaje_cargando_id = self.agregar_mensaje("Cargando respuesta...", remitente="bot")
        hilo.start()

    def _worker_llm_word(self, word_path: str, prompt: str):
        """
        Este método se ejecuta en un hilo aparte. Llama a preguntar_con_word
        y luego regresa al hilo principal para mostrar la respuesta.
        """
        try:
            respuesta_texto, _ = self.router_client.preguntar_con_word(word_path, prompt)
            # Limpiar la respuesta eliminando los "###"
            respuesta_texto = self._limpiar_respuesta_openrouter(respuesta_texto)
        except Exception as e:
            respuesta_texto = f"Error al procesar Word con OpenRouter:\n{e}"

        self.after(0, self._update_chat_with_response, respuesta_texto)

    def _update_chat_with_response(self, respuesta: str):
        if hasattr(self, "_mensaje_cargando_id") and self._mensaje_cargando_id:
            # Busca el label hijo del frame para cambiar el texto
            for widget in self._mensaje_cargando_id.winfo_children():
                if isinstance(widget, ctk.CTkLabel):
                    widget.configure(text=respuesta)
                    break
            self._mensaje_cargando_id = None
        else:
            self.agregar_mensaje(respuesta, remitente="bot")

    def agregar_mensaje(self, texto, remitente="usuario"):
        """
        Crea una burbuja de chat con ancho flexible y altura automática:
        - Si remitente="usuario", se alinea a la derecha con fondo azul claro.
        - Si remitente="bot", se alinea a la izquierda con fondo gris claro.
        Luego fuerza el scroll para que siempre se vea el último mensaje.
        """
        bubble_fg = "#d9eaff" if remitente == "usuario" else "#f1f1f1"
        
        # Obtener el ancho actual del chat_area con múltiples intentos
        self.chat_area.update_idletasks()
        chat_width = self.chat_area.winfo_width()
        
        # Si el ancho no es válido, usar el ancho de la ventana como referencia
        if chat_width <= 100:
            window_width = self.winfo_width()
            # Estimar el ancho del chat considerando el panel izquierdo (~370px) y márgenes
            chat_width = max(300, window_width - 450)
        
        # Calcular wraplength dinámicamente con margen más conservador
        wraplength = max(200, chat_width - 150)

        # Frame contenedor para cada mensaje
        container_frame = ctk.CTkFrame(self.chat_area, fg_color="transparent")
        container_frame.grid(row=self.chat_row, column=0, padx=15, pady=5, sticky="ew")
        
        # Configurar el grid del contenedor
        if remitente == "usuario":
            container_frame.grid_columnconfigure(0, weight=1)  # Columna izquierda expandible
            container_frame.grid_columnconfigure(1, weight=0)  # Columna derecha fija
            bubble_column = 1
            bubble_sticky = "e"
        else:
            container_frame.grid_columnconfigure(0, weight=0)  # Columna izquierda fija
            container_frame.grid_columnconfigure(1, weight=1)  # Columna derecha expandible
            bubble_column = 0
            bubble_sticky = "w"

        # Creamos la burbuja sin ancho fijo
        frame_burbuja = ctk.CTkFrame(container_frame, fg_color=bubble_fg, corner_radius=10)

        # Etiqueta interna con wraplength dinámico y más padding
        label = ctk.CTkLabel(
            frame_burbuja,
            text=texto,
            wraplength=wraplength,
            justify="left",
            font=ctk.CTkFont(size=12),
            anchor="w"  # Alineación a la izquierda dentro del label
        )
        label.pack(padx=15, pady=10, fill="both", expand=True)  # Más padding

        # Colocamos la burbuja en la columna correspondiente
        frame_burbuja.grid(
            row=0,
            column=bubble_column,
            sticky=bubble_sticky,
            padx=5
        )
        
        self.chat_row += 1

        # Forzamos el scroll al fondo
        self.after(50, lambda: self.chat_area._parent_canvas.yview_moveto(1.0))
        return frame_burbuja, label
    
    # Método adicional para recalcular wraplength cuando el chat se inicializa
    def _inicializar_chat_responsive(self):
        """Método para llamar después de que la ventana esté completamente inicializada"""
        self.after(500, self._update_message_wraplength)