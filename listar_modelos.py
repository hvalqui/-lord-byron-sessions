import os
from dotenv import load_dotenv
import google.generativeai as genai

# 1. Definimos la ruta que tú me diste
env_path = "/home/hvalqui/HValquiWorks/AI-DC_2025/06_AgentesIA/scr_ia/.env"

print(f"--- DIAGNÓSTICO ---")
# Verificamos si el archivo existe físicamente
if os.path.exists(env_path):
    print(f"1. El archivo .env EXISTE en la ruta.")
else:
    print(f"1. ERROR: No se encuentra el archivo en {env_path}")

# 2. Intentamos cargar las variables
load_dotenv(env_path)
api_key = os.getenv("GOOGLE_API_KEY")

if api_key:
    # Mostramos solo los primeros 5 caracteres por seguridad
    print(f"2. Llave encontrada: {api_key[:5]}**********")
    
    # 3. Intentamos la conexión
    genai.configure(api_key=api_key)
    print("3. Conectando con Google...")
    
    try:
        modelos = list(genai.list_models())
        if not modelos:
            print("4. Conexión exitosa, pero la lista de modelos volvió VACÍA.")
        else:
            print(f"4. ¡ÉXITO! Se encontraron {len(modelos)} modelos:")
            for m in modelos:
                if 'generateContent' in m.supported_generation_methods:
                    print(f"   - {m.name.split('/')[-1]}")
    except Exception as e:
        print(f"4. ERROR al conectar con Google: {e}")
else:
    print("2. ERROR: La variable GOOGLE_API_KEY está vacía o no existe en el archivo.")