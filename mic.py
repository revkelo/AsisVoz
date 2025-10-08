#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import customtkinter as ctk
import soundcard as sc
import soundfile as sf
import numpy as np
import threading
import os
import sys
import subprocess
import time
from datetime import datetime
import warnings
import tkinter as tk
from tkinter import filedialog, messagebox

# ================== Configuración general ==================
warnings.filterwarnings("ignore", category=sc.SoundcardRuntimeWarning)

# FS del sistema (mix format) con fallback seguro
try:
    FS = int(sc.default_samplerate())
except Exception:
    FS = 48000  # fallback razonable

BLOCK_LVL = 1024   # frames para medidor (coherente con blocksize)
BLOCK_REC = 2048   # frames para grabación (coherente con blocksize)

# Rango del medidor en dBFS (floor -> 0 dBFS)
METER_MIN_DB = -60.0
METER_MAX_DB = 0.0

# ================== Estado global (con locks) ==================
recording = False
mic_enabled = True
sys_enabled = True

mic_device = None
sys_device = None

mic_data = []
sys_data = []
buf_lock = threading.Lock()

# Control robusto de medidores (hilo, stop y generación anti-actualizaciones tardías)
meter_threads = {"mic": None, "sys": None}
meter_stops   = {"mic": threading.Event(), "sys": threading.Event()}
meter_gen     = {"mic": 0, "sys": 0}

start_time =  None
recording_threads = []

# Volúmenes: slider 0..1.5 (hasta 150 %)
SLIDER_MAX = 1.5
mic_volume = 1.00
sys_volume = 1.00

# Historial (hasta 50 en la sesión)
HISTORY_LIMIT = 50
recording_history: list[str] = []

# ================== Ventana ==================
ctk.set_appearance_mode("light")
ventana = ctk.CTk()
ventana.title("AsisVoz")

# Centrar ventana
ancho_ventana, alto_ventana = 620, 420
pantalla_ancho = ventana.winfo_screenwidth()
pantalla_alto = ventana.winfo_screenheight()
x = int((pantalla_ancho - ancho_ventana) / 2)
y = int((pantalla_alto - alto_ventana) / 2)
ventana.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")
ventana.resizable(False, False)

# ================== Menú (Historial) ==================
menubar = tk.Menu(ventana)
menu_hist = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Historial", menu=menu_hist)
ventana.config(menu=menubar)

def _open_path(p: str):
    try:
        if os.name == "nt":
            os.startfile(p)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", p])
        else:
            subprocess.Popen(["xdg-open", p])
    except Exception as e:
        messagebox.showerror("AsisVoz", f"No se pudo abrir:\n{p}\n\n{e}")

def _history_add(path: str):
    path = os.path.abspath(path)
    if path in recording_history:
        recording_history.remove(path)
    recording_history.insert(0, path)
    if len(recording_history) > HISTORY_LIMIT:
        del recording_history[HISTORY_LIMIT:]
    _history_rebuild_menu()

def _history_rebuild_menu():
    menu_hist.delete(0, "end")
    if not recording_history:
        menu_hist.add_command(label="(vacío)", state="disabled")
        return
    for i, p in enumerate(recording_history):
        base = os.path.basename(p)
        label = f"{i+1:02d}. {base}"
        menu_hist.add_command(label=label, command=lambda pp=p: _open_path(pp))

# ================== Utilidades de audio ==================
def _open_recorder_for_device(device, fs=FS, ch=1, blocksize=None):
    """Abrir recorder en modo compartido, con blocksize explícito."""
    if device is None:
        return None
    include_lb = getattr(device, "isloopback", False)
    mic = sc.get_microphone(id=device.id, include_loopback=include_lb)
    # exclusive=False por defecto en soundcard; pass blocksize coherente
    return mic.recorder(samplerate=fs, channels=ch, blocksize=blocksize or 0)

def _ensure_mono(x: np.ndarray) -> np.ndarray:
    if x is None:
        return np.zeros(0, dtype=np.float32)
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 2:
        x = np.mean(x, axis=1)
    return x.astype(np.float32, copy=False)

def _safe_concat(chunks):
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    try:
        return np.concatenate(chunks).astype(np.float32, copy=False)
    except Exception:
        clean = []
        for c in chunks:
            cc = _ensure_mono(c)
            if cc.size:
                clean.append(cc)
        if not clean:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(clean).astype(np.float32, copy=False)

def _dbug(msg: str):
    print(f"[AsisVoz] {msg}")

# === Conversiones dB/lineal ===
def db_to_lin(db: float) -> float:
    return 10.0 ** (float(db) / 20.0)

