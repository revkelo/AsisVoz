import os
import json
import time
import base64
import re
from tkinter import messagebox
import requests


class OpenRouterClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        
        # Punto final del API de OpenRouter
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        
        # Control de fallback para modelo alternativo
        self.modelo_principal = "deepseek/deepseek-r1-0528:free"
        self.modelo_fallback = "deepseek/deepseek-r1:free"
        self.usando_fallback = False
        self.contador_fallback = 0
        self.max_peticiones_fallback = 5

    def _obtener_modelo_actual(self):
        """Determina qué modelo usar basado en el estado del fallback"""
        if self.usando_fallback and self.contador_fallback < self.max_peticiones_fallback:
            return self.modelo_fallback
        else:
            # Si completamos las 5 peticiones del fallback, volvemos al principal
            if self.contador_fallback >= self.max_peticiones_fallback:
                self.usando_fallback = False
                self.contador_fallback = 0
            return self.modelo_principal

    def _manejar_error_429(self):
        """Activa el modo fallback cuando recibimos error 429"""
        if not self.usando_fallback:
            print(f"⚠️  Error 429 detectado. Cambiando a modelo fallback ({self.modelo_fallback}) por {self.max_peticiones_fallback} peticiones...")
            self.usando_fallback = True
            self.contador_fallback = 0
            return True
        else:
            # Ya estamos en fallback y sigue dando 429
            print("Manda un mensaje al soporte técnico.")
            messagebox.showerror("Alerta", "Manda un mensaje al soporte técnico.")
            return False

    def _incrementar_contador_fallback(self):
        """Incrementa el contador de peticiones en modo fallback"""
        if self.usando_fallback:
            self.contador_fallback += 1
            print(f"📊 Usando modelo fallback: {self.contador_fallback}/{self.max_peticiones_fallback}")
            
            if self.contador_fallback >= self.max_peticiones_fallback:
                print(f"✅ Completadas {self.max_peticiones_fallback} peticiones con modelo fallback. Volviendo al modelo principal ({self.modelo_principal})...")

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

        # Intento inicial
        return self._hacer_peticion_con_fallback(pdf_path, pregunta, pdf_base64)

    def _hacer_peticion_con_fallback(self, pdf_path: str, pregunta: str, pdf_base64: str) -> tuple[str, float]:
        """Hace la petición con manejo automático de fallback en caso de error 429"""
        max_intentos = 2  # Intento con modelo principal + intento con fallback
        
        for intento in range(max_intentos):
            modelo_actual = self._obtener_modelo_actual()
            
            payload = {
                "model": modelo_actual,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "responde en español " + pregunta},
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

            if respuesta.status_code == 429:
                # Si es el primer intento, activamos fallback
                if intento == 0 and self._manejar_error_429():
                    print("🔄 Reintentando con modelo fallback...")
                    continue
                else:
                    # Si ya estamos en fallback o es el segundo intento, lanzamos error
                    raise RuntimeError("Límite de solicitudes alcanzado en todos los modelos. Intente más tarde.")
            
            elif respuesta.status_code != 200:
                raise RuntimeError(f"OpenRouter error {respuesta.status_code}: {respuesta.text}")

            # Petición exitosa
            try:
                raw_text = respuesta.json()["choices"][0]["message"]["content"].strip()
                texto_limpio = self._limpiar_markdown(raw_text)
                
                # Incrementar contador si estamos usando fallback
                self._incrementar_contador_fallback()
                
                return texto_limpio, duracion
            except (KeyError, IndexError, json.JSONDecodeError):
                raise RuntimeError("Formato de respuesta inesperado:\n" + respuesta.text)

        # Si llegamos aquí, fallaron todos los intentos
        raise RuntimeError("Falló la petición con todos los modelos disponibles.")

    def preguntar_texto(self, prompt: str) -> tuple[str, float]:
        """
        Envía solo un mensaje de texto (sin archivos) al endpoint de OpenRouter.
        Devuelve (texto_limpio, tiempo_en_segundos).
        """
        max_intentos = 2  # Intento con modelo principal + intento con fallback
        
        for intento in range(max_intentos):
            modelo_actual = self._obtener_modelo_actual()
            
            payload = {
                "model": modelo_actual,
                "messages": [
                    {"role": "user", "content": "responde en español " + prompt}
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

            if respuesta.status_code == 429:
                # Si es el primer intento, activamos fallback
                if intento == 0 and self._manejar_error_429():
                    print("🔄 Reintentando con modelo fallback...")
                    continue
                else:
                    # Si ya estamos en fallback o es el segundo intento, lanzamos error
                    raise RuntimeError("Límite de solicitudes alcanzado en todos los modelos. Intente más tarde.")
            
            elif respuesta.status_code != 200:
                raise RuntimeError(f"OpenRouter error {respuesta.status_code}: {respuesta.text}")

            # Petición exitosa
            try:
                raw_text = respuesta.json()["choices"][0]["message"]["content"].strip()
                texto_limpio = self._limpiar_markdown(raw_text)
                
                # Incrementar contador si estamos usando fallback
                self._incrementar_contador_fallback()
                
                return texto_limpio, duracion
            except (KeyError, IndexError, json.JSONDecodeError):
                raise RuntimeError("Formato de respuesta inesperado:\n" + respuesta.text)

        # Si llegamos aquí, fallaron todos los intentos
        raise RuntimeError("Falló la petición con todos los modelos disponibles.")

    def _limpiar_markdown(self, texto: str) -> str:
        """
        Elimina tildes de negrita y cursiva propias de Markdown, dejando solo el texto limpio.
        """
        texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)  # Quita **negrita**
        texto = texto.replace("*", "")  # Elimina cualquier asterisco sobrante
        return texto

    def obtener_estado_fallback(self) -> dict:
        """Devuelve información sobre el estado actual del fallback"""
        return {
            "usando_fallback": self.usando_fallback,
            "contador": self.contador_fallback,
            "modelo_actual": self._obtener_modelo_actual(),
            "peticiones_restantes": self.max_peticiones_fallback - self.contador_fallback if self.usando_fallback else 0
        }

    def resetear_fallback(self):
        """Resetea manualmente el estado del fallback"""
        self.usando_fallback = False
        self.contador_fallback = 0
        print("🔄 Estado de fallback reseteado manualmente.")