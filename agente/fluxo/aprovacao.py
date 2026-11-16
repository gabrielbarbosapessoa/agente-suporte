from functools import lru_cache
from typing import TypedDict

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from agente.infra.memoria import checkpointer
from agente.repositorios.solicitacoes import listar_pendentes, registrar_decisao


class EstadoAprovacao(TypedDict, total=False):
    solicitacao_id: int
    pedido_id: int
    valor: str
    thread_cliente: str
    decisao: dict


def aguardar_decisao(estado: EstadoAprovacao) -> dict:
    decisao = interrupt({
        "solicitacao_id": estado["solicitacao_id"],
        "pedido_id": estado["pedido_id"],
        "valor": estado["valor"],
        "pergunta": "Aprovar o reembolso?",
    })
    return {"decisao": decisao}


def registrar(estado: EstadoAprovacao) -> dict:
    d = estado["decisao"]
    registrar_decisao(estado["solicitacao_id"], d["aprovada"], d["por"])

    if d["aprovada"]:
        texto = (f"Boa notícia: sua solicitação de devolução #{estado['solicitacao_id']} "
                 f"(pedido {estado['pedido_id']}) foi aprovada pelo financeiro. "
                 "Você vai receber por e-mail o código de postagem gratuito dos Correios.")
    else:
        texto = (f"Sua solicitação de devolução #{estado['solicitacao_id']} "
                 f"(pedido {estado['pedido_id']}) não foi aprovada pelo financeiro. "
                 "Se quiser, posso abrir um chamado para a equipe explicar o motivo.")


    from agente.fluxo.grafo import criar_grafo  
    criar_grafo(checkpointer()).update_state(
        {"configurable": {"thread_id": estado["thread_cliente"]}},
        {"mensagens": [AIMessage(content=texto)], "resposta": texto},
        as_node="responder",
    )
    return {}


@lru_cache
def grafo_aprovacao():
    g = StateGraph(EstadoAprovacao)
    g.add_node("aguardar_decisao", aguardar_decisao)
    g.add_node("registrar", registrar)
    g.add_edge(START, "aguardar_decisao")
    g.add_edge("aguardar_decisao", "registrar")
    g.add_edge("registrar", END)
    return g.compile(checkpointer=checkpointer())


def _config(solicitacao_id: int) -> dict:
    return {"configurable": {"thread_id": f"aprovacao-{solicitacao_id}"}}


def iniciar_aprovacao(solicitacao_id: int, pedido_id: int, valor: str, thread_cliente: str) -> None:
    """Roda o fluxo até o interrupt: fica salvo no Postgres, esperando a decisão."""
    grafo_aprovacao().invoke(
        {"solicitacao_id": solicitacao_id, "pedido_id": pedido_id,
         "valor": valor, "thread_cliente": thread_cliente},
        _config(solicitacao_id),
    )


def decidir(solicitacao_id: int, aprovada: bool, por: str = "financeiro") -> None:
    """Retoma o fluxo pausado com a decisão do humano."""
    grafo_aprovacao().invoke(
        Command(resume={"aprovada": aprovada, "por": por}),
        _config(solicitacao_id),
    )


if __name__ == "__main__":
    import sys

    comando = sys.argv[1] if len(sys.argv) > 1 else "listar"
    if comando == "listar":
        pendentes = listar_pendentes()
        if not pendentes:
            print("Nenhuma solicitação aguardando aprovação.")
        for s in pendentes:
            print(f"#{s['id']}  pedido {s['pedido_id']}  {s['cliente']}  R$ {s['valor']}  "
                  f"desde {s['criado_em']:%d/%m %H:%M}")
    elif comando in {"aprovar", "recusar"}:
        decidir(int(sys.argv[2]), aprovada=(comando == "aprovar"))
        print(f"Solicitação #{sys.argv[2]}: {comando} registrado e cliente avisado.")
    else:
        print(__doc__)