from agente.db import conexao
from agente.modelos import ItemPedido, Pedido




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