import os

from dotenv import load_dotenv

load_dotenv()

def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome)
    if not valor:
        raise ValueError(f"Variável de ambiente obrigatória '{nome}' não definida no .env")
    return valor

POSTGRES_USER = _obrigatoria("POSTGRES_USER")
POSTGRES_PASSWORD = _obrigatoria("POSTGRES_PASSWORD")
POSTGRES_DB = _obrigatoria("POSTGRES_DB")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))  
POSTGRES_HOST = _obrigatoria("POSTGRES_HOST")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"