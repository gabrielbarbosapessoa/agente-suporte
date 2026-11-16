from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from agente.llm import llm

from langchain_core.messages import BaseMessage


class Classificacao(BaseModel):

    intencao: Literal["politica", "pedido", "misto", "outro"] = Field(
        description=(
            "politica: dúvida sobre regras da loja (troca, garantia, frete, pagamento, cancelamento) "
            "que não depende de um pedido específico. "
            "pedido: quer saber dados de um pedido específico (status, rastreio, itens, valores). "
            "misto: quer saber se uma regra se aplica ao SEU pedido (ex.: 'posso devolver meu pedido 1?'). "
            "outro: saudação, agradecimento ou assunto fora do atendimento da loja."
        )
    )
    pedido_id: int | None = Field(
        default=None,
        description="Número do pedido, SOMENTE se o cliente informou na mensagem ou no histórico.",
    )
    email: str | None = Field(
        default=None,
        description="E-mail do cliente, SOMENTE se o cliente informou na mensagem ou no histórico.",
    )
    pergunta_reescrita: str = Field(
        description=(
            "A pergunta do cliente, completa e independente do histórico, SEM e-mail ou dados pessoais. "
            "Se a mensagem depender do histórico, reescreva-a completa. "
            "Se já for completa sozinha, mantenha as mesmas palavras."
        )
    )


PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é o roteador do atendimento da NovaByte, uma loja online de eletrônicos.
Classifique a última mensagem do cliente e extraia os dados pedidos.

Regras:
- Se a mensagem depender do histórico para fazer sentido, REESCREVA como uma pergunta completa.
  Exemplo:
    histórico: cliente perguntou se pode devolver um notebook por arrependimento
    mensagem: "e se for um fone?"
    pergunta_reescrita: "Posso devolver um fone de ouvido por arrependimento?"
- Se a mensagem já fizer sentido sozinha, mantenha as mesmas palavras, sem acrescentar nada.
- Remova e-mails e dados pessoais da pergunta reescrita (eles vão nos campos próprios).
- NUNCA invente número de pedido ou e-mail: se não foram informados, deixe vazio.

Histórico da conversa:
{historico}"""),
    ("human", "{mensagem}"),
])


def formatar_historico(historico: list[BaseMessage] | None) -> str:
    if not historico:
        return "(conversa nova)"
    return "\n".join(
        f"{'cliente' if m.type == 'human' else 'assistente'}: {m.content}" for m in historico
    )


def cadeia_roteador():
    return PROMPT | llm().with_structured_output(Classificacao)

def classificar(mensagem: str, historico: list[BaseMessage] | None = None) -> Classificacao:
    return cadeia_roteador().invoke({
        "mensagem": mensagem,
        "historico": formatar_historico(historico),
    })
if __name__ == "__main__":
    import sys

    mensagem = " ".join(sys.argv[1:]) or "Posso devolver meu pedido 1? Meu e-mail é ana.souza@example.com"
    print(classificar(mensagem).model_dump_json(indent=2))