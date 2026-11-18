from pathlib import Path

from agente.infra.db import conexao
from agente.rag.ingestao import ingerir

PASTA_SQL = Path(__file__).resolve().parents[2] / "db"


def banco_inicializado() -> bool:
    with conexao() as conn:
        linha = conn.execute("SELECT to_regclass('public.pedidos') AS tabela").fetchone()
    return linha["tabela"] is not None


def inicializar_banco() -> None:
    with conexao() as conn:
        for arquivo in sorted(PASTA_SQL.glob("*.sql")):
            conn.execute(arquivo.read_text(encoding="utf-8"))
            print(f"Executado: {arquivo.name}")


def main() -> None:
    if banco_inicializado():
        print("Banco já inicializado.")
    else:
        inicializar_banco()
    ingerir()


if __name__ == "__main__":
    main()
