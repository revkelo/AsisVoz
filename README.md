# AsisVoz

AsisVoz es una aplicación de escritorio desarrollada en Python que integra funcionalidades de reconocimiento de voz y síntesis de texto a voz. Utiliza la API de Deepgram para transcripción de audio y OpenRouter para la síntesis de voz.

## Características

- Reconocimiento de voz en tiempo real.
- Conversión de texto a voz utilizando OpenRouter.
- Interfaz gráfica de usuario (GUI) desarrollada con Tkinter.
- Configuración de claves API para Deepgram y OpenRouter.

## Requisitos

- Python 3.8 o superior.
- Bibliotecas de Python:
  - `tkinter`
  - `deepgram`
  - `openrouter`
  - Otras dependencias especificadas en el archivo `requirements.txt`.

## Instalación

1. Clona el repositorio:

   ```bash
   git clone https://github.com/revkelo/AsisVoz.git
   cd AsisVoz
   ```

2. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Configura tus claves API:
   - Obtén una clave API de Deepgram y otra de OpenRouter.
   - Cifra tus claves utilizando el script `VentanaKeys.py`:

     ```bash
     python VentanaKeys.py
     ```

   - Esto generará un archivo `config.json.cif` con las claves cifradas.

## Uso

1. Ejecuta la aplicación:

   ```bash
   python main.py
   ```

2. La interfaz gráfica se abrirá, permitiéndote interactuar con el asistente de voz.

## Estructura del Proyecto

- `main.py`: Archivo principal que inicia la aplicación.
- `VentanaPrincipal.py`: Contiene la lógica de la interfaz gráfica.
- `VentanaKeys.py`: Permite cifrar las claves API.
- `DeepGramClient.py`: Módulo para interactuar con la API de Deepgram.
- `OpenRouterClient.py`: Módulo para interactuar con la API de OpenRouter.
- `config.json.cif`: Archivo que almacena las claves API cifradas.
- `requirements.txt`: Lista de dependencias de Python.

## Contribuciones

Las contribuciones son bienvenidas. Si deseas colaborar, por favor sigue estos pasos:

1. Haz un fork del repositorio.
2. Crea una nueva rama para tu característica o corrección de error.
3. Realiza tus cambios y haz commit.
4. Envía un pull request describiendo tus cambios.

## Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.
