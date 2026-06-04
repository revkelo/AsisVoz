# AsisVoz

App de escritorio para **transcripción de audio y video con IA**. Soporta drag & drop, genera PDF y DOCX con timestamps y diarización de hablantes, e incluye un módulo de preguntas sobre la transcripción usando DeepSeek vía OpenRouter.

## Funcionalidades

- **Transcripción** de archivos de audio y video con Deepgram (STT)
- **Drag & drop** — arrastra el archivo directamente a la ventana
- **Diarización** — identifica y separa hablantes (`Speaker 0`, `Speaker 1`...)
- **Exporta a PDF y DOCX** con timestamps `[HH:MM:SS]` por segmento
- **Módulo QA** — transcribe y luego hace preguntas al documento con DeepSeek
- **Fallback automático** entre modelos de OpenRouter ante errores 429
- **Claves API cifradas** en `config.json.cif` — nunca en texto plano
- **Ejecutable .exe** compilado con PyInstaller (Windows)

## Stack

- **Python 3.11+**
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — GUI moderna
- [TkinterDnD2](https://github.com/pmgagne/tkinterdnd2) — drag & drop
- [Deepgram SDK](https://developers.deepgram.com/) — speech-to-text
- [OpenRouter](https://openrouter.ai/) — LLM (DeepSeek R1)
- [MoviePy](https://zulko.github.io/moviepy/) — extracción de audio de video
- [fpdf2](https://py-pdf.github.io/fpdf2/) — generación de PDF
- [python-docx](https://python-docx.readthedocs.io/) — generación de DOCX

## Instalación

```bash
git clone https://github.com/revkelo/AsisVoz.git
cd AsisVoz
pip install -r requirements.txt
```

## Configuración de claves API

Ejecutar el asistente de configuración al primer uso:

```bash
python VentanaKeys.py
```

Esto cifra y guarda tus claves en `config.json.cif`. Necesitas:
- **Deepgram API Key** — [console.deepgram.com](https://console.deepgram.com)
- **OpenRouter API Key** — [openrouter.ai/keys](https://openrouter.ai/keys)

> Las claves se almacenan cifradas localmente. Nunca se suben al repositorio.

## Uso

```bash
python main.py
```

1. Arrastra un archivo de audio/video a la ventana (o usa el selector)
2. La app transcribe con Deepgram, separando hablantes con timestamps
3. Exporta el resultado como `.pdf` y `.docx`

### Módulo QA (CLI)

Transcribe un audio y luego haz preguntas sobre el contenido:

```bash
cd QA
# Configurar DEEPGRAM_API_KEY y OPENROUTER_API_KEY en .env
cp .env.example .env
python main.py
```

## Estructura

```
AsisVoz/
├── main.py                # Punto de entrada + sistema de licencias
├── VentanaPrincipal.py    # GUI principal (CustomTkinter + drag & drop)
├── DeepGramClient.py      # Transcripción STT + generación PDF/DOCX
├── OpenRouterClient.py    # Chat IA con fallback entre modelos DeepSeek
├── VentanaKeys.py         # Cifrado y gestión de API keys
├── utils.py               # Utilidades compartidas
├── requirements.txt
└── QA/
    ├── main.py            # CLI: transcripción + Q&A sobre el documento
    └── .env.example
```

## Compilar ejecutable (Windows)

```bash
python -m PyInstaller --onefile --noconsole \
  --add-data "media/*;media" \
  --add-data "config.json.cif;." \
  --icon=media/logo.ico main.py
```

El `.exe` queda en `dist/main.exe`.

---

Desarrollado por **Kevin Gonzalez**
