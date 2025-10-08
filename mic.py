import customtkinter as ctk
import soundcard as sc
import soundfile as sf
import numpy as np
import threading
import os
import time
from datetime import datetime
import warnings
from tkinter import filedialog

# Suprimir warnings específicos de soundcard
warnings.filterwarnings("ignore", category=sc.SoundcardRuntimeWarning)

# --- Variables globales ---
fs = 44100
recording = False
mic_enabled = True    
sys_enabled = True
mic_device = None
sys_device = None
mic_data = []
sys_data = []
start_time = None
niveles_activos = {}
recording_threads = []
mic_volume = 0.3  # Volumen del micrófono (0.0 - 1.0)
sys_volume = 0.5  # Volumen del sistema (0.0 - 1.0)

# Crear carpeta si no existe
os.makedirs("grabaciones", exist_ok=True)

# --- Ventana ---
ctk.set_appearance_mode("light")
ventana = ctk.CTk()
ventana.title("AsisVoz")
# Centrar ventana en pantalla
ancho_ventana = 450
alto_ventana = 330
pantalla_ancho = ventana.winfo_screenwidth()
pantalla_alto = ventana.winfo_screenheight()
x = int((pantalla_ancho / 2) - (ancho_ventana / 2))
y = int((pantalla_alto / 2) - (alto_ventana / 2))
ventana.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")

ventana.resizable(False, False)

# --- Funciones de nivel en vivo ---
def actualizar_nivel(nombre, barra, device):
    def task():
        while niveles_activos.get(nombre, False):
            if device and niveles_activos.get(nombre, False):
                try:
                    if hasattr(device, 'isloopback') and device.isloopback:
                        mic = sc.get_microphone(id=device.id, include_loopback=True)
                    else:
                        mic = sc.get_microphone(id=device.id, include_loopback=False)
                    
                    with mic.recorder(samplerate=fs, channels=1) as rec:
                        while niveles_activos.get(nombre, False):
                            try:
                                audio = rec.record(numframes=1024)
                                if audio is not None and len(audio) > 0:
                                    if audio.ndim > 1:
                                        audio = np.mean(audio, axis=1)
                                    rms = np.sqrt(np.mean(audio**2))
                                    nivel = min(rms * 50, 1.0)
                                    ventana.after(0, lambda: barra.set(nivel))
                                else:
                                    ventana.after(0, lambda: barra.set(0))
                            except Exception as e:
                                print(f"Error en medición de nivel {nombre}: {e}")
                                ventana.after(0, lambda: barra.set(0))
                            time.sleep(0.05)
                except Exception as e:
                    print(f"Error inicializando nivel {nombre}: {e}")
                    ventana.after(0, lambda: barra.set(0))
            time.sleep(0.1)
    
    niveles_activos[nombre] = True
    threading.Thread(target=task, daemon=True).start()

def detener_nivel(nombre, barra):
    niveles_activos[nombre] = False
    barra.set(0)

# --- Función de grabación ---
def grabar_fuente(device, data_buffer, nombre):
    try:
        print(f"Iniciando grabación de {nombre}: {device.name}")
        
        if hasattr(device, 'isloopback') and device.isloopback:
            mic = sc.get_microphone(id=device.id, include_loopback=True)
        else:
            mic = sc.get_microphone(id=device.id, include_loopback=False)
        
        with mic.recorder(samplerate=fs, channels=1) as rec:
            while recording:
                try:
                    audio = rec.record(numframes=2048)
                    if audio is not None and len(audio) > 0:
                        if audio.ndim > 1:
                            audio = np.mean(audio, axis=1)
                        data_buffer.append(audio)
                except Exception as e:
                    print(f"Error durante grabación {nombre}: {e}")
                    break
                    
    except Exception as e:
        print(f"Error inicializando grabación {nombre}: {e}")

