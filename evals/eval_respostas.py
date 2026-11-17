"""Eval de ponta a ponta: roda o AGENTE inteiro e avalia a resposta final.

Duas camadas:
  1. checagens de texto (grátis): deve_conter / nao_deve_conter
  2. LLM como juiz (DeepEval): fidelidade, relevância e correção

    python -m evals.eval_respostas
    $env:EVAL_LIMITE="3"; python -m evals.eval_respostas   ← só os 3 primeiros casos
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path


os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
os.environ.setdefault("LANGSMITH_PROJECT", "agente-suporte-evals")
os.environ.setdefault("DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE", "300")
os.environ.setdefault("DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE", "1200")

from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval  
from deepeval.models import GeminiModel  
from deepeval.test_case import LLMTestCase, SingleTurnParams  
from langchain_core.messages import HumanMessage  

from agente.config import LLM_MODEL  
from agente.fluxo.grafo import criar_grafo  
from evals.comum import carregar_casos, historico_como_mensagens, pausar  

JUIZ_MODELO = os.getenv("EVAL_JUIZ_MODEL", LLM_MODEL)
LIMITE = int(os.getenv("EVAL_LIMITE", "0")) or None
IDS = [i.strip() for i in os.getenv("EVAL_IDS", "").split(",") if i.strip()]
SEM_JUIZ = os.getenv("EVAL_SEM_JUIZ") == "1"
PASTA_RESULTADOS = Path(__file__).parent / "resultados"


def criar_metricas() -> dict:
    juiz = GeminiModel(model=JUIZ_MODELO, api_key=os.environ["GOOGLE_API_KEY"])
    opcoes = {"model": juiz, "async_mode": False}
    return {
  
        "fidelidade": FaithfulnessMetric(threshold=0.8, include_reason=False, **opcoes),
   
        "relevancia": AnswerRelevancyMetric(threshold=0.7, include_reason=False, **opcoes),
     
        "correcao": GEval(
            name="Correção",
            criteria=(
                "A resposta real transmite as mesmas informações essenciais da resposta esperada "
                "(números, prazos, sim ou não, próximos passos). Diferenças de redação não importam; "
                "informação errada, contraditória ou faltando importa."
            ),
            evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT,
                               SingleTurnParams.EXPECTED_OUTPUT],
            threshold=0.7,
            **opcoes,
        ),
    }


def medir(metrica, teste, tentativas: int = 3) -> None:
    """Roda a métrica; se a API devolver 429 (limite por minuto), espera e tenta de novo."""
    for tentativa in range(1, tentativas + 1):
        try:
            metrica.measure(teste)
            return
        except Exception as erro:
            limite = any(t in str(erro) for t in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"))
            if not limite or tentativa == tentativas:
                raise
            print(f"    limite da API atingido, esperando 60s (tentativa {tentativa}/{tentativas})...")
            time.sleep(60)


def contem(texto: str, termo: str) -> bool:
    return termo.lower() in texto.lower()


def avaliar_caso(grafo, metricas: dict, caso: dict) -> dict:
    mensagens = historico_como_mensagens(caso) + [HumanMessage(content=caso["mensagem"])]
    estado = grafo.invoke({"mensagens": mensagens})
    resposta = estado["resposta"]

    contexto = [d.page_content for d in estado.get("trechos") or []]
    if estado.get("dados_pedido"):
        contexto.append(estado["dados_pedido"])


    faltando = [t for t in caso.get("deve_conter", []) if not contem(resposta, t)]
    vazou = [t for t in caso.get("nao_deve_conter", []) if contem(resposta, t)]


    notas = {}
    if "resposta_esperada" in caso:
        teste = LLMTestCase(
            input=caso["mensagem"],
            actual_output=resposta,
            expected_output=caso["resposta_esperada"],
            retrieval_context=contexto or None,
        )
        for nome, metrica in metricas.items():
            if nome == "fidelidade" and not contexto:
                continue 
            if nome == "relevancia" and caso.get("sem_relevancia"):
                continue  
            try:
                medir(metrica, teste)
                notas[nome] = {"nota": round(metrica.score, 2), "passou": metrica.is_successful()}
            except Exception as erro:
                notas[nome] = {"nota": None, "passou": None, "erro": str(erro)[:120]}

    reprovou = bool(faltando or vazou) or any(n["passou"] is False for n in notas.values())
    erro_juiz = any(n["passou"] is None for n in notas.values())
    status = "FALHOU" if reprovou else ("INCONCLUSIVO" if erro_juiz else "ok")

    return {
        "id": caso["id"],
        "resposta": resposta,
        "rota": estado["classificacao"].intencao,
        "contexto": contexto,
        "faltando": faltando,
        "vazou": vazou,
        "notas": notas,
        "status": status,
    }


def main() -> None:
    casos = carregar_casos(lambda c: not c.get("acao") and (
        "resposta_esperada" in c or "deve_conter" in c or "nao_deve_conter" in c)
        and (not IDS or c["id"] in IDS))[:LIMITE]
    grafo = criar_grafo() 
    metricas = {} if SEM_JUIZ else criar_metricas()
    print(f"{len(casos)} casos | juiz: {'(desligado)' if SEM_JUIZ else JUIZ_MODELO}\n")

    resultados = []
    for i, caso in enumerate(casos, start=1):
        r = avaliar_caso(grafo, metricas, caso)
        resultados.append(r)
        notas = "  ".join(f"{k}={v['nota']}" for k, v in r["notas"].items())
        print(f"[{i}/{len(casos)}] {r['status']} {r['id']}  {notas}")
        erros = {v["erro"] for v in r["notas"].values() if v.get("erro")}
        for erro in erros:
            print(f"    erro do juiz: {erro}")
        pausar()

    total = len(resultados)
    print("\n=== RESPOSTAS (ponta a ponta) ===")
    for status in ("ok", "FALHOU", "INCONCLUSIVO"):
        print(f"{status:<21} {sum(r['status'] == status for r in resultados)}/{total}")
    print(f"checagens de texto    {sum(not r['faltando'] and not r['vazou'] for r in resultados)}/{total}")
    for nome in ("fidelidade", "relevancia", "correcao"):
        notas = [r["notas"][nome] for r in resultados if nome in r["notas"]]
        validas = [n["nota"] for n in notas if n["nota"] is not None]
        if notas:
            media = sum(validas) / len(validas) if validas else 0
            aprovadas = sum(n["passou"] is True for n in notas)
            print(f"{nome:<21} média {media:.2f} | passou {aprovadas}/{len(validas)} avaliados"
                  f" | {len(notas) - len(validas)} erros do juiz")

    falhas = [r for r in resultados if r["status"] != "ok"]
    if falhas:
        print("\nFalhas e inconclusivos:")
        for r in falhas:
            print(f"- [{r['status']}] {r['id']}: faltando={r['faltando']} vazou={r['vazou']} "
                  f"notas={ {k: v['nota'] for k, v in r['notas'].items()} }")
            print(f"    resposta: {r['resposta'][:160]}")

   
    PASTA_RESULTADOS.mkdir(exist_ok=True)
    arquivo = PASTA_RESULTADOS / f"respostas-{datetime.now():%Y%m%d-%H%M}.json"
    arquivo.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResultados salvos em {arquivo}")


if __name__ == "__main__":
    main()
