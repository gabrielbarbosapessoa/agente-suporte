from decimal import Decimal

from agente.repositorios.pedidos import buscar_pedido


def test_busca_pedido_do_proprio_cliente():
    pedido = buscar_pedido(1, "ana.souza@example.com")
    assert pedido is not None
    assert pedido.status == "entregue"
    assert pedido.valor_total == Decimal("4299.00")
    assert pedido.itens[0].produto == "Notebook NovaBook Pro 14"


def test_email_ignora_maiusculas():
    assert buscar_pedido(1, "ANA.SOUZA@example.com") is not None


def test_pedido_de_outro_cliente_nao_aparece():
    assert buscar_pedido(3, "ana.souza@example.com") is None


def test_pedido_inexistente():
    assert buscar_pedido(999, "ana.souza@example.com") is None


def test_pedido_com_varios_itens():
    pedido = buscar_pedido(2, "ana.souza@example.com")
    assert len(pedido.itens) == 2
    soma = sum(i.preco_unitario * i.quantidade for i in pedido.itens)
    assert soma + pedido.valor_frete == pedido.valor_total