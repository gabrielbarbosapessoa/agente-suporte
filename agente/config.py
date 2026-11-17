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

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIM = 768  

RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
RERANK_MIN_SCORE = float(os.getenv("RERANK_MIN_SCORE", "0.0"))

LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")

JANELA_HISTORICO = 6

PROMPT_GUARD_MODEL = os.getenv("PROMPT_GUARD_MODEL", "meta-llama/Llama-Prompt-Guard-2-86M")
PROMPT_GUARD_LIMIAR = float(os.getenv("PROMPT_GUARD_LIMIAR", "0.5"))
PROMPT_GUARD_ATIVO = os.getenv("PROMPT_GUARD_ATIVO", "true").lower() == "true"