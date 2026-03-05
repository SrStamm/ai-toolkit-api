import os
from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.llms.mistralai import MistralAI
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

def setup_llamaindex():
    load_dotenv()

    # Configuración del LLM
    P_API_KEY = os.getenv("MISTRAL_API_KEY")
    P_MODEL = os.getenv("P_MODEL", "mistral-small-latest")

    if not P_API_KEY:
        raise ValueError("Falta MISTRAL_API_KEY en el entorno")

    Settings.llm = MistralAI(model=P_MODEL, api_key=P_API_KEY)

    # Configuración del Modelo de Embedding 
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
