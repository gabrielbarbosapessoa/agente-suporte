import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from agente.modelos import Pedido

FUSO_LOJA = ZoneInfo("America/Sao_Paulo")


PRAZO_ARREPENDIMENTO_DIAS = 7              
LIMITE_SEM_APROVACAO = Decimal("1000.00")   
TOLERANCIA_ATRASO_DIAS_UTEIS = 5           

PRAZO_POR_REGIAO = {"Sudeste": 5, "Sul": 7, "Centro-Oeste": 8, "Nordeste": 10, "Norte": 15}
REGIAO_POR_UF = {
    **dict.fromkeys(["SP", "RJ", "MG", "ES"], "Sudeste"),
    **dict.fromkeys(["PR", "SC", "RS"], "Sul"),
    **dict.fromkeys(["DF", "GO", "MT", "MS"], "Centro-Oeste"),
    **dict.fromkeys(["BA", "SE", "AL", "PE", "PB", "RN", "CE", "PI", "MA"], "Nordeste"),
    **dict.fromkeys(["AM", "PA", "AC", "RO", "RR", "AP", "TO"], "Norte"),
}


def dias_uteis(inicio: date, fim: date) -> int:
    """Dias úteis (seg a sex) depois de `inicio` até `fim`. Não considera feriados."""
    total, dia = 0, inicio
    while dia < fim:
        dia += timedelta(days=1)
        if dia.weekday() < 5: 
            total += 1
    return total


def dentro_do_arrependimento(entregue_em: date, hoje: date) -> bool:
    return 0 <= (hoje - entregue_em).days <= PRAZO_ARREPENDIMENTO_DIAS


def precisa_aprovacao(valor: Decimal) -> bool:
    return valor > LIMITE_SEM_APROVACAO


def prazo_entrega(uf: str, modalidade: str) -> int:
    prazo = PRAZO_POR_REGIAO[REGIAO_POR_UF[uf.upper()]]
    if modalidade == "expressa":
        prazo = math.ceil(prazo / 2) 
    return prazo


class AnalisePedido(BaseModel):
   
    dias_desde_entrega: int | None
    pode_arrependimento: bool
    reembolso_precisa_aprovacao: bool
    dias_uteis_de_atraso: int
    atraso_da_direito_a_compensacao: bool


def analisar_pedido(pedido: Pedido, hoje: date | None = None) -> AnalisePedido:
    hoje = hoje or datetime.now(FUSO_LOJA).date()

    dias_desde_entrega = None
    if pedido.entregue_em:
        entregue = pedido.entregue_em.astimezone(FUSO_LOJA).date()
        dias_desde_entrega = (hoje - entregue).days

    atraso = 0
    if pedido.status in {"pagamento_aprovado", "em_separacao", "enviado"} and pedido.pago_em:
        pago = pedido.pago_em.astimezone(FUSO_LOJA).date()
        atraso = max(0, dias_uteis(pago, hoje) - prazo_entrega(pedido.uf, pedido.modalidade_entrega))

    return AnalisePedido(
        dias_desde_entrega=dias_desde_entrega,
        pode_arrependimento=(
            pedido.status == "entregue"
            and dias_desde_entrega is not None
            and dias_desde_entrega <= PRAZO_ARREPENDIMENTO_DIAS
        ),
        reembolso_precisa_aprovacao=precisa_aprovacao(pedido.valor_total),
        dias_uteis_de_atraso=atraso,
        atraso_da_direito_a_compensacao=atraso > TOLERANCIA_ATRASO_DIAS_UTEIS,
    )