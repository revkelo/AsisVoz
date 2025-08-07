import json
import os
import sys
import customtkinter as ctk
import tkinter as tk  # Necesario para Menu
from tkinter import messagebox
from VentanaKeys import VentanaLicencia
from VentanaPrincipal import AsisVozApp
import utils  
from PIL import Image



# Configuración del tema
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Lista de licencias válidas
LICENCIAS_VALIDAS = [
     "A7X4D9-KLM3Q2-Z8N6YP",
     "P3W9XK-8JDLQ1-R2M4VT",
     "QZ8C1B-MN4V7E-5TPR6X"
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
        ventana_licencia = VentanaLicencia(root, utils.OPENROUTER_API_KEY, utils.DEEPGRAM_API_KEY)
        
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

ARCHIVO_ESTADO_LICENCIA = "estado_licencia.json"

def validar_keys():
    if not utils.OPENROUTER_API_KEY or not utils.DEEPGRAM_API_KEY:
        # Mostrar mensaje de error
        messagebox.showerror("Claves API inválidas", "❌ Las claves API no están correctamente configuradas.")
        return False
    return True


# ✅ Verificar si la licencia ingresada está en la lista
def verificar_licencia(clave_ingresada):
    return clave_ingresada in LICENCIAS_VALIDAS


# ✅ Guardar en archivo local que la licencia fue aceptada
def guardar_licencia_valida():
    try:
        with open(ARCHIVO_ESTADO_LICENCIA, "w") as f:
            json.dump({"licencia_valida": True}, f)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo guardar el estado de licencia:\n{e}")


# ✅ Verificar si ya hay una licencia registrada válida
def licencia_ya_registrada():
    if os.path.exists(ARCHIVO_ESTADO_LICENCIA):
        try:
            with open(ARCHIVO_ESTADO_LICENCIA, "r") as f:
                data = json.load(f)
                return data.get("licencia_valida", False)
        except:
            return False
    return False

def validar_licencia(self):
        clave = self.entry_licencia.get().strip()
        if verificar_licencia(clave):
            guardar_licencia_valida()
            messagebox.showinfo("✅ Licencia válida", "La licencia fue aceptada.")
            self.destroy()
        else:
            messagebox.showerror("❌ Licencia inválida", "La licencia no es válida.")


# ✅ Lógica para iniciar app solo si ya hay licencia
def iniciar_si_hay_licencia(root):
    if licencia_ya_registrada():
        
        iniciar_asisvoz(root)
    else:
        messagebox.showwarning("Licencia Requerida", "⚠️ Debe ingresar una licencia válida.")
        VentanaLicencia(root)

def mostrar_ventana_registro_equipo(root):
    global ventana_registro_equipo
    if ventana_registro_equipo is not None and ventana_registro_equipo.winfo_exists():
        traer_ventana_al_frente(ventana_registro_equipo, modal=True)
    else:
        ventana_registro_equipo = ctk.CTkToplevel(root)
        ventana_registro_equipo.title("Registrar Equipo")
        ico_path = utils.ruta_absoluta("media/logo.ico")
        if os.path.exists(ico_path):
            try:
                ventana_registro_equipo.iconbitmap(ico_path)
            except Exception:
                pass
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
                guardar_licencia_valida()  # ✅ Guarda que la licencia es válida
                messagebox.showinfo("Licencia válida", "✅ Licencia válida. Equipo registrado.")
                ventana_registro_equipo.grab_release()
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
    
    if not licencia_ya_registrada():
        # Mostrar advertencia
        messagebox.showwarning("Licencia requerida", "⚠️ Debe ingresar una licencia válida antes de continuar.")
        # Después de cerrar el mensaje, mostrar la ventana para registrar equipo
        root.after(100, lambda: mostrar_ventana_registro_equipo(root))
        return

    if not validar_keys():
        
        # Después de cerrar el mensaje, mostrar la ventana para registrar claves
        root.after(100, lambda: mostrar_ventana_licencia(root))  # reutiliza VentanaLicencia para corregir claves
        return

    root.destroy() 
    app = AsisVozApp(utils.OPENROUTER_API_KEY, utils.DEEPGRAM_API_KEY)



    app.mainloop()



def crear_ventana_principal():
  

    root = ctk.CTk()
    root.title("AsisVoz")
    ancho_ventana, alto_ventana = 600, 400
    centrar_ventana(root, ancho_ventana, alto_ventana)

    # Crear menú
    menubar = tk.Menu(root)
    root.config(menu=menubar)


    ico_path = utils.ruta_absoluta("media/logo.ico")
    if os.path.exists(ico_path):
        try:
            root.iconbitmap(ico_path)
        except Exception:
            pass

    menu_opciones = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Opciones", menu=menu_opciones)
    menu_opciones.add_command(label="Registrar Licencia", command=lambda: mostrar_ventana_licencia(root))
    menu_opciones.add_command(label="Registrar Equipo", command=lambda: mostrar_ventana_registro_equipo(root))
    menu_opciones.add_separator()
    menu_opciones.add_command(label="Salir", command=root.quit)

    # Frame principal
    main_frame = ctk.CTkFrame(root)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)



      # Imagen
    try:
        ruta_imagen = os.path.join("media", "icono.png")
        image = Image.open(ruta_imagen).resize((110, 110))
        ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=(110, 110))
        label_img = ctk.CTkLabel(main_frame, image=ctk_img, text="")
        label_img.image = ctk_img
        label_img.pack(pady=(50, 15))
    except Exception as e:
        print(f"❌ Error al cargar imagen: {e}")
    

    # Botón principal
    btn_iniciar = ctk.CTkButton(
        main_frame,
        text="Iniciar Aplicación",
        font=ctk.CTkFont(size=18, weight="bold"),
        width=250,
        height=60,
        command=lambda: iniciar_asisvoz(root)
    )
    btn_iniciar.pack(pady=18)

    # Info
    info_label = ctk.CTkLabel(
        main_frame,
        text="Asegúrese de tener una licencia válida antes de iniciar la aplicación",
        font=ctk.CTkFont(size=10),
        text_color="black"
    )
    info_label.pack(pady=(10, 20))

     
    root.resizable(False, False)

    root.mainloop()

if __name__ == "__main__":


    utils.descifrar_y_extraer_claves()
    print("Clave Deepgram:", utils.DEEPGRAM_API_KEY)
    print("Clave OpenRouter:", utils.OPENROUTER_API_KEY)
    utils.reproducir_sonido("finalizado")
    crear_ventana_principal()
