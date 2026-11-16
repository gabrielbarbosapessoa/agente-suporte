from agente.rag.busca import BuscaPoliticas
from evals.comum import carregar_casos, pausar, porcentagem


def avaliar(retriever: BuscaPoliticas, casos: list[dict]) -> tuple[int, float, list]:
    acertos, soma_rr, falhas = 0, 0.0, []
    for caso in casos:
        pergunta = caso.get("pergunta_busca", caso["mensagem"])
        secoes = [d.metadata["secao"] for d in retriever.invoke(pergunta)]

        if caso["secao_esperada"] in secoes:
            posicao = secoes.index(caso["secao_esperada"]) + 1
            acertos += 1
            soma_rr += 1 / posicao         
        else:
            falhas.append((caso["id"], secoes))
        pausar()
    return acertos, soma_rr / len(casos), falhas


def main() -> None:
    casos = carregar_casos(lambda c: "secao_esperada" in c)
    print(f"{len(casos)} casos com seção esperada\n")

    mini = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    bge = "BAAI/bge-reranker-v2-m3"
    configuracoes = [
        ("híbrida (sem rerank)", BuscaPoliticas(usar_rerank=False)),
        ("+ mMiniLM (corte 0,10)", BuscaPoliticas(usar_rerank=True, modelo_rerank=mini, min_score_rerank=0.10)),
        ("+ mMiniLM (sem corte)", BuscaPoliticas(usar_rerank=True, modelo_rerank=mini, min_score_rerank=0.0)),
        ("+ bge-reranker-v2-m3 (sem corte)", BuscaPoliticas(usar_rerank=True, modelo_rerank=bge, min_score_rerank=0.0)),
    ]

    resumo = []
    for nome, retriever in configuracoes:
        acertos, mrr, falhas = avaliar(retriever, casos)
        print(f"=== {nome} ===")
        print(f"hit rate@{retriever.k}  {porcentagem(acertos, len(casos))}")
        print(f"MRR         {mrr:.3f}")
        for id_, secoes in falhas:
            print(f"  não ok {id_}: veio {secoes}")
        print()
        resumo.append((nome, acertos, mrr))

    print("=== RESUMO ===")
    print(f"{'configuração':<34} {'hit rate':>9} {'MRR':>7}")
    for nome, acertos, mrr in resumo:
        print(f"{nome:<34} {acertos / len(casos):>9.0%} {mrr:>7.3f}")


if __name__ == "__main__":
    main()