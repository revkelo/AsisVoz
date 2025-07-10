from tkinter import Tk, filedialog
from xd import DeepgramPDFTranscriber  # Asegúrate de que tu clase esté en ese archivo o cambia el import

def seleccionar_audio() -> str:
    root = Tk()
    root.withdraw()  # Oculta la ventana principal de Tkinter
    archivo = filedialog.askopenfilename(
        title="Selecciona un archivo de audio",
        filetypes=[("Archivos de audio", "*.mp3 *.wav *.m4a *.flac *.aac *.ogg")]
    )
    return archivo

if __name__ == "__main__":
    DEEPGRAM_API_KEY = "9e231f7aaa5b8724a3cd852ef37774878750c957"
    transcriptor = DeepgramPDFTranscriber(DEEPGRAM_API_KEY)

    print("[Main] Selecciona el archivo de audio:")
    ruta_audio = seleccionar_audio()

    if ruta_audio:
        transcriptor.transcribir_audio(ruta_audio)
    else:
        print("❌ No se seleccionó ningún archivo.")
