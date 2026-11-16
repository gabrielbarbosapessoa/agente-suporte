from decimal import Decimal

from agente.infra.db import conexao


def solicitacao_ativa(pedido_id: int) -> dict | None:
    with conexao() as conn:
        return conn.execute(
            """SELECT id, status FROM solicitacoes
               WHERE pedido_id = %s AND status IN ('pendente_aprovacao', 'aprovada')""",
            (pedido_id,),
        ).fetchone()


def criar_solicitacao(pedido_id: int, valor: Decimal, status: str, thread_cliente: str,
                      decidido_por: str | None = None) -> int:
    with conexao() as conn:
        linha = conn.execute(
            """INSERT INTO solicitacoes (pedido_id, valor, status, thread_cliente, decidido_por,
                                         decidido_em)
               VALUES (%(pedido_id)s, %(valor)s, %(status)s, %(thread)s, %(por)s,
                       CASE WHEN %(por)s::text IS NULL THEN NULL ELSE now() END)
               RETURNING id""",
            {"pedido_id": pedido_id, "valor": valor, "status": status,
             "thread": thread_cliente, "por": decidido_por},
        ).fetchone()
    return linha["id"]


def registrar_decisao(solicitacao_id: int, aprovada: bool, decidido_por: str) -> None:
    with conexao() as conn:
        conn.execute(
            """UPDATE solicitacoes
               SET status = %(status)s, decidido_em = now(), decidido_por = %(por)s
               WHERE id = %(id)s AND status = 'pendente_aprovacao'""",
            {"status": "aprovada" if aprovada else "recusada", "por": decidido_por,
             "id": solicitacao_id},
        )


def listar_pendentes() -> list[dict]:
    with conexao() as conn:
        return conn.execute(
            """SELECT s.id, s.pedido_id, s.valor, s.criado_em, c.nome AS cliente
               FROM solicitacoes s
               JOIN pedidos p ON p.id = s.pedido_id
               JOIN clientes c ON c.id = p.cliente_id
               WHERE s.status = 'pendente_aprovacao'
               ORDER BY s.criado_em"""
        ).fetchall()