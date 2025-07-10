import os
import threading
import customtkinter as ctk
from DeepGramClient import DeepgramPDFTranscriber

from customtkinter import CTkImage

from OpenRouterClient import OpenRouterClient
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import tkinter as tk
import platform
import subprocess
from PIL import Image

import json

CONFIG_PATH = "./config.json"

def cargar_config():
    if not os.path.isfile(CONFIG_PATH):
        return {"openrouter_api_key": "", "deepgram_api_key": ""}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)



class AsisVozApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.pdf_path = None

        self.title("AsisVoz")
        self.geometry("1000x650")
        self.resizable(False, False)
        self.selected_files = []
        self._gif_frames = []
        self._gif_size = (200, 200)
        gif = Image.open("./media/cargando.gif")

        # Cliente de OpenRouter (tiene preguntar_texto y preguntar_con_pdf)
        self.config_data = cargar_config()

        self.openrouter_api_key = self.config_data.get("openrouter_api_key", "")
        self.deepgram_api_key = self.config_data.get("deepgram_api_key", "")

        self.router_client = OpenRouterClient(self.openrouter_api_key)
        self.transcriptor = DeepgramPDFTranscriber(self.deepgram_api_key)
        # Marco principal
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Crear barra de menú
        menubar = tk.Menu(self)

        # Crear un menú desplegable
        menu_opciones = tk.Menu(menubar, tearoff=0)
        menu_opciones.add_command(label="Cambiar API Key de Deepgram", command=self._cambiar_api_deepgram)
        menu_opciones.add_command(label="Cambiar API de OpenRouter", command=self._cambiar_api_openrouter)
        menu_opciones.add_separator()
        #menu_opciones.add_command(label="Salir", command=self.quit)

        # Añadir el menú desplegable a la barra de menú
        menubar.add_cascade(label="Opciones", menu=menu_opciones)

        # Configurar la ventana para usar esta barra de menú
        self.config(menu=menubar)

        # ─── LEFT (Audio + Transcripción) ───────────────────────────────────
        left_frame = ctk.CTkFrame(main_frame, width=320, fg_color="transparent")
        left_frame.pack(side="left", anchor="n", padx=(0, 30), fill="y")

        # Título “Audio”
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
            width=300,
            height=160,
            border_width=1,
            border_color="#aaaaaa"
        )
        upload_border.pack(pady=(0, 10))
        upload_border.pack_propagate(False)
        self._crear_area_upload(upload_border)

        # Lista de archivos seleccionados
        self.archivos_frame = ctk.CTkFrame(left_frame, fg_color="white", corner_radius=10)
        self.archivos_frame.pack(pady=(5, 20), fill="x")

        # Botón “Transcribir”
        self.btn_transcribir = ctk.CTkButton(
            left_frame,
            text="Transcribir",
            width=200,
            height=35,
            command=self._on_transcribir
        )
        self.btn_transcribir.pack(pady=(10, 5))

        # Botón “Abrir transcripción” (oculto inicialmente)
        self.btn_abrir_transcripcion = ctk.CTkButton(
            left_frame,
            text="Abrir transcripción generada",
            width=200,
            height=35,
            command=self._on_open_transcripcion
        )
        self.btn_abrir_transcripcion.pack(pady=(5, 0))
        self.btn_abrir_transcripcion.pack_forget()

        # ─── RIGHT (Chatbot) ────────────────────────────────────────────────
        right_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        right_frame.pack(side="left", fill="both", expand=True)

        chat_frame = ctk.CTkFrame(
            right_frame,
            width=620,            # ancho total del área de chat
            height=580,
            border_width=1,
            border_color="#aaaaaa",
            corner_radius=15
        )
        chat_frame.pack(anchor="n", padx=10, pady=10, fill="y")
        chat_frame.pack_propagate(False)

        # Icono y título del chatbot
        ctk.CTkLabel(
            chat_frame,
            text="🤖",
            font=ctk.CTkFont(size=36)
        ).pack(pady=(20, 5))
        ctk.CTkLabel(
            chat_frame,
            text="Chatbot",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack()
        ctk.CTkLabel(
            chat_frame,
            text="¡Hola! ¿Cómo puedo ayudarte hoy?",
            font=ctk.CTkFont(size=12),
            wraplength=580,        # cabrá en 580 px
            justify="center"
        ).pack(pady=(5, 10))

        # Área scrollable para los mensajes (usa width=620)
        self.chat_area = ctk.CTkScrollableFrame(
            chat_frame,
            width=620,
            height=360,
            fg_color="white",
            corner_radius=10
        )
        
        try:
            index = 0
            while True:
                # 1) copiar, 2) convertir a RGBA, 3) escalar al tamaño deseado
                frame = (
                    gif.copy()
                       .convert("RGBA")
                       .resize(self._gif_size, Image.LANCZOS)
                )
                # 4) crear el PhotoImage y guardarlo
                self._gif_frames.append(CTkImage(light_image=frame, size=self._gif_size))

                index += 1
                gif.seek(index)
        except EOFError:
            pass
        
        self.lbl_gif = ctk.CTkLabel(
            left_frame,
            image=None,
            width=self._gif_size[0],
            height=self._gif_size[1],
            fg_color="transparent",
            text=""
        )
        self.lbl_gif.place_forget()


        self.chat_area.pack(padx=10, pady=(0, 10), fill="both", expand=True)
        # Ahora sólo definimos UNA columna (columna 0)
        self.chat_area.grid_columnconfigure(0, weight=1)
        self.chat_row = 0

        # Marco inferior con entrada de texto + botones de envío
        frame_entry = ctk.CTkFrame(chat_frame, fg_color="transparent")
        frame_entry.pack(padx=10, pady=(0, 15), fill="x")

        # Campo de texto
        self.entry_message = ctk.CTkEntry(
            frame_entry,
            text_color="gray",
            placeholder_text="Escribe un mensaje..."
        )
        self.entry_message.pack(side="left", fill="x", expand=True)
        self.entry_message.bind("<Return>", lambda event: self._on_send_message())

        # Switch para activar o desactivar uso de PDF
        self.use_pdf_switch = ctk.CTkSwitch(
            frame_entry,
            text="Usar PDF",
            command=self._on_switch_toggle
        )
        self.use_pdf_switch.pack(side="left", padx=(5, 10))
        
        # Botón de enviar unificado
        ctk.CTkButton(
            frame_entry,
            text="Enviar",
            width=60,
            height=32,
            command=self._on_send_based_on_switch
        ).pack(side="left")

        # Actualizar binding del <Return>
        self.entry_message.bind("<Return>", lambda event: self._on_send_based_on_switch())


    def _on_select_pdf(self):
        ruta = filedialog.askopenfilename(
        title="Selecciona un archivo PDF",
        filetypes=[("Archivos PDF", "*.pdf")]
    )
        if ruta:
            self.pdf_path = ruta
            messagebox.showinfo("Archivo cargado", f"PDF seleccionado:\n{os.path.basename(ruta)}")
        else:
            self.pdf_path = None

    def _on_switch_toggle(self):
        if self.use_pdf_switch.get() == 0:
            self.pdf_path = None  # limpiar si desactiva

    def _on_send_based_on_switch(self):
        if self.use_pdf_switch.get() == 1:
            ruta = filedialog.askopenfilename(
                title="Selecciona un archivo PDF",
                filetypes=[("Archivos PDF", "*.pdf")]
            )
            if not ruta:
                messagebox.showwarning("PDF no seleccionado", "No se seleccionó ningún archivo.")
                return

            self.pdf_path = ruta
            self._on_send_with_pdf()
        else:
            self._on_send_message()


    def _on_switch_toggle(self):
        if self.use_pdf_switch.get() == 0:
            self.pdf_path = None  # limpiar si desactiva

    def _on_send_based_on_switch(self):
        if self.use_pdf_switch.get() == 1:
            ruta = filedialog.askopenfilename(
                title="Selecciona un archivo PDF",
                filetypes=[("Archivos PDF", "*.pdf")]
            )
            if not ruta:
                messagebox.showwarning("PDF no seleccionado", "No se seleccionó ningún archivo.")
                return

            self.pdf_path = ruta
            self._on_send_with_pdf()
        else:
            self._on_send_message()


    def _start_gif(self):
        # en lugar de pack(), lo hacemos visible con place again
        self.lbl_gif.place(relx=0.5, y=400, anchor="n")
        self._gif_index = 0
        self._animate_gif()

    def _animate_gif(self):
        frame = self._gif_frames[self._gif_index]
        self.lbl_gif.configure(image=frame)
        self._gif_index = (self._gif_index + 1) % len(self._gif_frames)
        self._gif_job = self.after(100, self._animate_gif)  # 10 fps

    def _stop_gif(self):
        if hasattr(self, "_gif_job"):
            self.after_cancel(self._gif_job)
        # ocultar con place_forget()
        self.lbl_gif.place_forget()


    def _crear_area_upload(self, contenedor):
        ctk.CTkLabel(
            contenedor,
            text="🎵",
            font=ctk.CTkFont(size=32)
        ).pack(pady=(10, 5))
        ctk.CTkLabel(
            contenedor,
            text="Arrastra tus archivos de audio para comenzar la carga",
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

        archivos_validos = [archivo for archivo in archivos if archivo.lower().endswith(extensiones_validas)]

        if not archivos_validos:
            messagebox.showerror("Error", "Por favor selecciona solo archivos de audio válidos.")
            return

        if len(archivos_validos) > 5:
            messagebox.showerror("Error", "Solo puedes seleccionar hasta 5 archivos.")
            return

        self.selected_files = list(archivos_validos)
        self._actualizar_lista_archivos()



    def _on_browse_files(self):
        tipos_permitidos = [("Audio files", "*.mp3 *.wav *.m4a *.flac *.ogg *.aac *.webm *.opus"),]
        rutas = filedialog.askopenfilenames(
            title="Selecciona archivos de audio",
            filetypes=tipos_permitidos
        )

        extensiones_validas = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.webm', '.opus')
        archivos_validos = [ruta for ruta in rutas if ruta.lower().endswith(extensiones_validas)]

        if not archivos_validos:
                messagebox.showerror("Error", "Por favor selecciona solo archivos de audio válidos.")
        else:
                # Aquí haces lo que necesitas con los archivos
                print("Archivos seleccionados:")
                for archivo in archivos_validos:
                    print(archivo)

        if not rutas:
            return

        if len(rutas) > 5:
            messagebox.showerror("Error", "Solo puedes seleccionar hasta 5 archivos.")
            return

        self.selected_files = list(rutas)
        self._actualizar_lista_archivos()
        print("Archivos seleccionados:", self.selected_files)

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
        self.selected_files.remove(ruta)
        self._actualizar_lista_archivos()

    def _cambiar_api_deepgram(self):
        ventana = tk.Toplevel()
        ventana.title("Cambiar API Key de Deepgram")
        ventana.geometry("400x150")
        ventana.resizable(False, False)

        # Centrar ventana
        ventana.update_idletasks()
        ancho, alto = 400, 150
        x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
        y = (ventana.winfo_screenheight() // 2) - (alto // 2)
        ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

        # Instrucciones
        tk.Label(ventana, text="Selecciona un archivo .txt con tu API key:").pack(pady=(20, 10))

        def seleccionar_archivo():
            ruta = filedialog.askopenfilename(
                title="Selecciona un archivo de texto",
                filetypes=[("Archivos de texto", "*.txt")]
            )

            if not ruta:
                return

            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    nueva_key = f.read().strip()

                if not nueva_key:
                    messagebox.showerror("Error", "El archivo está vacío.", parent=ventana)
                    return

                self.deepgram_api_key = nueva_key
                self.transcriptor = DeepgramTranscriber(self.deepgram_api_key)
                self.config_data["deepgram_api_key"] = nueva_key
                guardar_config(self.config_data)

                messagebox.showinfo("Éxito", "API key de Deepgram actualizada.", parent=ventana)
                ventana.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"No se pudo leer el archivo:\n{e}", parent=ventana)

        # Botón para seleccionar archivo
        tk.Button(ventana, text="Seleccionar archivo", command=seleccionar_archivo).pack(pady=(0, 20))


    def _cambiar_api_openrouter(self):
        ventana = tk.Toplevel()
        ventana.title("Cambiar API Key de OpenRouter")
        ventana.geometry("400x150")
        ventana.resizable(False, False)

        # Centrar ventana
        ventana.update_idletasks()
        ancho, alto = 400, 150
        x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
        y = (ventana.winfo_screenheight() // 2) - (alto // 2)
        ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

        tk.Label(ventana, text="Selecciona un archivo .txt con tu API key:").pack(pady=(20, 10))

        def seleccionar_archivo():
            ruta = filedialog.askopenfilename(
                title="Selecciona un archivo de texto",
                filetypes=[("Archivos de texto", "*.txt")]
            )

            if not ruta:
                return

            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    nueva_key = f.read().strip()

                if not nueva_key:
                    messagebox.showerror("Error", "El archivo está vacío.", parent=ventana)
                    return

                # Validación opcional de API key (por ejemplo, OpenRouter usa claves largas alfanuméricas)
                if len(nueva_key) < 20:
                    messagebox.showwarning("Advertencia", "La clave parece demasiado corta. ¿Es válida?", parent=ventana)

                self.openrouter_api_key = nueva_key
                self.router_client = OpenRouterClient(self.openrouter_api_key)
                self.config_data["openrouter_api_key"] = nueva_key
                guardar_config(self.config_data)

                messagebox.showinfo("Éxito", "API key de OpenRouter actualizada.", parent=ventana)
                ventana.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"No se pudo leer el archivo:\n{e}", parent=ventana)

        tk.Button(ventana, text="Seleccionar archivo", command=seleccionar_archivo).pack(pady=(0, 20))


    # ──────────────────────────────────────────────────────────────────────
    # Lógica de transcripción en segundo plano (Deepgram)
    # ──────────────────────────────────────────────────────────────────────
   
    """
    def _on_transcribir(self):
        if not self.selected_files:
            messagebox.showinfo("Sin archivos", "Primero selecciona archivos.")
            return

        self.btn_transcribir.configure(text="Transcribiendo...", state="disabled")
        ruta = self.selected_files[0]
        print("[AsisVozApp] (HILO PRINCIPAL) Ruta del archivo a transcribir:", ruta)

        hilo = threading.Thread(target=self._worker_transcribir, args=(ruta,))
        hilo.daemon = True
        hilo.start()
        
    """   
        

    
 

    def _on_transcribir(self):
        if not self.selected_files:
            messagebox.showinfo("Sin archivos", "Primero selecciona archivos.")
            return

        self.btn_transcribir.configure(text="Transcribiendo...", state="disabled")

        def tarea():
            try:
                #self.after(0, self._start_gif)
              
                ruta = self.selected_files[0]
                self.transcriptor.transcribir_audio(ruta)
                self.after(0, self._transcripcion_exitosa)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                #self.after(0, self._stop_gif)
                self.after(0, lambda: self.btn_transcribir.configure(text="Transcribir", state="normal"))
        threading.Thread(target=tarea, daemon=True).start()

    def _transcripcion_exitosa(self):
        messagebox.showinfo("Éxito", "Transcripción completada.")
        self._agregar_mensaje("✔ Transcripción completada", remitente="bot")
        self.btn_abrir_transcripcion.pack(pady=(5, 0))

    def _on_open_transcripcion(self):

        ruta_pdf = "transcripcion.pdf"
        
        if not os.path.exists(ruta_pdf):
            messagebox.showerror("Archivo no encontrado", f"No se encontró el archivo {ruta_pdf}.")
            return
        
        sistema = platform.system()
        
        if sistema == "Windows":
            os.startfile(ruta_pdf)
        elif sistema == "Darwin":
            subprocess.call(["open", ruta_pdf])
        else:
            subprocess.call(["xdg-open", ruta_pdf])
            
    # ──────────────────────────────────────────────────────────────────────
    # Lógica del chatbot (OpenRouter) en hilos para no bloquear la GUI
    # ──────────────────────────────────────────────────────────────────────
    def _on_send_message(self):
        """
        Envía el contenido de la caja de texto como “solo texto” (sin PDF).
        """
        texto = self.entry_message.get().strip()
        if texto == "":
            return

        self.entry_message.delete(0, "end")
        self._agregar_mensaje(texto, remitente="usuario")

        hilo = threading.Thread(target=self._worker_llm, args=(texto,))
        hilo.daemon = True
        self._mensaje_cargando_id = self._agregar_mensaje("Cargando respuesta...", remitente="bot")
        hilo.start()

    def _worker_llm(self, prompt: str):
        """
        Este método se ejecuta en un hilo aparte para no bloquear la GUI.
        Llama a preguntar_texto(prompt) y, al recibir la respuesta,
        vuelve al hilo principal para actualizar el chat.
        """
        try:
            respuesta_texto, _ = self.router_client.preguntar_texto(prompt)
        except Exception as e:
            respuesta_texto = f"Error al conectar con OpenRouter:\n{e}"

        self.after(0, self._update_chat_with_response, respuesta_texto)

    def _on_send_with_pdf(self):
        """
        Envía el contenido de la caja de texto junto a un PDF previamente seleccionado.
        """
        prompt = self.entry_message.get().strip()
        if prompt == "":
            return

        pdf_path = self.pdf_path  # Usar el PDF previamente seleccionado con el botón 📎

        if not pdf_path:
            messagebox.showwarning("PDF no seleccionado", "Por favor selecciona un archivo con el botón 📎.")
            return

        texto_usuario = f"{prompt}\n(Consulta con PDF: {os.path.basename(pdf_path)})"
        self._agregar_mensaje(texto_usuario, remitente="usuario")
        self.entry_message.delete(0, "end")

        hilo = threading.Thread(target=self._worker_llm_pdf, args=(pdf_path, prompt))
        hilo.daemon = True
        self._mensaje_cargando_id = self._agregar_mensaje("Cargando respuesta...", remitente="bot")
        hilo.start()


    def _worker_llm_pdf(self, pdf_path: str, prompt: str):
        """
        Este método se ejecuta en un hilo aparte. Llama a preguntar_con_pdf
        y luego regresa al hilo principal para mostrar la respuesta.
        """
        try:
            respuesta_texto, _ = self.router_client.preguntar_con_pdf(pdf_path, prompt)
        except Exception as e:
            respuesta_texto = f"Error al procesar PDF con OpenRouter:\n{e}"

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
            self._agregar_mensaje(respuesta, remitente="bot")

    def _agregar_mensaje(self, texto, remitente="usuario"):
        """
        Crea una burbuja de chat con ancho fijo (560 px) y altura automática:
        - Si remitente="usuario", se alinea a la derecha con fondo azul claro.
        - Si remitente="bot", se alinea a la izquierda con fondo gris claro.
        Luego fuerza el scroll para que siempre se vea el último mensaje.
        """
        bubble_fg = "#d9eaff" if remitente == "usuario" else "#f1f1f1"
        text_anchor = "e" if remitente == "usuario" else "w"

        # Creamos la burbuja con ancho fijo de 560 px
        frame_burbuja = ctk.CTkFrame(self.chat_area, fg_color=bubble_fg, corner_radius=10)
        frame_burbuja.configure(width=560)  # ancho máximo fijo
        # NO llamamos a pack_propagate(False): permitimos que la altura crezca al contenido.

        # Etiqueta interna con wraplength = 540 px
        label = ctk.CTkLabel(
            frame_burbuja,
            text=texto,
            wraplength=300,  # texto se quiebra antes de llegar a 540 px
            justify="left",
            font=ctk.CTkFont(size=12)
        )
        label.pack(padx=10, pady=5)

        # Colocamos la burbuja en la fila correspondiente
        frame_burbuja.grid(
            row=self.chat_row,
            column=0,
            padx=10,
            pady=2,
            sticky=text_anchor  # 'e' si es usuario, 'w' si es bot
        )
        self.chat_row += 1

        # Forzamos el scroll al fondo
        self.after(50, lambda: self.chat_area._parent_canvas.yview_moveto(1.0))
        return frame_burbuja

if __name__ == "__main__":
    # Reemplaza "TU_API_KEY_AQUI" con tu API key real de OpenRouter:

    app = AsisVozApp()
    app.mainloop()