def toggle_grabacion():
    global recording, mic_data, sys_data, start_time, recording_threads
    
    if not recording:
        if not mic_enabled and not sys_enabled:
            return

        mic_data.clear()
        sys_data.clear()
        recording_threads.clear()
        
        recording = True
        start_time = time.time()
        btn_grabar.configure(text="⏹️ Detener", fg_color="red")
        
        # Desactivar switches, combos y sliders durante grabación
        switch_mic.configure(state="disabled")
        switch_sys.configure(state="disabled")
        combo_mic.configure(state="disabled")
        combo_sys.configure(state="disabled")
        slider_mic.configure(state="disabled")
        slider_sys.configure(state="disabled")
        
        actualizar_cronometro()

        if mic_enabled and mic_device:
            thread_mic = threading.Thread(target=grabar_fuente, args=(mic_device, mic_data, "Micrófono"), daemon=True)
            thread_mic.start()
            recording_threads.append(thread_mic)
            
        if sys_enabled and sys_device:
            thread_sys = threading.Thread(target=grabar_fuente, args=(sys_device, sys_data, "Sistema"), daemon=True)
            thread_sys.start()
            recording_threads.append(thread_sys)
            
    else:
        recording = False
        btn_grabar.configure(text="🎙️ Grabar", fg_color="#2fa572")
        
        # Reactivar switches, combos y sliders después de grabar
        switch_mic.configure(state="normal")
        switch_sys.configure(state="normal")
        combo_mic.configure(state="normal")
        combo_sys.configure(state="normal")
        slider_mic.configure(state="normal")
        slider_sys.configure(state="normal")
        
        time.sleep(0.1)
        threading.Thread(target=guardar_archivo_mixto, daemon=True).start()



# --- Guardar archivo mixto ---
def guardar_archivo_mixto():
    try:
        # Determinar la longitud máxima para sincronizar
        max_length = 0
        if mic_data and len(mic_data) > 0:
            mic_audio = np.concatenate(mic_data)
            max_length = max(max_length, len(mic_audio))
        else:
            mic_audio = np.array([])

        if sys_data and len(sys_data) > 0:
            sys_audio = np.concatenate(sys_data)
            max_length = max(max_length, len(sys_audio))
        else:
            sys_audio = np.array([])

        if max_length == 0:
            print("No se grabó ningún audio.")
            return

        # Ajustar longitudes
        if len(mic_audio) > 0 and len(mic_audio) < max_length:
            mic_audio = np.concatenate([mic_audio, np.zeros(max_length - len(mic_audio))])
        elif len(mic_audio) == 0:
            mic_audio = np.zeros(max_length)

        if len(sys_audio) > 0 and len(sys_audio) < max_length:
            sys_audio = np.concatenate([sys_audio, np.zeros(max_length - len(sys_audio))])
        elif len(sys_audio) == 0:
            sys_audio = np.zeros(max_length)

        # Mezclar
        audio_mixto = (mic_audio * mic_volume) + (sys_audio * sys_volume)

        # Normalizar
        if np.max(np.abs(audio_mixto)) > 0:
            audio_mixto = audio_mixto / np.max(np.abs(audio_mixto)) * 0.95

        # Diálogo para elegir nombre y carpeta
        default_name = datetime.now().strftime("grabacion_%Y%m%d_%H%M%S.wav")
        filepath = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("Archivo de audio WAV", "*.wav")],
            initialfile=default_name,
            title="Guardar grabación como..."
        )

        if filepath:  # Si el usuario no canceló
            sf.write(filepath, audio_mixto, fs)
            print(f"Grabación guardada en: {filepath}")
        else:
            print("Guardado cancelado por el usuario.")

    except Exception as e:
        print(f"Error guardando: {e}")

# --- Cronómetro ---
def actualizar_cronometro():
    def task():
        while recording:
            try:
                elapsed = int(time.time() - start_time)
                mins, secs = divmod(elapsed, 60)
                horas, mins = divmod(mins, 60)
                if horas > 0:
                    tiempo_str = f"{horas:02}:{mins:02}:{secs:02}"
                else:
                    tiempo_str = f"{mins:02}:{secs:02}"
                ventana.after(0, lambda: cronometro_label.configure(text=tiempo_str))
                time.sleep(1)
            except Exception as e:
                print(f"Error en cronómetro: {e}")
                break
    threading.Thread(target=task, daemon=True).start()

