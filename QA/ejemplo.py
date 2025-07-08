from DeepgramTranscriber import DeepgramTranscriber, FormateadorTranscripcion, GuardadorTranscripcion
from OpenRouterClient import OpenRouterClient

def usar_deepgram():
    print("=== TRANSCRIPCIÓN CON DEEPGRAM ===")
    
    API_KEY = "TU_API_KEY_DEEPGRAM"
    AUDIO_URL = "https://www.example.com/audio.mp3"  # Cambia esto

    try:
        transcriptor = DeepgramTranscriber(API_KEY)
        formateador = FormateadorTranscripcion()
        guardador = GuardadorTranscripcion()

        respuesta = transcriptor.transcribir_url(AUDIO_URL)
        texto = formateador.extraer_texto(respuesta)

        guardador.guardar_txt(texto)
        guardador.guardar_pdf(texto)
        print("✅ Transcripción guardada como transcripcion.txt y transcripcion.pdf\n")
    except Exception as e:
        print(f"❌ Error en Deepgram: {e}\n")


def usar_openrouter():
    print("=== CONSULTA A PDF CON OPENROUTER ===")
    
    API_KEY = "TU_API_KEY_OPENROUTER"
    PDF_PATH = "documento.pdf"  # Cambia esto
    PREGUNTA = "¿Cuál es el resumen del documento?"

    try:
        cliente = OpenRouterClient(API_KEY)
        respuesta, tiempo = cliente.preguntar_con_pdf(PDF_PATH, PREGUNTA)
        print("📄 Respuesta:")
        print(respuesta)
        print(f"\n⏱️ Tiempo de respuesta: {tiempo:.2f} segundos\n")
    except Exception as e:
        print(f"❌ Error en OpenRouter: {e}")


if __name__ == "__main__":
    usar_deepgram()
    usar_openrouter()