def gain_to_db(g: float) -> float:
    if g <= 0.0:
        return float("-inf")
    return 20.0 * np.log10(float(g))

# === Volumen perceptual (slider 0..1.5) ===
# - 0..1.0  -> -60..0 dB
# - 1.0..1.5 -> 0..+3.522 dB (≈ 20*log10(1.5))
MAX_BOOST_DB = 20.0 * np.log10(SLIDER_MAX)  # depende del tope (150% => ~3.522 dB)

def slider_to_gain(v: float) -> float:
    v = float(max(0.0, min(SLIDER_MAX, v)))  # clamp 0..1.5
    if v <= 0.0:
        return 0.0
    if v <= 1.0:
        MIN_DB = -60.0
        db = MIN_DB + (0.0 - MIN_DB) * v
    else:
        frac = (v - 1.0) / (SLIDER_MAX - 1.0)  # 0..1
        db = frac * MAX_BOOST_DB
    return db_to_lin(db)

def level_to_progress(dbfs: float) -> float:
    if not np.isfinite(dbfs):
        return 0.0
    if dbfs <= METER_MIN_DB:
        return 0.0
    if dbfs >= METER_MAX_DB:
        return 1.0
    return (dbfs - METER_MIN_DB) / (METER_MAX_DB - METER_MIN_DB)

# ================== Medidores en vivo (con gen anti-UI tardía) ==================
def start_meter(name: str, bar, device, get_slider_gain):
    # detener hilo previo
    old_stop = meter_stops[name]
    old_stop.set()
    old_thread = meter_threads[name]
    if old_thread and old_thread.is_alive():
        try:
            old_thread.join(timeout=0.5)
        except Exception:
            pass

    # nueva generación y Event
    meter_gen[name] += 1
    gen_local = meter_gen[name]
    meter_stops[name] = threading.Event()

    bar.set(0)
    if device is None:
        return

    def _run():
        alpha = 0.35
        ema = 0.0
        stop_evt = meter_stops[name]

        def safe_ui_set(v):
            if gen_local == meter_gen[name]:
                ventana.after(0, lambda gl=gen_local, vv=max(0.0, min(1.0, v)): (
                    bar.set(vv) if gl == meter_gen[name] else None
                ))

        while not stop_evt.is_set():
            rec = None
            try:
                # abrir con blocksize = BLOCK_LVL y samplerate = FS
                rec = _open_recorder_for_device(device, fs=FS, ch=1, blocksize=BLOCK_LVL)
                if rec is None:
                    raise RuntimeError("No se pudo abrir recorder")
                with rec:
                    while not stop_evt.is_set():
                        audio = rec.record(numframes=BLOCK_LVL)  # coincide con blocksize
                        x = _ensure_mono(audio)
                        if x.size:
                            y = x * get_slider_gain()
                            rms = float(np.sqrt(np.mean(y * y))) if y.size else 0.0
                            dbfs = float("-inf") if rms <= 0.0 else 20.0 * np.log10(rms)
                            ema = alpha * level_to_progress(dbfs) + (1.0 - alpha) * ema
                            safe_ui_set(ema)
                        else:
                            safe_ui_set(0)
            except Exception as e:
                # Reacción específica a 0x88890007 (OUT_OF_ORDER): reapertura del stream
                if "0x88890007" in str(e) or "AUDCLNT_E_OUT_OF_ORDER" in str(e):
                    _dbug(f"Medidor {name}: OUT_OF_ORDER -> reabriendo…")
                    safe_ui_set(0)
                    time.sleep(0.05)
                    continue  # reintentar: nueva apertura en la siguiente iteración
                else:
                    _dbug(f"Error medidor {name}: {e}")
                    safe_ui_set(0)
                    time.sleep(0.10)
            finally:
                try:
                    if rec is not None:
                        # el contexto with asegura cierre; no se requiere más
                        pass
                except Exception:
                    pass

        safe_ui_set(0)

    th = threading.Thread(target=_run, daemon=True)
    meter_threads[name] = th
    th.start()

def stop_meter(name: str, bar):
    meter_gen[name] += 1
    meter_stops[name].set()
    th = meter_threads[name]
    if th and th.is_alive():
        try:
            th.join(timeout=0.5)
        except Exception:
            pass
    bar.set(0)