# --- Funciones de control ---
def toggle_mic():
    global mic_enabled
    mic_enabled = switch_mic.get()
    if mic_enabled and mic_device:
        actualizar_nivel("mic", barra_mic, mic_device)
    else:
        detener_nivel("mic", barra_mic)

def toggle_sys():
    global sys_enabled
    sys_enabled = switch_sys.get()
    if sys_enabled and sys_device:
        actualizar_nivel("sys", barra_sys, sys_device)
    else:
        detener_nivel("sys", barra_sys)

def seleccionar_mic(nombre):
    global mic_device
    detener_nivel("mic", barra_mic)
    mic_device = dispositivos_dict.get(nombre, None)
    if mic_enabled and mic_device:
        actualizar_nivel("mic", barra_mic, mic_device)

def seleccionar_sys(nombre):
    global sys_device
    detener_nivel("sys", barra_sys)
    sys_device = dispositivos_dict.get(nombre, None)
    if sys_enabled and sys_device:
        actualizar_nivel("sys", barra_sys, sys_device)

# --- Funciones de volumen ---
def cambiar_volumen_mic(valor):
    global mic_volume
    mic_volume = valor

def cambiar_volumen_sys(valor):
    global sys_volume
    sys_volume = valor

# --- Obtener dispositivos ---
try:
    dispositivos = sc.all_microphones(include_loopback=True)
    dispositivos_dict = {}
    dispositivos_mic = []
    dispositivos_sys = []
    
    for d in dispositivos:
        if hasattr(d, 'isloopback') and d.isloopback:
            nombre = d.name[:30] + "..." if len(d.name) > 30 else d.name
            dispositivos_dict[nombre] = d
            dispositivos_sys.append(nombre)
        else:
            nombre = d.name[:30] + "..." if len(d.name) > 30 else d.name
            dispositivos_dict[nombre] = d
            dispositivos_mic.append(nombre)
    
    print(f"Dispositivos: {len(dispositivos_mic)} mic, {len(dispositivos_sys)} sys")
    
except Exception as e:
    print(f"Error obteniendo dispositivos: {e}")
    dispositivos_mic = []
    dispositivos_sys = []
    dispositivos_dict = {}

# --- GUI Compacta ---
# Header
header_frame = ctk.CTkFrame(ventana, height=60)
header_frame.pack(fill="x", padx=10, pady=(10, 5))

cronometro_label = ctk.CTkLabel(header_frame, text="00:00", font=("Arial", 24, "bold"))
cronometro_label.pack(side="left", padx=10, pady=15)

btn_grabar = ctk.CTkButton(header_frame, text="🎙️ Grabar", fg_color="#2fa572", 
                          command=toggle_grabacion, width=120, height=40, 
                          font=("Arial", 14, "bold"))
btn_grabar.pack(side="right", padx=10, pady=10)

# Panel de fuentes
fuentes_frame = ctk.CTkFrame(ventana)
fuentes_frame.pack(fill="both", expand=True, padx=10, pady=5)

# Micrófono compacto
mic_frame = ctk.CTkFrame(fuentes_frame)
mic_frame.pack(fill="x", padx=10, pady=(10, 5))

mic_header = ctk.CTkFrame(mic_frame)
mic_header.pack(fill="x", padx=5, pady=5)

ctk.CTkLabel(mic_header, text="🎤", font=("Arial", 16)).pack(side="left", padx=(5, 10))
switch_mic = ctk.CTkSwitch(mic_header, text="Micrófono", command=toggle_mic, width=50)
switch_mic.pack(side="left")
switch_mic.select()


# Barra de nivel verde para micrófono
barra_mic = ctk.CTkProgressBar(mic_header, width=80, height=10, progress_color="#00ff00")
barra_mic.pack(side="right", padx=5)
barra_mic.set(0)

