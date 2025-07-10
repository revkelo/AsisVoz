import os
import json
import time
import base64
import re
import requests


class OpenRouterClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Punto final del API de OpenRouter
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def preguntar_con_pdf(self, pdf_path: str, pregunta: str) -> tuple[str, float]:
        """
        Envía un PDF (codificado en base64) junto con una pregunta al endpoint de OpenRouter,
        usando el plugin "file-parser". Devuelve (texto_limpio, tiempo_en_segundos).
        """
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"Archivo no encontrado: {pdf_path}")

        # Leemos el PDF y lo codificamos en Base64
        with open(pdf_path, "rb") as f:
            pdf_base64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "model": "deepseek/deepseek-r1:free",
            #"model": "deepseek/deepseek-r1-0528-qwen3-8b",
            #"model": "qwen/qwen3-235b-a22b:free",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": pregunta},
                        {
                            "type": "file",
                            "file": {
                                "filename": os.path.basename(pdf_path),
                                "file_data": f"data:application/pdf;base64,{pdf_base64}"
                            }
                        }
                    ]
                }
            ],
            "plugins": [
                {
                    "id": "file-parser",
                    "pdf": {"engine": "pdf-text"}
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        inicio = time.time()
        respuesta = requests.post(self.endpoint, headers=headers, json=payload)
        duracion = time.time() - inicio

        if respuesta.status_code != 200:
            raise RuntimeError(f"OpenRouter error {respuesta.status_code}: {respuesta.text}")

        try:
            raw_text = respuesta.json()["choices"][0]["message"]["content"].strip()
            texto_limpio = self._limpiar_markdown(raw_text)
            return texto_limpio, duracion
        except (KeyError, IndexError, json.JSONDecodeError):
            raise RuntimeError("Formato de respuesta inesperado:\n" + respuesta.text)

    def preguntar_texto(self, prompt: str) -> tuple[str, float]:
        """
        Envía solo un mensaje de texto (sin archivos) al endpoint de OpenRouter.
        Devuelve (texto_limpio, tiempo_en_segundos).
        """
        payload = {
            "model": "deepseek/deepseek-r1:free",
            "messages": [
                {"role": "user", "content": prompt}
            ]
            # No incluimos plugins cuando solo es texto
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        inicio = time.time()
        respuesta = requests.post(self.endpoint, headers=headers, json=payload)
        duracion = time.time() - inicio

        if respuesta.status_code != 200:
            raise RuntimeError(f"OpenRouter error {respuesta.status_code}: {respuesta.text}")

        try:
            raw_text = respuesta.json()["choices"][0]["message"]["content"].strip()
            texto_limpio = self._limpiar_markdown(raw_text)
            return texto_limpio, duracion
        except (KeyError, IndexError, json.JSONDecodeError):
            raise RuntimeError("Formato de respuesta inesperado:\n" + respuesta.text)

    def _limpiar_markdown(self, texto: str) -> str:
        """
        Elimina tildes de negrita y cursiva propias de Markdown, dejando solo el texto limpio.
        """
        texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)  # Quita **negrita**
        texto = texto.replace("*", "")  # Elimina cualquier asterisco sobrante
        return texto



