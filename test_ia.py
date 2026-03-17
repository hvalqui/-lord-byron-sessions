import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq


# 1. Cargamos la ruta absoluta que ya comprobamos que funciona
env_path = "/home/hvalqui/HValquiWorks/AI-DC_2025/06_AgentesIA/scr_ia/.env"
load_dotenv(env_path)

# 2. Configuramos el modelo con el nombre que salió en tu lista
#llm = ChatGoogleGenerativeAI(
    #model="gemini-2.5-flash", 
#    model="gemini-2.0-flash-lite",
#    google_api_key=os.getenv("GOOGLE_API_KEY")
#)
llm = ChatGroq(model="llama-3.3-70b-versatile")


# 3. Prueba de fuego
try:
    #print("Probando conexión con Gemini 2.5 Flash...")
    print("Probando conexión con llama-3.3-70b-versatile...")
    respuesta = llm.invoke("Hello! Give me a very short definition of 'Syntax'.")
    print("\n--- RESPUESTA ---")
    print(respuesta.content)
    print("-----------------")
    print("\n¡CONEXIÓN TOTALMENTE ESTABLE!")
except Exception as e:
    print(f"\nError final: {e}")