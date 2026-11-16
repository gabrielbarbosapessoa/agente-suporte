import json
from typing import Annotated, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, AnyMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from agente.busca import BuscaPoliticas
from agente.config import JANELA_HISTORICO
from agente.pedidos import buscar_pedido
from agente.regras import analisar_pedido
from agente.resposta import cadeia_resposta
from agente.roteador import Classificacao, classificar

from langchain_core.runnables import RunnableConfig
from agente.aprovacao import iniciar_aprovacao
from agente.solicitacoes import criar_solicitacao, solicitacao_ativa


class Estado(TypedDict, total=False):
    mensagens: Annotated[list[AnyMessage], add_messages]  
    email: str | None                              
    pedido_id: int | None


    classificacao: Classificacao
    trechos: list[Document]
    dados_pedido: str | None
    resposta: str


MSG_BOAS_VINDAS = (
    "Olá! Sou o assistente da NovaByte. Posso ajudar com trocas e devoluções, "
    "garantia, entregas, pagamentos e com os seus pedidos. Como posso ajudar?"
)
MSG_PEDIR_DADOS = (
    "Para consultar o seu pedido, preciso do número do pedido e do e-mail usado na compra. "
    "Pode me informar?"
)


def _responder_com(texto: str) -> dict:
    """Toda resposta vira uma AIMessage no histórico."""
    return {"resposta": texto, "mensagens": [AIMessage(content=texto)]}



def rotear(estado: Estado) -> dict:
    mensagens = estado["mensagens"]
    ultima = mensagens[-1].content
    historico = mensagens[:-1][-JANELA_HISTORICO:] 

    c = classificar(ultima, historico)

    atualizacao = {
        "classificacao": c,
        "trechos": [],
        "dados_pedido": None,
    }
    if c.email:
        atualizacao["email"] = c.email
    if c.pedido_id:
        atualizacao["pedido_id"] = c.pedido_id
    return atualizacao


def buscar_politicas(estado: Estado) -> dict:
    pergunta = estado["classificacao"].pergunta_reescrita
    return {"trechos": BuscaPoliticas().invoke(pergunta)}


def consultar_pedido(estado: Estado) -> dict:
    pedido = buscar_pedido(estado["pedido_id"], estado["email"])
    if pedido is None:
        return {"dados_pedido": "Pedido não encontrado para esse número e e-mail."}
    dados = {
        "pedido": pedido.model_dump(mode="json"),
        "fatos_calculados": analisar_pedido(pedido).model_dump(),
    }
    return {"dados_pedido": json.dumps(dados, ensure_ascii=False, indent=2)}


def responder(estado: Estado) -> dict:
    resposta = cadeia_resposta().invoke({
        "pergunta": estado["classificacao"].pergunta_reescrita,
        "trechos": estado.get("trechos", []),
        "dados_pedido": estado.get("dados_pedido"),
    })
    return _responder_com(resposta)

def solicitar_devolucao(estado: Estado, config: RunnableConfig) -> dict:
    """Ação: abre a devolução. Mensagens fixas (sem LLM): resultado de ação tem que ser exato."""
    pedido = buscar_pedido(estado["pedido_id"], estado["email"])
    if pedido is None:
        return _responder_com("Não encontrei esse pedido para o e-mail informado.")

    ativa = solicitacao_ativa(pedido.id)
    if ativa:
        return _responder_com(
            f"Já existe a solicitação de devolução #{ativa['id']} para o pedido {pedido.id} "
            f"(situação: {ativa['status'].replace('_', ' ')})."
        )

    analise = analisar_pedido(pedido)
    if not analise.pode_arrependimento:
        return _responder_com(
            f"Não consigo abrir a devolução por arrependimento do pedido {pedido.id}: "
            "ela só vale para pedidos entregues há até 7 dias corridos. "
            "Se o produto tiver defeito, posso te explicar como acionar a garantia."
        )

    thread_cliente = config["configurable"]["thread_id"]
    aviso_fone = (
        " Atenção: fones intra-auriculares só são aceitos com o lacre de higiene intacto."
        if any(i.categoria == "fone" for i in pedido.itens) else ""
    )

    if analise.reembolso_precisa_aprovacao:
        sid = criar_solicitacao(pedido.id, pedido.valor_total, "pendente_aprovacao", thread_cliente)
        iniciar_aprovacao(sid, pedido.id, str(pedido.valor_total), thread_cliente)  # ⏸️ HITL
        return _responder_com(
            f"Abri a solicitação de devolução #{sid} do pedido {pedido.id}. Como o reembolso "
            f"(R$ {pedido.valor_total}) é acima de R$ 1.000, ele passa pela aprovação do "
            "financeiro, em até 2 dias úteis. Eu te aviso aqui assim que houver uma decisão."
            + aviso_fone
        )

    sid = criar_solicitacao(pedido.id, pedido.valor_total, "aprovada", thread_cliente,
                            decidido_por="automatico")
    return _responder_com(
        f"Pronto! A devolução #{sid} do pedido {pedido.id} foi aprovada. Você vai receber por "
        "e-mail o código de postagem gratuito dos Correios." + aviso_fone
    )

def boas_vindas(estado: Estado) -> dict:
    return _responder_com(MSG_BOAS_VINDAS)  


def pedir_dados(estado: Estado) -> dict:
    return _responder_com(MSG_PEDIR_DADOS)  



def depois_do_roteador(estado: Estado) -> str:
    c = estado["classificacao"]
    if c.intencao == "outro":
        return "boas_vindas"
    if c.intencao == "politica":
        return "buscar_politicas"

    if not (estado.get("pedido_id") and estado.get("email")):
        return "pedir_dados"
    if c.intencao == "devolucao":
        return "solicitar_devolucao"
    return "buscar_politicas" if c.intencao == "misto" else "consultar_pedido"


def depois_da_busca(estado: Estado) -> str:
    return "consultar_pedido" if estado["classificacao"].intencao == "misto" else "responder"


def criar_grafo(checkpointer=None):
    g = StateGraph(Estado)

    g.add_node("rotear", rotear)
    g.add_node("buscar_politicas", buscar_politicas)
    g.add_node("consultar_pedido", consultar_pedido)
    g.add_node("responder", responder)
    g.add_node("boas_vindas", boas_vindas)
    g.add_node("pedir_dados", pedir_dados)
    g.add_node("solicitar_devolucao", solicitar_devolucao)

    g.add_edge(START, "rotear")
    g.add_conditional_edges(
        "rotear", depois_do_roteador,
        ["boas_vindas", "buscar_politicas", "consultar_pedido", "pedir_dados", "solicitar_devolucao"],
    )
    g.add_conditional_edges("buscar_politicas", depois_da_busca, ["consultar_pedido", "responder"])
    g.add_edge("consultar_pedido", "responder")
    g.add_edge("responder", END)
    g.add_edge("boas_vindas", END)
    g.add_edge("pedir_dados", END)
    g.add_edge("solicitar_devolucao", END)

    return g.compile(checkpointer=checkpointer)
