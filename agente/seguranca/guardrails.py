
import re
from dataclasses import dataclass

TAMANHO_MAXIMO = 1000 


_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_CARTAO = re.compile(r"\b\d(?:[ -]?\d){12,18}\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _luhn_valido(numero: str) -> bool:
    """Algoritmo de Luhn: o dígito verificador que todo cartão de crédito tem."""
    digitos = [int(d) for d in numero][::-1]
    soma = 0
    for i, d in enumerate(digitos):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        soma += d
    return soma % 10 == 0


def mascarar_dados_sensiveis(texto: str) -> str:
    """Troca números de cartão e CPF por marcadores, antes de qualquer coisa ver o texto."""
    def cartao(m: re.Match) -> str:
        digitos = re.sub(r"\D", "", m.group())
        return "[CARTÃO REMOVIDO]" if _luhn_valido(digitos) else m.group()

    texto = _CARTAO.sub(cartao, texto)
    return _CPF.sub("[CPF REMOVIDO]", texto)



_PADROES_INJECAO = [
    r"ignor\w*\s+(todas\s+)?(as\s+)?(suas\s+)?(instru|regras|orienta)",
    r"ignore\s+(all\s+)?(previous|prior|the)\s+instructions",
    r"esque[cç]a\s+(todas\s+)?(as\s+)?(suas\s+)?(instru|regras)",
    r"(revele|mostre|me\s+(d[eê]|passe))\s+(o\s+)?(seu\s+)?(prompt|instru[cç][oõ]es\s+do\s+sistema)",
    r"system\s*prompt",
    r"voc[eê]\s+agora\s+[eé]\b",
    r"(liste|mostre|me\s+passe)\s+(os\s+)?(e-?mails|dados|cpfs?)\s+de\s+todos",
]
_INJECAO = re.compile("|".join(_PADROES_INJECAO), re.IGNORECASE)


@dataclass
class ResultadoEntrada:
    texto: str              
    bloqueado: bool
    motivo: str | None = None


def verificar_entrada(texto: str) -> ResultadoEntrada:
    mascarado = mascarar_dados_sensiveis(texto)
    if len(texto) > TAMANHO_MAXIMO:
        return ResultadoEntrada(mascarado, True, "mensagem_longa")
    if _INJECAO.search(texto):
        return ResultadoEntrada(mascarado, True, "prompt_injection")
    return ResultadoEntrada(mascarado, False)


def verificar_saida(resposta: str, email_cliente: str | None) -> tuple[str, list[str]]:
    """Devolve a resposta segura e a lista de problemas encontrados."""
    problemas = []

    emails_estranhos = {
        e for e in _EMAIL.findall(resposta)
        if not email_cliente or e.lower() != email_cliente.lower()
    }
    if emails_estranhos:
        problemas.append("email_de_terceiro")
        for e in emails_estranhos:
            resposta = resposta.replace(e, "[E-MAIL REMOVIDO]")

    mascarada = mascarar_dados_sensiveis(resposta)
    if mascarada != resposta:
        problemas.append("dado_sensivel")
    return mascarada, problemas
