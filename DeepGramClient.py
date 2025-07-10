import os
import time
from deepgram import DeepgramClient, PrerecordedOptions
from fpdf import FPDF


class DeepgramPDFTranscriber:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key de Deepgram requerida.")
        print("[Inicializando] Cliente Deepgram...")
        self.client = DeepgramClient(api_key)

    def segundos_a_hhmmss(self, segundos: float) -> str:
        horas = int(segundos // 3600)
        minutos = int((segundos % 3600) // 60)
        segundos_restantes = int(segundos % 60)
        return f"[{horas:02d}:{minutos:02d}:{segundos_restantes:02d}]"

    def generar_pdf(self, nombre_salida: str, transcripciones: list[str]):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Transcripción de audio", ln=True, align="C")
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, f"Archivo: {nombre_salida}", ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("Arial", size=12)
        for linea in transcripciones:
            pdf.multi_cell(0, 10, linea)

        pdf.output(f"{nombre_salida}.pdf")
        print(f"\n✅ PDF guardado como '{nombre_salida}.pdf'")

    def transcribir_audio(self, ruta_audio: str):
        inicio = time.time()
        try:
            if not ruta_audio or not os.path.isfile(ruta_audio):
                raise FileNotFoundError("❌ Archivo no válido o no encontrado.")

            with open(ruta_audio, "rb") as f:
                audio_bytes = f.read()

            options = PrerecordedOptions(
                model="nova-2",
                language="es",
                smart_format=True,
                punctuate=True,
                paragraphs=True,
                diarize=True,
            )

            response = self.client.listen.prerecorded.v("1").transcribe_file(
                {"buffer": audio_bytes},
                options,
                timeout=1000
            )

            channel = response.results.channels[0]
            transcripciones = []

            for alt in channel.alternatives:
                if hasattr(alt, "paragraphs") and alt.paragraphs and hasattr(alt.paragraphs, "paragraphs"):
                    for paragraph in alt.paragraphs.paragraphs:
                        tiempo = self.segundos_a_hhmmss(paragraph.start)
                        speaker = f"Locutor {paragraph.speaker}"
                        texto = " ".join([s.text for s in paragraph.sentences])
                        linea = f"{tiempo} {speaker}: {texto.strip()}"
                        transcripciones.append(linea)
                elif alt.transcript and alt.transcript.strip():
                    # Fallback si hay texto sin párrafos
                    transcripciones.append(alt.transcript.strip())

            if not transcripciones:
                raise ValueError("⚠ No se detectó voz en el archivo. Verifica que contenga audio hablado.")

            self.generar_pdf("transcripcion", transcripciones)

            fin = time.time()
            print(f"\n⏱ Tiempo de ejecución: {fin - inicio:.2f} segundos")

        except Exception as e:
            print(f"❌ Exception: {e}")
            raise  # Opcional: relanza para que la GUI también lo muestre si lo capturas desde allá

