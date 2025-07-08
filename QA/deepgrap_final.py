import os
import sys
import json
import mimetypes
import time
import tkinter as tk
from tkinter import filedialog

from deepgram import DeepgramClient, PrerecordedOptions
from fpdf import FPDF

# ----------------------------
# CONFIGURACIONES DE API
# ----------------------------
DEEPGRAM_API_KEY = "9e231f7aaa5b8724a3cd852ef37774878750c957"

# ----------------------------
# FUNCIONES AUXILIARES
# ----------------------------
def seleccionar_archivo_audio() -> str:
    """
    Abre un diálogo (tkinter) para que el usuario seleccione un archivo de audio.
    Devuelve la ruta completa, o None si cancela.
    """
    root = tk.Tk()
    root.withdraw()
    filetypes = [
        ("Archivos de audio", "*.wav *.mp3 *.m4a *.flac *.ogg"),
        ("Todos los archivos", "*.*"),
    ]
    ruta = filedialog.askopenfilename(
        title="Selecciona el archivo de audio",
        filetypes=filetypes
    )
    root.destroy()
    return ruta or None

def verificar_extension_audio(ruta_audio: str) -> None:
    """
    Muestra un aviso si la extensión de audio es poco común (opcional).
    """
    ext = os.path.splitext(ruta_audio)[1].lower()
    if ext not in [".wav", ".mp3", ".m4a", ".flac", ".ogg"]:
        print(f"⚠️  Atención: la extensión '{ext}' podría no ser totalmente compatible con Deepgram.")

def segundos_a_mmss(segundos: float) -> str:
    """
    Convierte segundos (float) a formato "MM:SS".
    """
    total = int(segundos)
    minutos = total // 60
    seg = total % 60
    return f"{minutos:02d}:{seg:02d}"

def transcribir_con_deepgram(ruta_audio: str) -> object:
    """
    Envía el archivo de audio a Deepgram de forma síncrona, solicitando diarization y smart_format.
    Devuelve el objeto de respuesta de Deepgram (que contiene canales, alternativas, etc.). 
    Lanza excepción si algo falla.
    """
    if not DEEPGRAM_API_KEY:
        raise RuntimeError("La clave API de Deepgram no está definida.")

    try:
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
    except Exception as e:
        raise RuntimeError(f"Error al inicializar DeepgramClient: {e}")

    try:
        with open(ruta_audio, "rb") as f:
            audio_bytes = f.read()
    except FileNotFoundError:
        raise RuntimeError(f"ERROR: No existe el archivo: {ruta_audio}")

    mime_type, _ = mimetypes.guess_type(ruta_audio)
    mimetype = mime_type or "application/octet-stream"

    source = {
        "buffer": audio_bytes,
        "mimetype": mimetype
    }

    opciones = PrerecordedOptions(
        model="whisper",
        language="es",
        punctuate=True,
        diarize=True,
        smart_format=True,
        paragraphs=True
    )

    try:
        respuesta = deepgram.listen.rest.v("1").transcribe_file(
            source=source,
            options=opciones,
            timeout=900
        )
    except Exception as e:
        raise RuntimeError(f"ERROR durante la petición a Deepgram:\n{e}")

    return respuesta

def extraer_transcripcion_con_diarization(respuesta) -> str:
    """
    A partir del objeto devuelto por Deepgram (con diarization y smart_format), arma un string formateado
    que incluya párrafos separados por orador y las marcas de tiempo (MM:SS) al inicio.
    Si existe `smart_format_results`, se usa para respetar párrafos; 
    si no, se agrupa palabra por palabra.
    """
    texto_formateado = ""
    try:
        # Accedemos al canal 0 y a la primera alternativa
        canal0 = respuesta.results.channels[0]
        alt = canal0.alternatives[0]

        # 1) Intentamos usar smart_format_results (puede incluir timestamps en cada párrafo)
        smart = getattr(alt, "smart_format_results", None)
        if smart and isinstance(smart, dict) and "paragraphs" in smart:
            # smart["paragraphs"] suele ser una lista de dicts: { "speaker": int, "text": str, "start": float, "end": float }
            for par in smart["paragraphs"]:
                speaker_id = par.get("speaker", 0)
                texto = par.get("text", "").strip()
                inicio = par.get("start", None)  # timestamp en segundos
                if texto:
                    ts = segundos_a_mmss(inicio) if inicio is not None else "00:00"
                    texto_formateado += f"[{ts}] Speaker {speaker_id}: {texto}\n\n"
            return texto_formateado.rstrip("\n")

        # 2) Si no hay smart_format_results, caemos en agrupamiento palabra a palabra
        palabras = getattr(alt, "words", None)
        if not palabras:
            # Si no hay words, tomamos únicamente el transcript plano
            texto_formateado = getattr(alt, "transcript", "").strip()
            return texto_formateado

        # Agrupamos por speaker, capturando el primer timestamp de cada bloque
        speaker_actual = palabras[0].speaker
        inicio_actual = palabras[0].start  # segundos
        linea = f"[{segundos_a_mmss(inicio_actual)}] Speaker {speaker_actual}: "
        for w in palabras:
            if w.speaker != speaker_actual:
                # Cerramos párrafo anterior y comenzamos uno nuevo
                texto_formateado += linea.strip() + "\n\n"
                speaker_actual = w.speaker
                inicio_actual = w.start
                linea = f"[{segundos_a_mmss(inicio_actual)}] Speaker {speaker_actual}: "
            linea += w.word + " "
        texto_formateado += linea.strip()
        return texto_formateado

    except Exception as e:
        # En caso de excepción, volcamos el JSON completo para diagnóstico
        try:
            detalle = json.dumps(respuesta, default=lambda o: o.__dict__, indent=2, ensure_ascii=False)
        except:
            detalle = str(respuesta)
        raise RuntimeError("ERROR al extraer diarization:\n" + detalle)

