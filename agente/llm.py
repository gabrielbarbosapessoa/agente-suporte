from functools import lru_cache

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from agente.config import EMBEDDING_DIM, EMBEDDING_MODEL


@lru_cache
def embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        output_dimensionality=EMBEDDING_DIM,
    )