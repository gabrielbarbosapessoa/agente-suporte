"""Reranking com cross-encoder: reordena os candidatos da busca híbrida."""
from functools import lru_cache

from langchain_core.documents import Document
from langsmith import traceable

from agente.config import RERANK_MIN_SCORE, RERANKER_MODEL, RERANKER_REVISION


@lru_cache
def _modelo(nome: str):
    import torch
    from sentence_transformers import CrossEncoder

    return CrossEncoder(nome, revision=RERANKER_REVISION, activation_fn=torch.nn.Sigmoid())


@traceable(name="rerank", run_type="chain")
def reranquear(
    pergunta: str,
    docs: list[Document],
    top_n: int = 4,
    min_score: float = RERANK_MIN_SCORE,
    modelo: str = RERANKER_MODEL,
) -> list[Document]:
    """Dá uma nota de 0 a 1 para cada par (pergunta, trecho), ordena e corta."""
    if not docs:
        return []
    notas = _modelo(modelo).predict([(pergunta, d.page_content) for d in docs])
    for doc, nota in zip(docs, notas):
        doc.metadata["score_rerank"] = float(nota)
    ordenados = sorted(docs, key=lambda d: d.metadata["score_rerank"], reverse=True)
    return [d for d in ordenados if d.metadata["score_rerank"] >= min_score][:top_n]