def guardar_texto_en_archivo(texto: str, ruta_salida: str) -> None:
    """
    Guarda el 'texto' completo en el archivo de texto indicado.
    """
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(texto)

def generar_pdf_desde_texto(texto: str, ruta_salida: str) -> None:
    """
    Genera un PDF sencillo que contiene todo el 'texto'
    y lo guarda en 'ruta_salida', usando fuente más pequeña (10 pt) y line height reducido (6 mm).
    """
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Elegimos Arial 10 pt
    pdf.set_font("Arial", size=10)

    # Interlineado de 6 mm (en multi_cell, el segundo parámetro es el alto de fila)
    pdf.multi_cell(0, 6, texto)

    pdf.output(ruta_salida)

# ----------------------------
# FLUJO PRINCIPAL EN CONSOLA
# ----------------------------
def main():
    print("\n=== Audio → Deepgram (diarization + smart_format + timestamps) ===\n")

    # 1) Abrir diálogo para seleccionar audio
    print("1) Selecciona el archivo de audio…")
    ruta_audio = seleccionar_archivo_audio()
    if not ruta_audio:
        print("No se seleccionó ningún archivo. Saliendo.")
        sys.exit(0)

    if not os.path.isfile(ruta_audio):
        print(f"ERROR: El archivo '{ruta_audio}' no existe. Saliendo.")
        sys.exit(1)

    verificar_extension_audio(ruta_audio)

    # 2) Transcribir con Deepgram (objeto completo)
    print("\n2) Enviando audio a Deepgram para transcripción…\n")
    t_inicio_trans = time.time()
    try:
        respuesta_deep = transcribir_con_deepgram(ruta_audio)
    except Exception as e:
        print(f"\n❌ Error durante la transcripción:\n{e}\n")
        sys.exit(1)
    t_fin_trans = time.time()
    duracion_trans = t_fin_trans - t_inicio_trans
    print(f"   ► Tiempo de transcripción Deepgram: {duracion_trans:.2f} segundos.\n")

    # 3) Extraer texto formateado con párrafos, speaker labels y timestamps
    print("--- Armando transcripción con diarization (inicio) ---\n")
    t_inicio_diar = time.time()
    try:
        transcripcion_txt = extraer_transcripcion_con_diarization(respuesta_deep)
    except Exception as e:
        print(f"\n❌ Error al procesar diarization:\n{e}\n")
        sys.exit(1)
    t_fin_diar = time.time()
    duracion_diar = t_fin_diar - t_inicio_diar
    print(transcripcion_txt)
    print("\n--- Armando transcripción con diarization (fin) ---\n")
    print(f"   ► Tiempo de procesamiento de diarización: {duracion_diar:.2f} segundos.\n")

    # 4) Guardar transcripción en .txt
    nombre_txt = "transcripcion.txt"
    print(f"3) Guardando transcripción de texto en '{nombre_txt}'…")
    t_inicio_guardado_txt = time.time()
    try:
        guardar_texto_en_archivo(transcripcion_txt, nombre_txt)
    except Exception as e:
        print(f"\n❌ Error guardando archivo de texto:\n{e}\n")
        sys.exit(1)
    t_fin_guardado_txt = time.time()
    duracion_guardado_txt = t_fin_guardado_txt - t_inicio_guardado_txt
    print(f"   ► Archivo de texto generado exitosamente en {duracion_guardado_txt:.2f} segundos.\n")

    # 5) Generar PDF a partir del mismo texto (con fuente pequeña y line height reducido)
    nombre_pdf = "transcripcion.pdf"
    print(f"4) Generando PDF en '{nombre_pdf}'…")
    t_inicio_pdf = time.time()
    try:
        generar_pdf_desde_texto(transcripcion_txt, nombre_pdf)
    except Exception as e:
        print(f"\n❌ Error generando PDF:\n{e}\n")
        sys.exit(1)
    t_fin_pdf = time.time()
    duracion_pdf = t_fin_pdf - t_inicio_pdf
    print(f"   ► PDF generado exitosamente en {duracion_pdf:.2f} segundos.\n")

    tiempo_total = time.time() - t_inicio_trans
    print(f"¡Proceso completado! Tiempo total desde la petición: {tiempo_total:.2f} segundos.")
    print("Revisa 'transcripcion.txt' y 'transcripcion.pdf'.")

if __name__ == "__main__":
    main()
