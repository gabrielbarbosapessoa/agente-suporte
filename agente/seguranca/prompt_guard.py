from functools import lru_cache

from langsmith import traceable

from agente.config import PROMPT_GUARD_MODEL


@lru_cache(maxsize=1)
def carregar_prompt_guard(nome: str = PROMPT_GUARD_MODEL):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(nome)
    modelo = AutoModelForSequenceClassification.from_pretrained(nome)
    modelo.eval()
    return tokenizer, modelo


@traceable(name="prompt_guard", run_type="chain")
def probabilidade_de_ataque(texto: str, nome: str = PROMPT_GUARD_MODEL) -> float:
    import torch

    tokenizer, modelo = carregar_prompt_guard(nome)
    entradas = tokenizer(texto, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        logits = modelo(**entradas).logits
    return torch.softmax(logits, dim=-1)[0, 1].item()