from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from agente.db import conexao


class ItemPedido(BaseModel):
    produto: str
    categoria: str
    quantidade: int
    preco_unitario: Decimal


class Pedido(BaseModel):
    id: int
    cliente: str
    uf: str
    status: str
    forma_pagamento: str
    parcelas: int
    modalidade_entrega: str
    valor_frete: Decimal
    valor_total: Decimal
    codigo_rastreio: str | None
    criado_em: datetime
    pago_em: datetime | None
    enviado_em: datetime | None
    entregue_em: datetime | None
    itens: list[ItemPedido]

SQL_PEDIDO = """
    SELECT p.id, c.nome AS cliente, c.uf, p.status, p.forma_pagamento,
           p.parcelas, p.modalidade_entrega, p.valor_frete, p.valor_total,
           p.codigo_rastreio, p.criado_em, p.pago_em, p.enviado_em, p.entregue_em
    FROM pedidos p
    JOIN clientes c ON c.id = p.cliente_id
    WHERE p.id = %(pedido_id)s
      AND lower(c.email) = lower(%(email)s)
"""


SQL_ITENS = """
    SELECT pr.nome AS produto, pr.categoria, i.quantidade, i.preco_unitario
    FROM itens_pedido i
    JOIN produtos pr ON pr.id = i.produto_id
    WHERE i.pedido_id = %(pedido_id)s
    ORDER BY i.id
"""

def buscar_pedido(pedido_id: int, email: str) -> Pedido | None:
    """Retorna o pedido se ele pertencer ao cliente com esse e-mail; senão None."""
    params = {"pedido_id": pedido_id, "email": email}
    with conexao() as conn:
        linha = conn.execute(SQL_PEDIDO, params).fetchone()
        if linha is None:
            return None
        itens = conn.execute(SQL_ITENS, params).fetchall()
    return Pedido(**linha, itens=[ItemPedido(**item) for item in itens])