import json
import os
import time
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

ARQUIVO_CASOS = Path(__file__).parent / "casos.json"
PAUSA = float(os.getenv("EVAL_PAUSA", "4"))  


def carregar_casos(filtro=None) -> list[dict]:
    casos = json.loads(ARQUIVO_CASOS.read_text(encoding="utf-8"))
    return [c for c in casos if filtro is None or filtro(c)]


def historico_como_mensagens(caso: dict) -> list:
    tipos = {"cliente": HumanMessage, "assistente": AIMessage}
    return [tipos[autor](content=texto) for autor, texto in caso.get("historico", [])]


def pausar() -> None:
    time.sleep(PAUSA)


def porcentagem(acertos: int, total: int) -> str:
    return f"{acertos}/{total} ({acertos / total:.0%})" if total else "0/0"