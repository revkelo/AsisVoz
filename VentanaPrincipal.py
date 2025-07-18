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
from PIL import Image

import utils


class AsisVozApp(TkinterDnD.Tk):
    def __init__(self,openrouter_key, deepgram_key):
        super().__init__()
        
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.pdf_path = None
        self.title("AsisVoz")
        self.geometry("1000x850")
        self.minsize(800, 600)  # Tamaño mínimo de ventana
        self.centrar_ventana()
        self.resizable(True, True)  # Permitir redimensionar
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

        # Icono y título del chatbot
        header_frame = ctk.CTkFrame(chat_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(20, 10))
        
        ctk.CTkLabel(
            header_frame,
            text="🤖",
            font=ctk.CTkFont(size=36)
        ).pack()
        ctk.CTkLabel(
            header_frame,
            text="Chatbot",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack()
        ctk.CTkLabel(
            header_frame,
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
        
        self.historial_archivo = "historial.txt"
        self.historial_transcripciones = self._cargar_historial()

        # Menú superior
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        self.historial_menu = tk.Menu(menubar, tearoff=0)
        self._actualizar_menu_historial()
        menubar.add_cascade(label="Historial", menu=self.historial_menu)

        # Actualizar binding del <Return>
        self.entry_message.bind("<Return>", lambda event: self._on_send_based_on_switch())

        # Bind para actualizar el chat cuando se redimensiona la ventana
        self.bind("<Configure>", self._on_window_resize)
        self._inicializar_chat_responsive()

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
        Llama a GET /v1/projects/:project_id/balances
        y muestra el amount en USD y COP.
        """
        # Obtener project_id
        self.aux = utils.obtener_project_id_deepgram(self.deepgram_api_key)
        url = f"https://api.deepgram.com/v1/projects/{self.aux}/balances"
        headers = {
            "Authorization": f"Token {self.deepgram_api_key}"
        }

        # Tasa de conversión (puedes actualizarla manualmente si deseas)
        tasa_dolar_a_cop = 4000  # Puedes cambiar esta cifra según la tasa actual

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Extraer amount y units del primer balance
            balances = data.get("balances", [])
            if balances:
                amount = balances[0].get("amount")  # valor en USD
                units = balances[0].get("units")

                # Convertir a pesos colombianos
                amount_cop = round(amount * tasa_dolar_a_cop)

                return f"💰 {amount:.2f} {units.upper()} / ${amount_cop:,} COP"
            else:
                return "❗ No se encontró ningún balance disponible."

        except requests.RequestException as e:
            print(f"❌ Error al obtener balance de Deepgram: {e}")
            return "❌ Error al obtener balance."

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


    def _cargar_historial(self):
        """
        Carga el historial desde historial.txt y devuelve una lista de rutas.
        """
        if not os.path.exists(self.historial_archivo):
            return []
        with open(self.historial_archivo, "r", encoding="utf-8") as f:
            lineas = [line.strip() for line in f.readlines() if line.strip()]
        return lineas[-20:]  # Solo las últimas 20

    def _guardar_en_historial(self, ruta_pdf):
        """
        Guarda una nueva transcripción y actualiza el menú.
        """
        # Añadir al historial en memoria
        self.historial_transcripciones.append(ruta_pdf)
        self.historial_transcripciones = self.historial_transcripciones[-20:]

        # Guardar todo en el archivo (manteniendo persistencia completa)
        with open(self.historial_archivo, "a", encoding="utf-8") as f:
            f.write(ruta_pdf + "\n")

        # Actualizar menú
        self._actualizar_menu_historial()

    def _actualizar_menu_historial(self):
        """
        Refresca el menú "Historial" con las últimas transcripciones.
        """
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

    def _abrir_transcripcion_desde_historial(self, ruta_pdf):
        if not os.path.exists(ruta_pdf):
            messagebox.showerror("Error", f"No se encontró el archivo:\n{ruta_pdf}")
            return

        try:
            sistema = platform.system()
            if sistema == "Windows":
                os.startfile(ruta_pdf)
            elif sistema == "Darwin":
                subprocess.call(["open", ruta_pdf])
            else:
                subprocess.call(["xdg-open", ruta_pdf])
        except Exception as e:
            messagebox.showerror("Error al abrir archivo", f"No se pudo abrir:\n{ruta_pdf}\n\n{e}")


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

    def _mostrar_aviso_banner(self, mensaje, color="#d1f0d1", duracion=3000):
        aviso = ctk.CTkFrame(self, fg_color=color, corner_radius=8)
        aviso.place(relx=0.5, rely=0.95, anchor="s")  # Posición inferior centrada

        ctk.CTkLabel(
            aviso,
            text=mensaje,
            text_color="black",
            font=ctk.CTkFont(size=12)
        ).pack(padx=10, pady=5)

        # Eliminar el aviso después de X milisegundos
        self.after(duracion, aviso.destroy)

    def _mostrar_aviso_banner_eliminar(self, mensaje, color="#f16046", duracion=3000):
        aviso = ctk.CTkFrame(self, fg_color=color, corner_radius=8)
        aviso.place(relx=0.5, rely=0.95, anchor="s")  # Posición inferior centrada

        ctk.CTkLabel(
            aviso,
            text=mensaje,
            text_color="black",
            font=ctk.CTkFont(size=12)
        ).pack(padx=10, pady=5)

        # Eliminar el aviso después de X milisegundos
        self.after(duracion, aviso.destroy)

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

        self.selected_files = list(archivos_validos)
        self._actualizar_lista_archivos()
        nombre_base = os.path.splitext(os.path.basename(self.selected_files[0]))[0]
        self.nombre_pdf = f"{nombre_base}.pdf"  # Guardamos el nombre para usarlo luego

        print("Archivos seleccionados:", self.selected_files)
        self._mostrar_aviso_banner("✔ Archivos cargados correctamente")

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
        self._mostrar_aviso_banner_eliminar("❌ Archivo eliminado correctamente")
        self.selected_files.remove(ruta)
        self._actualizar_lista_archivos()

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

        # Deshabilitar inmediatamente el botón
        self.btn_transcribir.configure(state="disabled")
        self.update_idletasks()

        try:
            carpeta_destino = filedialog.askdirectory(
                title="Selecciona una carpeta para guardar el PDF"
            )

            if not carpeta_destino:
                messagebox.showinfo("Cancelado", "No se seleccionó ninguna carpeta.")
                return

            nombre_base = os.path.splitext(os.path.basename(self.selected_files[0]))[0]

            nombre_base = (nombre_base[:70] + '...') if len(nombre_base) > 50 else nombre_base
            self.nombre_pdf = os.path.join(carpeta_destino, f"{nombre_base}.pdf")


            self.btn_transcribir.configure(text="Transcribiendo...")

            def tarea():
                try:
                    ruta = self.selected_files[0]
                    self.transcriptor.transcribir_audio(ruta, self.nombre_pdf)
                    self._mostrar_aviso_banner(f"🎧 Transcribiendo: {os.path.basename(ruta)}")
                    self.after(0, self._transcripcion_exitosa)
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Error", str(e)))
                finally:
                    self.after(0, lambda: self.btn_transcribir.configure(text="Transcribir", state="normal"))

            threading.Thread(target=tarea, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")


        if not carpeta_destino:
            messagebox.showinfo("Cancelado", "No se seleccionó ninguna carpeta.")
            return

        # Crear nombre del PDF usando el nombre del primer archivo de audio
        nombre_base = os.path.splitext(os.path.basename(self.selected_files[0]))[0]
        self.nombre_pdf = os.path.join(carpeta_destino, f"{nombre_base}.pdf")
            
        self.btn_transcribir.configure(text="Transcribiendo...", state="disabled")

        def tarea():
            try:
                ruta = self.selected_files[0]
                self.transcriptor.transcribir_audio(ruta, self.nombre_pdf)
                self._mostrar_aviso_banner(f"🎧 Transcribiendo: {os.path.basename(ruta)}")
                self.after(0, self._transcripcion_exitosa)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.after(0, lambda: self.btn_transcribir.configure(text="Transcribir", state="normal"))
        threading.Thread(target=tarea, daemon=True).start()

    def _transcripcion_exitosa(self):
        self._guardar_en_historial(self.nombre_pdf)
        messagebox.showinfo("Éxito", "Transcripción completada.")
        self._mostrar_aviso_banner("✅ Transcripción terminada")

        self._agregar_mensaje("✔ Transcripción completada", remitente="bot")
        self.btn_abrir_transcripcion.pack(pady=(5, 0))
        self.lbl_saldo.configure(
            text=self.obtener_balance_deepgram()
        )

    def _on_open_transcripcion(self):
        if not hasattr(self, "nombre_pdf"):
            messagebox.showerror("Error", "No se ha generado ningún PDF.")
            return
        

        ruta_pdf = self.nombre_pdf

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
            
    def _on_send_message(self):
        """
        Envía el contenido de la caja de texto como "solo texto" (sin PDF).
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
            # Limpiar la respuesta eliminando los "###"
            respuesta_texto = self._limpiar_respuesta_openrouter(respuesta_texto)
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
            # Limpiar la respuesta eliminando los "###"
            respuesta_texto = self._limpiar_respuesta_openrouter(respuesta_texto)
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
        return frame_burbuja
    # Método adicional para recalcular wraplength cuando el chat se inicializa
    def _inicializar_chat_responsive(self):
        """Método para llamar después de que la ventana esté completamente inicializada"""
        self.after(500, self._update_message_wraplength)