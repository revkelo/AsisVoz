import customtkinter as ctk
import tkinter as tk  # Necesario para Menu
from tkinter import messagebox
from VentanaKeys import VentanaLicencia, cargar_keys
from VentanaPrincipal import AsisVozApp
import utils  # Importa la app principal

# Configuración del tema
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

# Lista de licencias válidas
LICENCIAS_VALIDAS = [
    "ABC123-DEF456-GHI789",
    "JKL321-MNO654-PQR987",
    "TUV111-WXY222-ZZZ333"
]

ventana_licencia = None
ventana_registro_equipo = None

def traer_ventana_al_frente(ventana, modal=True):
    """Función para traer una ventana al frente de manera robusta"""
    try:
        ventana.deiconify()  # Asegura que la ventana esté visible
        ventana.lift()  # Levanta la ventana
        ventana.attributes('-topmost', True)  # Pone la ventana siempre arriba temporalmente
        ventana.focus_force()  # Fuerza el foco
        
        if modal:
            ventana.grab_set()  # Hace la ventana modal solo si se especifica
        
        # Después de un momento, quita el always-on-top pero mantiene el foco
        ventana.after(100, lambda: ventana.attributes('-topmost', False))
    except:
        pass

def mostrar_ventana_licencia(root):
    global ventana_licencia
    if ventana_licencia is not None and ventana_licencia.winfo_exists():
        traer_ventana_al_frente(ventana_licencia, modal=False)  # No modal para ventana de licencia
    else:
        ventana_licencia = VentanaLicencia(root)
        
        # Configurar el cierre adecuado para la ventana de licencia
        original_destroy = ventana_licencia.destroy
        def safe_destroy():
            try:
                ventana_licencia.grab_release()  # Libera el grab si existe
            except:
                pass
            original_destroy()
        
        ventana_licencia.destroy = safe_destroy
        ventana_licencia.protocol("WM_DELETE_WINDOW", safe_destroy)
        
        traer_ventana_al_frente(ventana_licencia, modal=False)  # No modal para ventana de licencia

def verificar_licencia(clave: str) -> bool:
    return clave.strip() in LICENCIAS_VALIDAS

def mostrar_ventana_registro_equipo(root):
    global ventana_registro_equipo
    if ventana_registro_equipo is not None and ventana_registro_equipo.winfo_exists():
        traer_ventana_al_frente(ventana_registro_equipo, modal=True)
    else:
        ventana_registro_equipo = ctk.CTkToplevel(root)
        ventana_registro_equipo.title("Registrar Equipo")
        ventana_registro_equipo.geometry("400x200")
        ventana_registro_equipo.resizable(False, False)
        
        # Centrar la ventana
        centrar_ventana(ventana_registro_equipo, 400, 200)
        
        # Configurar como ventana modal
        ventana_registro_equipo.transient(root)
        ventana_registro_equipo.grab_set()
        
        label_titulo = ctk.CTkLabel(
            ventana_registro_equipo, 
            text="Ingrese su clave de licencia:", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        label_titulo.pack(pady=20)

        entry_clave = ctk.CTkEntry(
            ventana_registro_equipo, 
            font=ctk.CTkFont(size=12), 
            width=300,
            height=35,
            placeholder_text="Ingrese su clave de licencia"
        )
        entry_clave.pack(pady=10)

        def registrar():
            clave = entry_clave.get()
            if verificar_licencia(clave):
                messagebox.showinfo("Licencia válida", "✅ Licencia válida. Equipo registrado.")
                ventana_registro_equipo.grab_release()  # Libera el grab antes de cerrar
                ventana_registro_equipo.destroy()
            else:
                messagebox.showerror("Licencia inválida", "❌ La clave de licencia no es válida.")

        def cerrar_ventana():
            ventana_registro_equipo.grab_release()  # Libera el grab antes de cerrar
            ventana_registro_equipo.destroy()

        btn_registrar = ctk.CTkButton(
            ventana_registro_equipo, 
            text="Registrar", 
            font=ctk.CTkFont(size=12, weight="bold"),
            width=150,
            height=35,
            command=registrar
        )
        btn_registrar.pack(pady=20)
        
        # Manejar el cierre de la ventana
        ventana_registro_equipo.protocol("WM_DELETE_WINDOW", cerrar_ventana)
        
        # Traer al frente después de crear todos los elementos
        ventana_registro_equipo.after(10, lambda: traer_ventana_al_frente(ventana_registro_equipo, modal=True))

def centrar_ventana(ventana, ancho, alto):
    ventana.update_idletasks()
    x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
    y = (ventana.winfo_screenheight() // 2) - (alto // 2)
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

def iniciar_asisvoz(root):
    root.withdraw()
    app = AsisVozApp()
    def on_close():
        app.destroy()
        root.deiconify()
    app.protocol("WM_DELETE_WINDOW", on_close)
    app.mainloop()

def crear_ventana_principal():
    cargar_keys()

    root = ctk.CTk()
    root.title("App Principal")
    ancho_ventana, alto_ventana = 600, 400
    centrar_ventana(root, ancho_ventana, alto_ventana)

    # Crear menú
    menubar = tk.Menu(root)
    root.config(menu=menubar)

    menu_opciones = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Opciones", menu=menu_opciones)
    menu_opciones.add_command(label="Registrar Licencia", command=lambda: mostrar_ventana_licencia(root))
    menu_opciones.add_command(label="Registrar Equipo", command=lambda: mostrar_ventana_registro_equipo(root))
    menu_opciones.add_separator()
    menu_opciones.add_command(label="Salir", command=root.quit)

    # Frame principal
    main_frame = ctk.CTkFrame(root)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Título
    titulo_label = ctk.CTkLabel(
        main_frame, 
        text="Sistema de Gestión de Licencias", 
        font=ctk.CTkFont(size=24, weight="bold")
    )
    titulo_label.pack(pady=(40, 30))

    # Botón principal
    btn_iniciar = ctk.CTkButton(
        main_frame,
        text="Iniciar Aplicación",
        font=ctk.CTkFont(size=18, weight="bold"),
        width=250,
        height=60,
        command=lambda: iniciar_asisvoz(root)
    )
    btn_iniciar.pack(pady=20)

    # Info
    info_label = ctk.CTkLabel(
        main_frame,
        text="Asegúrese de tener una licencia válida antes de iniciar la aplicación",
        font=ctk.CTkFont(size=10),
        text_color="gray"
    )
    info_label.pack(pady=(10, 20))
    
    utils.descifrar_y_extraer_claves("config.json.cif")

    root.mainloop()

if __name__ == "__main__":
    crear_ventana_principal()