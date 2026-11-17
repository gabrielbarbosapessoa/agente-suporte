import argparse
import uuid

from langchain_core.messages import HumanMessage
from langchain_core.tracers.langchain import wait_for_all_tracers


from agente.fluxo.grafo import criar_grafo
from agente.infra.memoria import checkpointer
from agente.config import RERANKER_MODEL
from agente.rag.rerank import _modelo as carregar_reranker
from agente.seguranca.guardrails import mascarar_dados_sensiveis


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread", default=None, help="id da conversa (para continuar uma antiga)")
    parser.add_argument("--debug", action="store_true", help="mostra o caminho percorrido no grafo")
    args = parser.parse_args()

    thread_id = args.thread or f"sessao-{uuid.uuid4().hex[:8]}"
    config = {
        "configurable": {"thread_id": thread_id},
        # Aparecem no LangSmith: dá pra filtrar todas as execuções de uma conversa
        "run_name": "atendimento",
        "tags": ["chat"],
        "metadata": {"thread_id": thread_id},
    }
    agente = criar_grafo(checkpointer())

    # Warm-up: carrega o reranker (≈2 GB) ANTES da primeira pergunta, e não no meio dela
    print("Carregando modelos...")
    carregar_reranker(RERANKER_MODEL)  # aquecer: o lru_cache guarda o modelo para as próximas chamadas

    print(f"Conversa: {thread_id}  (digite 'sair' para encerrar)\n")
    salvo = agente.get_state(config).values
    if salvo.get("mensagens"):
        print(f"(última mensagem) NovaByte: {salvo['mensagens'][-1].content}\n")
    while True:
        mensagem = input("Você: ").strip()
        if mensagem.lower() in {"sair", "exit", "quit"}:
            break
        if not mensagem:
            continue

        caminho = []
        for passo in agente.stream(
            {"mensagens": [HumanMessage(content=mascarar_dados_sensiveis(mensagem))]}, config, stream_mode="updates"
        ):
            caminho.extend(passo)

        estado = agente.get_state(config).values
        if args.debug:
            print(f"  [{' → '.join(caminho)}]")
        print(f"NovaByte: {estado['resposta']}")

        # As citações [1], [2]... só fazem sentido se o cliente puder ver a que se referem
        trechos = estado.get("trechos") or []
        if trechos and "responder" in caminho:
            print("Fontes:")
            for i, doc in enumerate(trechos, start=1):
                print(f"  [{i}] {doc.metadata['documento']} > {doc.metadata['secao']}")
        print()


if __name__ == "__main__":
    try:
        main()
    finally:
        # Os traces vão para o LangSmith em segundo plano: espera terminar de enviar antes de fechar
        wait_for_all_tracers()