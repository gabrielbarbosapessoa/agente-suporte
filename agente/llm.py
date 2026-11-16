from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from agente.config import EMBEDDING_DIM, EMBEDDING_MODEL, LLM_MODEL


@lru_cache
def embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        output_dimensionality=EMBEDDING_DIM,
    )


@lru_cache
def llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=LLM_MODEL)