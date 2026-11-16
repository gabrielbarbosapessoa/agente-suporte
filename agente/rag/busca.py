from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from agente.infra.db import conexao
from agente.config import RERANK_MIN_SCORE, RERANKER_MODEL
from agente.infra.llm import embeddings
from agente.rag.rerank import reranquear

SQL_BUSCA_HIBRIDA = """
WITH
consulta AS (
    SELECT replace(plainto_tsquery('portuguese', %(pergunta)s)::text, '&', '|')::tsquery AS q
),
vetorial AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> %(vetor)s::vector) AS posicao
    FROM politicas_chunks
    ORDER BY embedding <=> %(vetor)s::vector
    LIMIT %(k_candidatos)s
),
textual AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(busca_textual, consulta.q) DESC) AS posicao
    FROM politicas_chunks, consulta
    WHERE busca_textual @@ consulta.q
    ORDER BY ts_rank_cd(busca_textual, consulta.q) DESC
    LIMIT %(k_candidatos)s
),
fusao AS (
    SELECT COALESCE(v.id, t.id) AS id,
           COALESCE(1.0 / (%(rrf_k)s + v.posicao), 0)
         + COALESCE(1.0 / (%(rrf_k)s + t.posicao), 0) AS score,
           v.posicao AS pos_vetorial,
           t.posicao AS pos_textual
    FROM vetorial v
    FULL OUTER JOIN textual t ON t.id = v.id
)
SELECT c.id, c.documento, c.secao, c.conteudo,
       f.score, f.pos_vetorial, f.pos_textual
FROM fusao f
JOIN politicas_chunks c ON c.id = f.id
ORDER BY f.score DESC
LIMIT %(k)s
"""


class BuscaPoliticas(BaseRetriever):
    """Retriever híbrido das políticas da NovaByte."""

    k: int = 4               # quantos trechos devolver no final
    k_candidatos: int = 20   # quantos cada busca (vetorial e textual) traz
    k_fusao: int = 12        # quantos saem da fusão RRF e vão pro rerank
    rrf_k: int = 60          # constante do RRF

    # Rerank (bge-reranker-v2-m3) escolhido pelo eval (python -m evals.eval_retrieval):
    # híbrida 100% hit / MRR 0,774 · + bge 100% / 0,804 · + mMiniLM 86% / 0,756
    usar_rerank: bool = True
    modelo_rerank: str = RERANKER_MODEL
    min_score_rerank: float = RERANK_MIN_SCORE

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        params = {
            "pergunta": query,
            "vetor": str(embeddings().embed_query(query)),
            "k": self.k_fusao if self.usar_rerank else self.k,
            "k_candidatos": self.k_candidatos,
            "rrf_k": self.rrf_k,
        }
        with conexao() as conn:
            linhas = conn.execute(SQL_BUSCA_HIBRIDA, params).fetchall()

        docs = [
            Document(
                page_content=linha["conteudo"],
                metadata={
                    "id": linha["id"],
                    "documento": linha["documento"],
                    "secao": linha["secao"],
                    "score": float(linha["score"]),
                    "pos_vetorial": linha["pos_vetorial"],
                    "pos_textual": linha["pos_textual"],
                },
            )
            for linha in linhas
        ]

        if self.usar_rerank:
            docs = reranquear(query, docs, top_n=self.k,
                              min_score=self.min_score_rerank, modelo=self.modelo_rerank)
        return docs

if __name__ == "__main__":
    import sys

    pergunta = " ".join(sys.argv[1:]) or "posso devolver um produto se me arrependi?"
    for doc in BuscaPoliticas().invoke(pergunta):
        m = doc.metadata
        print(f"rerank={m.get('score_rerank', 0):.3f}  rrf={m['score']:.4f}  "
              f"vet={m['pos_vetorial']}  txt={m['pos_textual']}  {m['documento']} > {m['secao']}")