# ================== Grabación ==================
def grabar_fuente(device, data_buffer: list, etiqueta: str):
    if device is None:
        _dbug(f"Grabación '{etiqueta}' sin dispositivo: se omite.")
        return
    try:
        rec = _open_recorder_for_device(device, fs=FS, ch=1, blocksize=BLOCK_REC)
        if rec is None:
            _dbug(f"No se abrió recorder para '{etiqueta}'.")
            return

        _dbug(f"Iniciando grabación de {etiqueta}: {device.name}")
        with rec:
            while recording:
                try:
                    audio = rec.record(numframes=BLOCK_REC)  # = blocksize
                    x = _ensure_mono(audio)
                    if x.size:
                        with buf_lock:
                            data_buffer.append(x)
                except Exception as e:
                    if "0x88890007" in str(e) or "AUDCLNT_E_OUT_OF_ORDER" in str(e):
                        _dbug(f"{etiqueta}: OUT_OF_ORDER -> reabriendo…")
                        break  # salir para permitir reapertura si fuera necesario
                    _dbug(f"Error durante grabación {etiqueta}: {e}")
                    break
    except Exception as e:
        _dbug(f"Error inicializando grabación {etiqueta}: {e}")

def actualizar_cronometro():
    def _run():
        while recording:
            try:
                elapsed = max(0, int(time.time() - (start_time or time.time())))
                mins, secs = divmod(elapsed, 60)
                horas, mins = divmod(mins, 60)
                tiempo_str = f"{horas:02}:{mins:02}:{secs:02}" if horas else f"{mins:02}:{secs:02}"
                ventana.after(0, lambda s=tiempo_str: cronometro_label.configure(text=s))
                time.sleep(1.0)
            except Exception as e:
                _dbug(f"Error en cronómetro: {e}")
                break
    threading.Thread(target=_run, daemon=True).start()

def toggle_grabacion():
    global recording, start_time, recording_threads
    if not recording:
        if not mic_enabled and not sys_enabled:
            messagebox.showinfo("AsisVoz", "Activa al menos una fuente para grabar.")
            return

        with buf_lock:
            mic_data.clear()
            sys_data.clear()
        recording_threads.clear()

        recording = True
        start_time = time.time()
        btn_grabar.configure(text="⛔ Detener", fg_color="#d93025")
        switch_mic.configure(state="disabled")
        switch_sys.configure(state="disabled")
        combo_mic.configure(state="disabled")
        combo_sys.configure(state="disabled")
        slider_mic.configure(state="disabled")
        slider_sys.configure(state="disabled")

        actualizar_cronometro()

        if mic_enabled and mic_device:
            t1 = threading.Thread(target=grabar_fuente, args=(mic_device, mic_data, "Micrófono"), daemon=True)
            t1.start()
            recording_threads.append(t1)

        if sys_enabled and sys_device:
            t2 = threading.Thread(target=grabar_fuente, args=(sys_device, sys_data, "Sistema"), daemon=True)
            t2.start()
            recording_threads.append(t2)
    else:
        recording = False
        btn_grabar.configure(text="🎙️ Grabar", fg_color="#2fa572")
        switch_mic.configure(state="normal")
        switch_sys.configure(state="normal")
        combo_mic.configure(state="normal")
        combo_sys.configure(state="normal")
        slider_mic.configure(state="normal")
        slider_sys.configure(state="normal")
        threading.Thread(target=guardar_archivo_mixto, daemon=True).start()

def guardar_archivo_mixto():
    try:
        with buf_lock:
            mic_audio = _safe_concat(mic_data) if mic_data else np.zeros(0, dtype=np.float32)
            sys_audio = _safe_concat(sys_data) if sys_data else np.zeros(0, dtype=np.float32)

        max_len = max(mic_audio.size, sys_audio.size)
        if max_len == 0:
            _dbug("No se capturó audio (buffers vacíos).")
            return

        if mic_audio.size < max_len:
            mic_audio = np.pad(mic_audio, (0, max_len - mic_audio.size))
        if sys_audio.size < max_len:
            sys_audio = np.pad(sys_audio, (0, max_len - sys_audio.size))

        # Ganancia del slider (0..150 %)
        g_mic = slider_to_gain(mic_volume)
        g_sys = slider_to_gain(sys_volume)

        mix = mic_audio * g_mic + sys_audio * g_sys

        # Limpiar NaN/Inf
        mix = np.nan_to_num(mix, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32, copy=False)

        # Anti-clipping
        peak = float(np.max(np.abs(mix))) if mix.size else 0.0
        if peak > 1.0:
            mix = (mix / peak) * 0.99

        # Diálogo de guardado (usuario elige ubicación)
        default_name = f"grabacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("Archivo de audio WAV", "*.wav")],
            initialfile=default_name,
            title="Guardar grabación como…",
        )

        if not filepath:
            _dbug("Guardado cancelado por el usuario.")
            return

        sf.write(filepath, mix, FS)
        _dbug(f"Grabación guardada en: {filepath}")

        # Añadir al historial del menú (sesión)
        _history_add(filepath)

    except Exception as e:
        _dbug(f"Error guardando mezcla: {e}")
        messagebox.showerror("AsisVoz", f"Ocurrió un error guardando el archivo:\n{e}")

