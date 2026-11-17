import json
import os
import time
from pathlib import Path

os.environ.setdefault("LANGSMITH_PROJECT", "agente-suporte-evals")

from agente.config import PROMPT_GUARD_LIMIAR
from agente.seguranca.guardrails import _INJECAO
from agente.seguranca.prompt_guard import probabilidade_de_ataque
from evals.comum import porcentagem

CASOS = json.loads((Path(__file__).parent / "casos_guardrails.json").read_text(encoding="utf-8"))


def main() -> None:
    probabilidade_de_ataque("aquecimento")
    resultados = []
    tempos = []

    for caso in CASOS:
        regex = bool(_INJECAO.search(caso["mensagem"]))
        inicio = time.perf_counter()
        prob = probabilidade_de_ataque(caso["mensagem"])
        tempos.append(time.perf_counter() - inicio)
        modelo = prob >= PROMPT_GUARD_LIMIAR
        resultados.append((caso["ataque"], regex, regex or modelo))
        tipo = "ATAQUE" if caso["ataque"] else "normal"
        print(f"{tipo:6}  regex={'S' if regex else '-'}  modelo={prob:.2f}  {caso['mensagem'][:60]}")

    ataques = [r for r in resultados if r[0]]
    normais = [r for r in resultados if not r[0]]

    print(f"\nLimiar: {PROMPT_GUARD_LIMIAR}")
    print(f"{'':16}{'ataques pegos':>18}{'falsos positivos':>20}")
    for nome, i in [("só regex", 1), ("regex + modelo", 2)]:
        pegos = sum(r[i] for r in ataques)
        falsos = sum(r[i] for r in normais)
        print(f"{nome:16}{porcentagem(pegos, len(ataques)):>18}{porcentagem(falsos, len(normais)):>20}")
    print(f"\nLatência do modelo: média {sum(tempos) / len(tempos) * 1000:.0f} ms, máx {max(tempos) * 1000:.0f} ms")


if __name__ == "__main__":
    main()