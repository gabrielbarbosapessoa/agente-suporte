from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

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