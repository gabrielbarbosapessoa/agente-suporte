import argparse
import uuid

from langchain_core.messages import HumanMessage

from agente.grafo import criar_grafo
from agente.memoria import checkpointer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread", default=None, help="id da conversa (para continuar uma antiga)")
    args = parser.parse_args()

    thread_id = args.thread or f"sessao-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    agente = criar_grafo(checkpointer())

    print(f"Conversa: {thread_id}  (digite 'sair' para encerrar)\n")
    while True:
        mensagem = input("Você: ").strip()
        if mensagem.lower() in {"sair", "exit", "quit"}:
            break
        if not mensagem:
            continue

        caminho = []
        for passo in agente.stream(
            {"mensagens": [HumanMessage(content=mensagem)]}, config, stream_mode="updates"
        ):
            caminho.extend(passo)

        estado = agente.get_state(config).values
        print(f"  [{' → '.join(caminho)}]")
        print(f"NovaByte: {estado['resposta']}\n")


if __name__ == "__main__":
    main()