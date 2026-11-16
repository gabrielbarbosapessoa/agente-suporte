
import json
from typing import TypedDict

from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph

from agente.busca import BuscaPoliticas
from agente.pedidos import buscar_pedido
from agente.regras import analisar_pedido
from agente.resposta import cadeia_resposta
from agente.roteador import Classificacao, classificar



class Estado(TypedDict, total=False):
    mensagem: str                         
    historico: list[tuple[str, str]]      
    classificacao: Classificacao          
    trechos: list[Document]             
    dados_pedido: str                  
    resposta: str                        


MSG_BOAS_VINDAS = (
    "Olá! Sou o assistente da NovaByte. Posso ajudar com trocas e devoluções, "
    "garantia, entregas, pagamentos e com os seus pedidos. Como posso ajudar?"
)
MSG_PEDIR_DADOS = (
    "Para consultar o seu pedido, preciso do número do pedido e do e-mail usado na compra. "
    "Pode me informar?"
)



def rotear(estado: Estado) -> dict:
    return {"classificacao": classificar(estado["mensagem"], estado.get("historico"))}


def buscar_politicas(estado: Estado) -> dict:
    pergunta = estado["classificacao"].pergunta_reescrita
    return {"trechos": BuscaPoliticas().invoke(pergunta)}


def consultar_pedido(estado: Estado) -> dict:
    c = estado["classificacao"]
    pedido = buscar_pedido(c.pedido_id, c.email)
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
    return {"resposta": resposta}


def boas_vindas(estado: Estado) -> dict:
    return {"resposta": MSG_BOAS_VINDAS} 


def pedir_dados(estado: Estado) -> dict:
    return {"resposta": MSG_PEDIR_DADOS} 



def depois_do_roteador(estado: Estado) -> str:
    c = estado["classificacao"]
    if c.intencao == "outro":
        return "boas_vindas"
    if c.intencao == "politica":
        return "buscar_politicas"
  
    if not (c.pedido_id and c.email):
        return "pedir_dados"
    return "buscar_politicas" if c.intencao == "misto" else "consultar_pedido"


def depois_da_busca(estado: Estado) -> str:
    return "consultar_pedido" if estado["classificacao"].intencao == "misto" else "responder"

def criar_grafo():
    g = StateGraph(Estado)

    g.add_node("rotear", rotear)
    g.add_node("buscar_politicas", buscar_politicas)
    g.add_node("consultar_pedido", consultar_pedido)
    g.add_node("responder", responder)
    g.add_node("boas_vindas", boas_vindas)
    g.add_node("pedir_dados", pedir_dados)

    g.add_edge(START, "rotear")
    g.add_conditional_edges(
        "rotear", depois_do_roteador,
        ["boas_vindas", "buscar_politicas", "consultar_pedido", "pedir_dados"],
    )
    g.add_conditional_edges("buscar_politicas", depois_da_busca, ["consultar_pedido", "responder"])
    g.add_edge("consultar_pedido", "responder")
    g.add_edge("responder", END)
    g.add_edge("boas_vindas", END)
    g.add_edge("pedir_dados", END)

    return g.compile()


if __name__ == "__main__":
    import sys

    mensagem = " ".join(sys.argv[1:]) or "Posso devolver meu pedido 1? Meu e-mail é ana.souza@example.com"
    agente = criar_grafo()


    for passo in agente.stream({"mensagem": mensagem}, stream_mode="updates"):
        for no in passo:
            print(f"→ {no}")
            final = passo[no]
    print("\n" + final["resposta"])