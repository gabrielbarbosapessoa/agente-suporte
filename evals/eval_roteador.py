from collections import Counter

from agente.fluxo.roteador import classificar
from evals.comum import carregar_casos, historico_como_mensagens, pausar, porcentagem


def main() -> None:
    casos = carregar_casos()
    acertos = Counter()
    erros = []

    for i, caso in enumerate(casos, start=1):
        c = classificar(caso["mensagem"], historico_como_mensagens(caso))

        checagens = {
            "intencao": c.intencao in caso.get("intencoes_aceitas", [caso["intencao"]]),
            "pedido_id": c.pedido_id == caso.get("pedido_id"),
            "email": (c.email or None) == caso.get("email"),
        }
        for nome, ok in checagens.items():
            acertos[nome] += ok
        if not all(checagens.values()):
            erros.append((caso["id"], caso["intencao"], c))

        print(f"[{i}/{len(casos)}] {'ok' if all(checagens.values()) else 'nãook'} {caso['id']}")
        pausar()

    total = len(casos)
    print("\n=== ROTEADOR ===")
    for nome in ("intencao", "pedido_id", "email"):
        print(f"{nome:<10} {porcentagem(acertos[nome], total)}")

    if erros:
        print("\nErros:")
        for id_, esperado, c in erros:
            print(f"- {id_}: esperado={esperado} | veio={c.intencao} "
                  f"pedido={c.pedido_id} email={c.email}")


if __name__ == "__main__":
    main()