# ================== Descubrimiento de dispositivos ==================
def _nombre_unico(d):
    base = d.name if d and d.name else "Dispositivo"
    base = base.strip()
    short_id = (str(d.id) or "")[-6:]
    nombre = base if len(base) <= 40 else (base[:37] + "…")
    return f"{nombre} : {short_id}" if short_id else nombre

try:
    dispositivos = sc.all_microphones(include_loopback=True)
except Exception as e:
    _dbug(f"Error listando dispositivos: {e}")
    dispositivos = []

dispositivos_dict = {}
dispositivos_mic = []
dispositivos_sys = []

for d in dispositivos:
    nombre = _nombre_unico(d)
    dispositivos_dict[nombre] = d
    if getattr(d, "isloopback", False):
        dispositivos_sys.append(nombre)
    else:
        dispositivos_mic.append(nombre)

_dbug(f"Dispositivos detectados: {len(dispositivos_mic)} mic, {len(dispositivos_sys)} sys")

# ================== Callbacks de UI (volumen y toggles) ==================
def _format_db(db: float) -> str:
    return "−∞ dB" if not np.isfinite(db) else f"{db:.2f} dB"

def _format_pct(v: float) -> str:
    return f"{int(round(100 * v))}%"

def cambiar_volumen_mic(valor):
    global mic_volume
    mic_volume = float(valor)
    g = slider_to_gain(mic_volume)
    db = gain_to_db(g)
    vol_label_mic.configure(text=f"{_format_pct(mic_volume)}  ({_format_db(db)})")

def cambiar_volumen_sys(valor):
    global sys_volume
    sys_volume = float(valor)
    g = slider_to_gain(sys_volume)
    db = gain_to_db(g)
    vol_label_sys.configure(text=f"{_format_pct(sys_volume)}  ({_format_db(db)})")

def toggle_mic():
    global mic_enabled
    mic_enabled = switch_mic.get()
    if mic_enabled and mic_device:
        start_meter("mic", barra_mic, mic_device, lambda: slider_to_gain(mic_volume))
    else:
        stop_meter("mic", barra_mic)

def toggle_sys():
    global sys_enabled
    sys_enabled = switch_sys.get()
    if sys_enabled and sys_device:
        start_meter("sys", barra_sys, sys_device, lambda: slider_to_gain(sys_volume))
    else:
        stop_meter("sys", barra_sys)

def seleccionar_mic(nombre):
    global mic_device
    new_dev = dispositivos_dict.get(nombre)
    if new_dev is mic_device:
        return
    mic_device = new_dev
    if mic_enabled:
        start_meter("mic", barra_mic, mic_device, lambda: slider_to_gain(mic_volume))
    else:
        stop_meter("mic", barra_mic)

def seleccionar_sys(nombre):
    global sys_device
    new_dev = dispositivos_dict.get(nombre)
    if new_dev is sys_device:
        return
    sys_device = new_dev
    if sys_enabled:
        start_meter("sys", barra_sys, sys_device, lambda: slider_to_gain(sys_volume))
    else:
        stop_meter("sys", barra_sys)

# ================== UI ==================
# Header
header_frame = ctk.CTkFrame(ventana, height=60)
header_frame.pack(fill="x", padx=10, pady=(10, 5))

cronometro_label = ctk.CTkLabel(header_frame, text="00:00", font=("Arial", 24, "bold"))
cronometro_label.pack(side="left", padx=10, pady=15)

btn_grabar = ctk.CTkButton(
    header_frame,
    text="🎙️ Grabar",
    fg_color="#2fa572",
    command=toggle_grabacion,
    width=160,
    height=42,
    font=("Arial", 14, "bold"),
)
btn_grabar.pack(side="right", padx=10, pady=10)

# Panel principal
fuentes_frame = ctk.CTkFrame(ventana)
fuentes_frame.pack(fill="both", expand=True, padx=10, pady=5)

# ---- Micrófono ----
mic_frame = ctk.CTkFrame(fuentes_frame)
mic_frame.pack(fill="x", padx=10, pady=(10, 6))

mic_header = ctk.CTkFrame(mic_frame)
mic_header.pack(fill="x", padx=8, pady=6)

