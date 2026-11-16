from functools import lru_cache

from langchain_core.documents import Document

from agente.config import RERANK_MIN_SCORE, RERANKER_MODEL


@lru_cache
def _modelo():
    import torch
    from sentence_transformers import CrossEncoder


    return CrossEncoder(RERANKER_MODEL, activation_fn=torch.nn.Sigmoid())


def reranquear(
    pergunta: str,
    docs: list[Document],
    top_n: int = 4,
    min_score: float = RERANK_MIN_SCORE,
) -> list[Document]:
    if not docs:
        return []
    notas = _modelo().predict([(pergunta, d.page_content) for d in docs])
    for doc, nota in zip(docs, notas):
        doc.metadata["score_rerank"] = float(nota)
    ordenados = sorted(docs, key=lambda d: d.metadata["score_rerank"], reverse=True)
    return [d for d in ordenados if d.metadata["score_rerank"] >= min_score][:top_n]