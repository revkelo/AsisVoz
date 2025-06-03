import os
import sys
import json
import base64
import time
import re                # ← Agregamos re para procesar el texto
import tkinter as tk
from tkinter import filedialog

import requests

# ----------------------------
# CONFIGURACIONES DE API
# ----------------------------
OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ----------------------------
# FUNCIONES AUXILIARES
# ----------------------------

def seleccionar_archivo_pdf() -> str:
    """
    Abre un diálogo para que el usuario seleccione un archivo PDF.
    Devuelve la ruta completa, o None si cancela.
    """
    root = tk.Tk()
    root.withdraw()
    filetypes = [("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")]
    ruta = filedialog.askopenfilename(
        title="Selecciona el archivo PDF",
        filetypes=filetypes
    )
    root.destroy()
    return ruta or None

def encode_pdf_to_base64(pdf_path: str) -> str:
    """
    Codifica un PDF en Base64 para enviarlo a OpenRouter.
    """
    with open(pdf_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def limpiar_markdown(texto: str) -> str:
    """
    Elimina los asteriscos usados para negritas (o cualquier '*' suelto)
    para que el texto quede sin formato Markdown.
    """
    # 1) Primero eliminamos dobles asteriscos que rodean texto: **negrita** → negrita
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)

    # 2) Luego eliminamos asteriscos simples que puedan quedar: *cursiva* o marcadores sueltos
    texto = texto.replace("*", "")
    return texto

def preguntar_a_deepseek(pdf_base64: str, pregunta: str) -> tuple[str, float]:
    """
    Envía 'pregunta' y el PDF (en Base64) al modelo Deepseek vía OpenRouter.
    Devuelve una tupla (respuesta_limpia, tiempo_en_segundos).
    """
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": pregunta},
                {
                    "type": "file",
                    "file": {
                        "filename": "documento.pdf",
                        "file_data": f"data:application/pdf;base64,{pdf_base64}"
                    }
                }
            ]
        }
    ]
    plugins = [
        {
            "id": "file-parser",
            "pdf": {"engine": "pdf-text"}
        }
    ]
    payload = {
        "model": "deepseek/deepseek-r1:free",
        "messages": messages,
        "plugins": plugins
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    start_time = time.time()
    respuesta = requests.post(OPENROUTER_URL, headers=headers, json=payload)
    elapsed = time.time() - start_time

    if respuesta.status_code != 200:
        raise RuntimeError(f"Error OpenRouter (status {respuesta.status_code}): {respuesta.text}")

    data = respuesta.json()
    try:
        content_raw = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        detalle = json.dumps(data, indent=2, ensure_ascii=False)
        raise RuntimeError("Respuesta inesperada de Deepseek:\n" + detalle)

    # Limpiamos el texto para quitar los asteriscos de negrita
    content_limpio = limpiar_markdown(content_raw)
    return content_limpio, elapsed

# ----------------------------
# FLUJO PRINCIPAL EN CONSOLA
# ----------------------------
def main():
    print("\n=== Consulta a Deepseek sobre un PDF (medición de tiempo) ===\n")

    # 1) Seleccionar el PDF
    print("1) Selecciona el archivo PDF…")
    ruta_pdf = seleccionar_archivo_pdf()
    if not ruta_pdf:
        print("No se seleccionó ningún PDF. Saliendo.")
        sys.exit(0)
    if not os.path.isfile(ruta_pdf):
        print(f"ERROR: El archivo '{ruta_pdf}' no existe. Saliendo.")
        sys.exit(1)

    # 2) Codificar a Base64
    print("\n2) Codificando PDF a Base64…")
    try:
        pdf_base64 = encode_pdf_to_base64(ruta_pdf)
    except Exception as e:
        print(f"\n❌ Error al codificar PDF:\n{e}\n")
        sys.exit(1)
    print("   ► PDF codificado exitosamente.\n")

    # 3) Bucle de preguntas a Deepseek
    print("3) Ahora puedes hacer preguntas al contenido del PDF.")
    print("   Escribe 'salir' o 'exit' para terminar.\n")
    while True:
        pregunta = input("Pregunta: ").strip()
        if pregunta.lower() in {"salir", "exit"}:
            print("\n¡Hasta luego!")
            break
        if not pregunta:
            print("→ Debes escribir algo o 'salir'.")
            continue

        print("\n   ► Enviando consulta a Deepseek…\n")
        try:
            respuesta_limpia, tiempo = preguntar_a_deepseek(pdf_base64, pregunta)
        except Exception as e:
            print(f"\n❌ Error al consultar Deepseek:\n{e}\n")
            continue

        print("Respuesta:\n")
        print(respuesta_limpia)  # Aquí ya no habrá asteriscos para negrita
        print(f"\n→ Tiempo de respuesta: {tiempo:.2f} segundos")
        print("\n" + "-"*40 + "\n")

if __name__ == "__main__":
    main()
