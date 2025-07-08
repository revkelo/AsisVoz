import os
import json
import mimetypes
import time
from deepgram import DeepgramClient, PrerecordedOptions
from fpdf import FPDF

class DeepgramTranscriber:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key de Deepgram requerida.")
        print("[DeepgramTranscriber] Inicializando cliente Deepgram…")
        self.client = DeepgramClient(api_key)
        print("[DeepgramTranscriber] Cliente creado.")

    def transcribir(self, ruta_audio: str):
        print(f"[DeepgramTranscriber] Verificando existencia de '{ruta_audio}'…")
        if not os.path.isfile(ruta_audio):
            raise FileNotFoundError(f"Archivo no encontrado: {ruta_audio}")

        with open(ruta_audio, "rb") as f:
            audio_bytes = f.read()
        print(f"[DeepgramTranscriber] Archivo cargado ({len(audio_bytes)} bytes).")

        mime_type, _ = mimetypes.guess_type(ruta_audio)
        source = {
            "buffer": audio_bytes,
            "mimetype": mime_type or "application/octet-stream"
        }

        opciones = PrerecordedOptions(
            model="whisper",
            language="es",
            punctuate=True,
            diarize=True,
            smart_format=True,
            paragraphs=True
        )
        print("[DeepgramTranscriber] Llamando a Deepgram para transcribir… (timeout=900s)")

        try:
            respuesta = self.client.listen.rest.v("1").transcribe_file(
                source=source,
                options=opciones,
                timeout=900
            )
            print("[DeepgramTranscriber] Respuesta de Deepgram recibida.")
        except Exception as e:
            print(f"[DeepgramTranscriber] ERROR en transcribir(): {e}")
            raise

        return respuesta

    def extraer_transcripcion(self, respuesta):
        print("[DeepgramTranscriber] Extrayendo texto de la respuesta…")
        def segundos_a_mmss(segundos: float) -> str:
            minutos = int(segundos) // 60
            segundos = int(segundos) % 60
            return f"{minutos:02}:{segundos:02}"

        try:
            canal = respuesta.results.channels[0]
            alt = canal.alternatives[0]
            smart = getattr(alt, "smart_format_results", None)
            texto = ""

            if smart and "paragraphs" in smart:
                print("[DeepgramTranscriber] Usando 'smart_format_results' (paragraphs).")
                for par in smart["paragraphs"]:
                    ts = segundos_a_mmss(par.get("start", 0))
                    speaker = par.get("speaker", 0)
                    texto += f"[{ts}] Speaker {speaker}: {par['text']}\n\n"

            elif hasattr(alt, "words"):
                print("[DeepgramTranscriber] Usando información de 'words'.")
                palabras = alt.words
                if not palabras:
                    return alt.transcript.strip()

                speaker_actual = palabras[0].speaker
                inicio = palabras[0].start
                linea = f"[{segundos_a_mmss(inicio)}] Speaker {speaker_actual}: "

                for palabra in palabras:
                    if palabra.speaker != speaker_actual:
                        texto += linea.strip() + "\n\n"
                        speaker_actual = palabra.speaker
                        inicio = palabra.start
                        linea = f"[{segundos_a_mmss(inicio)}] Speaker {speaker_actual}: "
                    linea += palabra.word + " "
                texto += linea.strip()
            else:
                print("[DeepgramTranscriber] Usando 'transcript' sin palabras ni párrafos.")
                texto = alt.transcript.strip()

            print("[DeepgramTranscriber] Extracción de texto completada.")
            return texto

        except Exception as e:
            print(f"[DeepgramTranscriber] ERROR en extraer_transcripcion(): {e}")
            raise RuntimeError("Error al extraer la transcripción.") from e

    def guardar_txt(self, texto: str, nombre_archivo="transcripcion.txt"):
        print(f"[DeepgramTranscriber] Guardando texto en '{nombre_archivo}'…")
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(texto)
        print("[DeepgramTranscriber] Texto guardado (TXT).")

    def generar_pdf(self, texto: str, nombre_archivo="transcripcion.pdf"):
        print(f"[DeepgramTranscriber] Generando PDF en '{nombre_archivo}'…")
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, texto)
        pdf.output(nombre_archivo)
        print("[DeepgramTranscriber] PDF generado.")

    def obtener_ruta_pdf(self, nombre_archivo="transcripcion.pdf") -> str:
        abs_path = os.path.abspath(nombre_archivo)
        print(f"[DeepgramTranscriber] Ruta absoluta PDF: {abs_path}")
        return abs_path

    def procesar_audio(self, ruta_audio: str):
        print(f"[DeepgramTranscriber] procesar_audio() arrancó para '{ruta_audio}'")
        inicio = time.time()

        # 1) Transcribir
        respuesta = self.transcribir(ruta_audio)

        # 2) Extraer texto
        texto = self.extraer_transcripcion(respuesta)

        # 3) Guardar en .txt
        self.guardar_txt(texto)

        # 4) Generar PDF
        self.generar_pdf(texto)

        duracion = time.time() - inicio
        print(f"[DeepgramTranscriber] ✔ Transcripción completada en {duracion:.2f} s.")
        return texto