if dispositivos_mic:
    combo_mic = ctk.CTkComboBox(mic_frame, values=dispositivos_mic, command=seleccionar_mic, 
                               width=400, height=25, font=("Arial", 10))
    combo_mic.pack(padx=10, pady=(0, 5))
    combo_mic.set(dispositivos_mic[0])
    seleccionar_mic(dispositivos_mic[0])
    
    # Control de volumen para micrófono
    vol_frame_mic = ctk.CTkFrame(mic_frame)
    vol_frame_mic.pack(fill="x", padx=10, pady=(0, 10))
    
    ctk.CTkLabel(vol_frame_mic, text="Vol:", font=("Arial", 10)).pack(side="left", padx=(5, 5))
    slider_mic = ctk.CTkSlider(vol_frame_mic, from_=0, to=1, number_of_steps=100, 
                              command=cambiar_volumen_mic, width=250)
    slider_mic.pack(side="left", padx=5)
    slider_mic.set(mic_volume)
    
    vol_label_mic = ctk.CTkLabel(vol_frame_mic, text="30%", font=("Arial", 10), width=30)
    vol_label_mic.pack(side="left", padx=5)
    
    def actualizar_label_mic(valor):
        vol_label_mic.configure(text=f"{int(valor*100)}%")
        cambiar_volumen_mic(valor)
    slider_mic.configure(command=actualizar_label_mic)
    
else:
    ctk.CTkLabel(mic_frame, text="❌ Sin micrófonos", text_color="orange").pack(pady=5)

# Sistema compacto
sys_frame = ctk.CTkFrame(fuentes_frame)
sys_frame.pack(fill="x", padx=10, pady=5)

sys_header = ctk.CTkFrame(sys_frame)
sys_header.pack(fill="x", padx=5, pady=5)

ctk.CTkLabel(sys_header, text="🔊", font=("Arial", 16)).pack(side="left", padx=(5, 10))
switch_sys = ctk.CTkSwitch(sys_header, text="Sistema", command=toggle_sys, width=50)
switch_sys.pack(side="left")
switch_sys.select()
# Barra de nivel verde para sistema
barra_sys = ctk.CTkProgressBar(sys_header, width=80, height=10, progress_color="#00ff00")
barra_sys.pack(side="right", padx=5)
barra_sys.set(0)

if dispositivos_sys:
    combo_sys = ctk.CTkComboBox(sys_frame, values=dispositivos_sys, command=seleccionar_sys, 
                               width=400, height=25, font=("Arial", 10))
    combo_sys.pack(padx=10, pady=(0, 5))
    combo_sys.set(dispositivos_sys[0])
    seleccionar_sys(dispositivos_sys[0])
    
    # Control de volumen para sistema
    vol_frame_sys = ctk.CTkFrame(sys_frame)
    vol_frame_sys.pack(fill="x", padx=10, pady=(0, 10))
    
    ctk.CTkLabel(vol_frame_sys, text="Vol:", font=("Arial", 10)).pack(side="left", padx=(5, 5))
    slider_sys = ctk.CTkSlider(vol_frame_sys, from_=0, to=1, number_of_steps=100, 
                              command=cambiar_volumen_sys, width=250)
    slider_sys.pack(side="left", padx=5)
    slider_sys.set(sys_volume)
    
    vol_label_sys = ctk.CTkLabel(vol_frame_sys, text="50%", font=("Arial", 10), width=30)
    vol_label_sys.pack(side="left", padx=5)
    
    def actualizar_label_sys(valor):
        vol_label_sys.configure(text=f"{int(valor*100)}%")
        cambiar_volumen_sys(valor)
    slider_sys.configure(command=actualizar_label_sys)
    
else:
    ctk.CTkLabel(sys_frame, text="❌ Sin audio sistema", text_color="orange").pack(pady=5)

# --- Función de limpieza ---
def on_closing():
    global recording, niveles_activos
    recording = False
    niveles_activos.clear()
    ventana.destroy()

ventana.protocol("WM_DELETE_WINDOW", on_closing)
ventana.mainloop()