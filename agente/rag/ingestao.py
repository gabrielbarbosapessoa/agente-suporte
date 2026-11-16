import hashlib
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

from agente.infra.db import conexao
from agente.infra.llm import embeddings

PASTA_POLITICAS = Path("data/politicas")

_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "titulo"), ("##", "secao")],
)


def _limpar(texto: str) -> str:
    linhas = [l for l in texto.splitlines() if not l.lstrip().startswith(">")]
    return "\n".join(linhas)


def gerar_chunks(pasta: Path = PASTA_POLITICAS) -> list[Document]:
    chunks: list[Document] = []
    for arquivo in sorted(pasta.glob("*.md")):
        partes = _splitter.split_text(_limpar(arquivo.read_text(encoding="utf-8")))
        for parte in partes:
            secao = parte.metadata.get("secao")
            if not secao or not parte.page_content.strip():
                continue 
            titulo = parte.metadata.get("titulo", arquivo.stem)
       
            conteudo = f"[{titulo} > {secao}]\n{parte.page_content.strip()}"
            id_chunk = hashlib.sha256(f"{arquivo.name}|{conteudo}".encode()).hexdigest()[:32]
            chunks.append(Document(
                page_content=conteudo,
                metadata={"id": id_chunk, "documento": arquivo.name, "secao": secao},
            ))
    return chunks


SQL_INSERIR = """
    INSERT INTO politicas_chunks (id, documento, secao, conteudo, embedding)
    VALUES (%(id)s, %(documento)s, %(secao)s, %(conteudo)s, %(embedding)s::vector)
"""


def ingerir() -> None:
    chunks = gerar_chunks()
    ids_atuais = {c.metadata["id"] for c in chunks}

    with conexao() as conn:
        existentes = {linha["id"] for linha in conn.execute("SELECT id FROM politicas_chunks")}

    novos = [c for c in chunks if c.metadata["id"] not in existentes]
    removidos = existentes - ids_atuais

    vetores = embeddings().embed_documents([c.page_content for c in novos]) if novos else []

    with conexao() as conn, conn.transaction():
        if removidos:
            conn.execute("DELETE FROM politicas_chunks WHERE id = ANY(%s)", (list(removidos),))
        for chunk, vetor in zip(novos, vetores):
            conn.execute(SQL_INSERIR, {
                **chunk.metadata,
                "conteudo": chunk.page_content,
                "embedding": str(vetor),  
            })

    print(f"{len(chunks)} chunks | {len(novos)} novos | "
          f"{len(removidos)} removidos | {len(chunks) - len(novos)} sem mudança")


if __name__ == "__main__":
    ingerir()