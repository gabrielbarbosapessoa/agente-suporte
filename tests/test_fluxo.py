from langchain_core.messages import HumanMessage

from agente.fluxo import grafo
from agente.fluxo.roteador import Classificacao

PERGUNTA_CARLA = "Meu pedido 4 está atrasado, tenho direito a alguma coisa?"


def _classificador_fixo(monkeypatch, classificacao):
    monkeypatch.setattr(grafo, "classificar", lambda mensagem, historico: classificacao)


def test_pedir_dados_guarda_a_pergunta_pendente():
    original = Classificacao(intencao="misto", pedido_id=4, pergunta_reescrita=PERGUNTA_CARLA)
    atualizacao = grafo.pedir_dados({"classificacao": original})
    assert atualizacao["pendente"] == original
    assert atualizacao["resposta"] == grafo.MSG_PEDIR_DADOS


def test_dados_completados_retomam_a_intencao_original(monkeypatch):
    pendente = Classificacao(intencao="misto", pedido_id=4, pergunta_reescrita=PERGUNTA_CARLA)
    _classificador_fixo(monkeypatch, Classificacao(
        intencao="pedido", email="carla.mendes@example.com", pergunta_reescrita="Consultar o pedido 4"))

    atualizacao = grafo.rotear({
        "mensagens": [HumanMessage(content="carla.mendes@example.com")],
        "pendente": pendente,
    })

    assert atualizacao["classificacao"].intencao == "misto"
    assert atualizacao["classificacao"].pergunta_reescrita == PERGUNTA_CARLA
    assert atualizacao["email"] == "carla.mendes@example.com"
    assert atualizacao["pendente"] is None


def test_devolucao_pendente_continua_sendo_devolucao(monkeypatch):
    pendente = Classificacao(intencao="devolucao", pedido_id=7, pergunta_reescrita="Quero devolver o pedido 7")
    _classificador_fixo(monkeypatch, Classificacao(
        intencao="pedido", email="fernando.alves@example.com", pergunta_reescrita="Consultar o pedido 7"))

    atualizacao = grafo.rotear({
        "mensagens": [HumanMessage(content="fernando.alves@example.com")],
        "pendente": pendente,
    })

    assert atualizacao["classificacao"].intencao == "devolucao"


def test_mudanca_de_assunto_descarta_a_pendente(monkeypatch):
    pendente = Classificacao(intencao="misto", pedido_id=4, pergunta_reescrita=PERGUNTA_CARLA)
    nova = Classificacao(intencao="politica", pergunta_reescrita="Qual o prazo de garantia?")
    _classificador_fixo(monkeypatch, nova)

    atualizacao = grafo.rotear({
        "mensagens": [HumanMessage(content="Qual o prazo de garantia?")],
        "pendente": pendente,
    })

    assert atualizacao["classificacao"] == nova
    assert atualizacao["pendente"] is None
