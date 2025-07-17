import tkinter as tk
from VentanaKeys import VentanaLicencia, cargar_keys
from VentanaPrincipal import AsisVozApp  # Importa la app principal
from utils import validar_api_key_deepgram, verificar_openrouter_key


ventana_licencia = None

def mostrar_ventana_licencia(root):
    global ventana_licencia

    if ventana_licencia is not None and tk.Toplevel.winfo_exists(ventana_licencia):
        ventana_licencia.deiconify()
        ventana_licencia.lift()
        ventana_licencia.focus_force()
    else:
        ventana_licencia = VentanaLicencia(root)

def centrar_ventana(ventana, ancho, alto):
    ventana.update_idletasks()
    x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
    y = (ventana.winfo_screenheight() // 2) - (alto // 2)
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

def iniciar_asisvoz(root):
    root.withdraw()  # Oculta la ventana principal

    app = AsisVozApp()

    # Cuando se cierre AsisVoz, vuelve a mostrar la ventana principal
    def on_close():
        app.destroy()
        root.deiconify()

    app.protocol("WM_DELETE_WINDOW", on_close)
    app.mainloop()

def crear_ventana_principal():
    cargar_keys()

    root = tk.Tk()
    root.title("App Principal")
    ancho_ventana, alto_ventana = 600, 400
    centrar_ventana(root, ancho_ventana, alto_ventana)

    menubar = tk.Menu(root)
    root.config(menu=menubar)

    opciones_menu = tk.Menu(menubar, tearoff=0)
    opciones_menu.add_command(label="Registrar Licencia", command=lambda: mostrar_ventana_licencia(root))
    opciones_menu.add_separator()
    opciones_menu.add_command(label="Salir", command=root.quit)

    menubar.add_cascade(label="Opciones", menu=opciones_menu)

    btn_frame = tk.Frame(root)
    btn_frame.place(relx=0.5, rely=0.5, anchor="center")

    btn_iniciar = tk.Button(
        btn_frame,
        text="Iniciar Aplicación",
        font=("Arial", 16),
        width=20,
        height=2,
        command=lambda: iniciar_asisvoz(root)
    )
    btn_iniciar.pack()

    root.mainloop()

if __name__ == "__main__":
    crear_ventana_principal()
