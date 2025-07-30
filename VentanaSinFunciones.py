import customtkinter as ctk
from customtkinter import CTkImage
from tkinterdnd2 import TkinterDnD
import tkinter as tk
from PIL import Image, ImageTk, ImageSequence
import os


class AsisVozVisualMock(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("AsisVoz (Visual Mock)")
        self.geometry("1000x850")
        self.minsize(800, 600)
        self.resizable(True, True)
        self.centrar_ventana()

        # Menú superior
        self._crear_menu()

        # Main Frame
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Left Frame
        left_frame = ctk.CTkFrame(main_frame, fg_color="transparent", width=350)
        left_frame.pack(side="left", anchor="n", padx=(0, 20), fill="y")

        ctk.CTkLabel(left_frame, text="Audio", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(left_frame, text="Agrega tus archivos de audio aquí", font=ctk.CTkFont(size=12), wraplength=300, justify="left").pack(anchor="w", pady=(0, 15))

        upload_border = ctk.CTkFrame(left_frame, height=160, border_width=1, border_color="#aaaaaa")
        upload_border.pack(pady=(0, 10), fill="x")
        upload_border.pack_propagate(False)

        ctk.CTkLabel(upload_border, text="🎵", font=ctk.CTkFont(size=32)).pack(pady=(10, 5))
        ctk.CTkLabel(upload_border, text="Arrastra tus archivos de audio\npara comenzar la carga", font=ctk.CTkFont(size=11), wraplength=280, justify="center").pack()
        ctk.CTkLabel(upload_border, text="O", font=ctk.CTkFont(size=11)).pack(pady=5)
        ctk.CTkButton(upload_border, text="Buscar archivos de audio").pack()

        archivos_frame = ctk.CTkFrame(left_frame, fg_color="white", corner_radius=10)
        archivos_frame.pack(pady=(5, 20), fill="x")

        ctk.CTkButton(left_frame, text="Transcribir", height=35).pack(pady=(10, 5), fill="x")
        ctk.CTkButton(left_frame, text="Abrir transcripción generada", height=35).pack(pady=(5, 0), fill="x")

        # Right Frame
        right_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        right_frame.pack(side="left", fill="both", expand=True)

        chat_frame = ctk.CTkFrame(right_frame, border_width=1, border_color="#aaaaaa", corner_radius=15)
        chat_frame.pack(anchor="n", padx=10, pady=(40, 10), fill="both", expand=True)

        header_frame = ctk.CTkFrame(chat_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(20, 10))

        # Cargar y mostrar logo en lugar del emoji
        logo_path = "media/icono.png"
        if os.path.exists(logo_path):
            logo_img = CTkImage(dark_image=Image.open(logo_path), size=(48, 48))
            ctk.CTkLabel(header_frame, image=logo_img, text="").pack()
        else:
            ctk.CTkLabel(header_frame, text="🤖", font=ctk.CTkFont(size=36)).pack()

        ctk.CTkLabel(header_frame, text="Chatbot", font=ctk.CTkFont(size=16, weight="bold")).pack()
        ctk.CTkLabel(header_frame, text="¡Hola! ¿Cómo puedo ayudarte hoy?", font=ctk.CTkFont(size=12), justify="center").pack(pady=(5, 0))

        chat_area = ctk.CTkScrollableFrame(chat_frame, fg_color="white", corner_radius=10)
        chat_area.pack(padx=15, pady=(0, 10), fill="both", expand=True)

        frame_entry = ctk.CTkFrame(chat_frame, fg_color="transparent")
        frame_entry.pack(padx=10, pady=(0, 15), fill="x")

        ctk.CTkEntry(frame_entry, text_color="black", placeholder_text="Escribe un mensaje...").pack(side="left", fill="x", expand=True)
        ctk.CTkSwitch(frame_entry, text="Usar PDF").pack(side="left", padx=(5, 10))
        ctk.CTkButton(frame_entry, text="Enviar", width=60, height=32).pack(side="left")



    def _crear_menu(self):
        menubar = tk.Menu(self)
        historial_menu = tk.Menu(menubar, tearoff=0)


        menubar.add_cascade(label="Historial", menu=historial_menu)
        self.config(menu=menubar)


    def animar_gif(self):
        self.gif_index = (self.gif_index + 1) % len(self.frames)
        self.gif_label.configure(image=self.frames[self.gif_index])
        self.after(100, self.animar_gif)

    def centrar_ventana(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f'+{x}+{y}')


if __name__ == "__main__":
    app = AsisVozVisualMock()
    app.mainloop()
