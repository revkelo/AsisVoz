import utils

# Extraer claves desde un archivo cifrado
utils.descifrar_y_extraer_claves("config.json.cif")

# Ahora las claves están disponibles así:
print("Clave Deepgram:", utils.DEEPGRAM_API_KEY)
print("Clave OpenRouter:", utils.OPENROUTER_API_KEY)
