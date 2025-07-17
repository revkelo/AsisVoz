import tkinter as tk
from tkinter import messagebox
from VentanaPrincipal import AsisVozApp

class VentanaPrincipal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inicio - AsisVoz")
        self.geometry("400x250")
        self.resizable(False, False)

        # ─── Menú superior ─────────────────────────────────────
        menubar = tk.Menu(self)

        menu_opciones = tk.Menu(menubar, tearoff=0)
        menu_opciones.add_command(label="Registrar Licencia", command=self.registrar_licencia)
        menu_opciones.add_command(label="Configurar Keys", command=self.configurar_keys)
        menubar.add_cascade(label="Opciones", menu=menu_opciones)

        self.config(menu=menubar)

        # ─── Título y botón ────────────────────────────────────
        tk.Label(self, text="Bienvenido a AsisVoz", font=("Arial", 16, "bold")).pack(pady=30)

        btn_iniciar = tk.Button(self, text="Iniciar", font=("Arial", 12), width=15, command=self.abrir_asisvoz)
        btn_iniciar.pack(pady=10)

    def registrar_licencia(self):
        messagebox.showinfo("Licencia", "Aquí se registrará la licencia...")

    def configurar_keys(self):
        messagebox.showinfo("Configuración", "Aquí se configurarán las API keys...")

    def abrir_asisvoz(self):
        self.withdraw()  # Ocultar esta ventana
        app = AsisVozApp()
        app.mainloop()
        self.deiconify()  # Mostrarla nuevamente cuando se cierre la otra

if __name__ == "__main__":
    app = VentanaPrincipal()
    app.mainloop()