ctk.CTkLabel(mic_header, text="🎤", font=("Arial", 16)).pack(side="left", padx=(5, 10))
switch_mic = ctk.CTkSwitch(mic_header, text="Micrófono", command=toggle_mic, width=50)
switch_mic.pack(side="left")
switch_mic.select()

barra_mic = ctk.CTkProgressBar(mic_header, width=160, height=12, progress_color="#00ff00")
barra_mic.pack(side="right", padx=5)
barra_mic.set(0)

if dispositivos_mic:
    combo_mic = ctk.CTkComboBox(mic_frame, values=dispositivos_mic, command=seleccionar_mic,
                                width=560, height=28, font=("Arial", 10))
    combo_mic.pack(padx=10, pady=(0, 6))
    combo_mic.set(dispositivos_mic[0])
    seleccionar_mic(dispositivos_mic[0])

    vol_frame_mic = ctk.CTkFrame(mic_frame)
    vol_frame_mic.pack(fill="x", padx=10, pady=(0, 10))
    ctk.CTkLabel(vol_frame_mic, text="Vol:", font=("Arial", 10)).pack(side="left", padx=(5, 5))
    slider_mic = ctk.CTkSlider(
        vol_frame_mic, from_=0, to=SLIDER_MAX,
        number_of_steps=int(SLIDER_MAX*100),
        command=cambiar_volumen_mic, width=360
    )
    slider_mic.pack(side="left", padx=5)
    vol_label_mic = ctk.CTkLabel(vol_frame_mic, text="", font=("Arial", 10), width=180, anchor="w")
    vol_label_mic.pack(side="left", padx=6)
    slider_mic.set(mic_volume)
    cambiar_volumen_mic(mic_volume)
else:
    ctk.CTkLabel(mic_frame, text="❌ Sin micrófonos", text_color="orange").pack(pady=6)

# ---- Sistema (loopback) ----
sys_frame = ctk.CTkFrame(fuentes_frame)
sys_frame.pack(fill="x", padx=10, pady=6)

sys_header = ctk.CTkFrame(sys_frame)
sys_header.pack(fill="x", padx=8, pady=6)

ctk.CTkLabel(sys_header, text="🔊", font=("Arial", 16)).pack(side="left", padx=(5, 10))
switch_sys = ctk.CTkSwitch(sys_header, text="Sistema", command=toggle_sys, width=50)
switch_sys.pack(side="left")
switch_sys.select()

barra_sys = ctk.CTkProgressBar(sys_header, width=160, height=12, progress_color="#00ff00")
barra_sys.pack(side="right", padx=5)
barra_sys.set(0)

if dispositivos_sys:
    combo_sys = ctk.CTkComboBox(sys_frame, values=dispositivos_sys, command=seleccionar_sys,
                                 width=560, height=28, font=("Arial", 10))
    combo_sys.pack(padx=10, pady=(0, 6))
    combo_sys.set(dispositivos_sys[0])
    seleccionar_sys(dispositivos_sys[0])

    vol_frame_sys = ctk.CTkFrame(sys_frame)
    vol_frame_sys.pack(fill="x", padx=10, pady=(0, 10))
    ctk.CTkLabel(vol_frame_sys, text="Vol:", font=("Arial", 10)).pack(side="left", padx=(5, 5))
    slider_sys = ctk.CTkSlider(
        vol_frame_sys, from_=0, to=SLIDER_MAX,
        number_of_steps=int(SLIDER_MAX*100),
        command=cambiar_volumen_sys, width=360
    )
    slider_sys.pack(side="left", padx=5)
    vol_label_sys = ctk.CTkLabel(vol_frame_sys, text="", font=("Arial", 10), width=180, anchor="w")
    vol_label_sys.pack(side="left", padx=6)
    slider_sys.set(sys_volume)
    cambiar_volumen_sys(sys_volume)
else:
    ctk.CTkLabel(sys_frame, text="❌ Sin dispositivos de sistema (loopback)", text_color="orange").pack(pady=6)

# ================== Cierre y atajos ==================
def on_closing():
    global recording
    recording = False
    for name, bar in (("mic", barra_mic), ("sys", barra_sys)):
        stop_meter(name, bar)
    ventana.destroy()

def _key_space(evt):
    toggle_grabacion()

ventana.bind("<space>", _key_space)  # Espacio = iniciar/detener
ventana.protocol("WM_DELETE_WINDOW", on_closing)

# Arrancar medidores iniciales si hay dispositivos
if mic_device and mic_enabled:
    start_meter("mic", barra_mic, mic_device, lambda: slider_to_gain(mic_volume))
if sys_device and sys_enabled:
    start_meter("sys", barra_sys, sys_device, lambda: slider_to_gain(sys_volume))

ventana.mainloop()
