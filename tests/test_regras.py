from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from agente import regras
from agente.modelos import Pedido

HOJE = date(2026, 11, 16)  # segunda-feira fixa → teste sempre igual


def test_dias_uteis_pula_fim_de_semana():
    assert regras.dias_uteis(date(2026, 11, 13), HOJE) == 1  # sexta → segunda


@pytest.mark.parametrize("dias, esperado", [(0, True), (7, True), (8, False)])
def test_arrependimento_limite_de_7_dias(dias, esperado):
    assert regras.dentro_do_arrependimento(HOJE - timedelta(days=dias), HOJE) is esperado


@pytest.mark.parametrize("valor, esperado", [("1000.00", False), ("1000.01", True)])
def test_aprovacao_acima_de_mil(valor, esperado):
    assert regras.precisa_aprovacao(Decimal(valor)) is esperado


def test_expressa_e_metade_do_prazo():
    assert regras.prazo_entrega("SP", "expressa") == 3  # 5 / 2 → 3


def _ha(dias: int) -> datetime:
    return datetime(2026, 11, 16, 14, tzinfo=regras.FUSO_LOJA) - timedelta(days=dias)


def _pedido(**campos) -> Pedido:
    base = dict(id=1, cliente="Teste", uf="SP", status="entregue", forma_pagamento="cartao",
                parcelas=1, modalidade_entrega="padrao", valor_frete=Decimal("0"),
                valor_total=Decimal("100"), codigo_rastreio=None, criado_em=_ha(10),
                pago_em=None, enviado_em=None, entregue_em=None, itens=[])
    return Pedido(**{**base, **campos})


def test_analise_ana_notebook():
    analise = regras.analisar_pedido(_pedido(entregue_em=_ha(3), valor_total=Decimal("4299")), HOJE)
    assert analise.pode_arrependimento and analise.reembolso_precisa_aprovacao


def test_analise_carla_atrasada_no_norte():
    analise = regras.analisar_pedido(_pedido(uf="AM", status="enviado", pago_em=_ha(36)), HOJE)
    assert analise.atraso_da_direito_a_compensacao