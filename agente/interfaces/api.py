import json

from fastapi.responses import RedirectResponse, StreamingResponse
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path
from fastapi.responses import RedirectResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from agente import config as cfg
from agente.config import DOCS_ATIVO, PROMPT_GUARD_ATIVO, RERANKER_MODEL
from agente.fluxo.grafo import criar_grafo
from agente.infra.memoria import checkpointer
from agente.rag.rerank import _modelo as carregar_reranker
from agente.interfaces.protecao import exigir_chave, limitar_uso
from agente.seguranca.guardrails import TAMANHO_MAXIMO, mascarar_dados_sensiveis
from agente.seguranca.prompt_guard import carregar_prompt_guard

ThreadId = Annotated[str, Path(pattern=r"^sessao-[0-9a-f]{32}$")]


class NovaMensagem(BaseModel):
    mensagem: str = Field(min_length=1, max_length=TAMANHO_MAXIMO)


class Fonte(BaseModel):
    documento: str
    secao: str


class Resposta(BaseModel):
    thread_id: str
    resposta: str
    caminho: list[str]
    fontes: list[Fonte]


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    if not cfg.API_KEY:
        raise RuntimeError("Defina API_KEY no .env antes de subir a API")
    carregar_reranker(RERANKER_MODEL)
    if PROMPT_GUARD_ATIVO:
        carregar_prompt_guard()
    app.state.agente = criar_grafo(checkpointer())
    yield


app = FastAPI(
    title="Agente de suporte NovaByte",
    lifespan=ciclo_de_vida,
    docs_url="/docs" if DOCS_ATIVO else None,
    redoc_url=None,
    openapi_url="/openapi.json" if DOCS_ATIVO else None,
)


def _config(thread_id: str) -> dict:
    return {
        "configurable": {"thread_id": thread_id},
        "run_name": "atendimento",
        "tags": ["api"],
        "metadata": {"thread_id": thread_id},
    }


@app.get("/", include_in_schema=False)
def raiz():
    return RedirectResponse("/docs") if DOCS_ATIVO else {"servico": "agente-suporte"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/conversas", status_code=201, dependencies=[Depends(exigir_chave)])
def nova_conversa() -> dict:
    return {"thread_id": f"sessao-{uuid.uuid4().hex}"}


@app.post(
    "/conversas/{thread_id}/mensagens",
    response_model=Resposta,
    dependencies=[Depends(exigir_chave), Depends(limitar_uso)],
)
def enviar_mensagem(thread_id: ThreadId, corpo: NovaMensagem) -> Resposta:
    agente = app.state.agente
    config = _config(thread_id)
    entrada = {"mensagens": [HumanMessage(content=mascarar_dados_sensiveis(corpo.mensagem))]}

    caminho = []
    for passo in agente.stream(entrada, config, stream_mode="updates"):
        caminho.extend(passo)

    estado = agente.get_state(config).values
    fontes = []
    if "responder" in caminho:
        fontes = [
            Fonte(documento=d.metadata["documento"], secao=d.metadata["secao"])
            for d in estado.get("trechos") or []
        ]
    return Resposta(thread_id=thread_id, resposta=estado["resposta"], caminho=caminho, fontes=fontes)


@app.get("/conversas/{thread_id}", dependencies=[Depends(exigir_chave)])
def historico(thread_id: ThreadId) -> dict:
    estado = app.state.agente.get_state(_config(thread_id)).values
    if not estado.get("mensagens"):
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    autores = {"human": "cliente", "ai": "assistente"}
    mensagens = [{"autor": autores[m.type], "texto": m.content} for m in estado["mensagens"]]
    return {"thread_id": thread_id, "mensagens": mensagens}

def _evento(tipo: str, dados: dict) -> str:
    return f"event: {tipo}\ndata: {json.dumps(dados, ensure_ascii=False)}\n\n"


def _texto(pedaco) -> str:
    if isinstance(pedaco.content, str):
        return pedaco.content
    return "".join(p.get("text", "") for p in pedaco.content if isinstance(p, dict))


@app.post(
    "/conversas/{thread_id}/mensagens/stream",
    dependencies=[Depends(exigir_chave), Depends(limitar_uso)],
)
def enviar_mensagem_stream(thread_id: ThreadId, corpo: NovaMensagem) -> StreamingResponse:
    agente = app.state.agente
    config = _config(thread_id)
    entrada = {"mensagens": [HumanMessage(content=mascarar_dados_sensiveis(corpo.mensagem))]}

    def gerar():
        caminho = []
        try:
            for modo, dados in agente.stream(entrada, config, stream_mode=["updates", "messages"]):
                if modo == "updates":
                    for no in dados:
                        caminho.append(no)
                        yield _evento("passo", {"no": no})
                else:
                    pedaco, meta = dados
                    texto = _texto(pedaco)
                    if meta.get("langgraph_node") == "responder" and texto:
                        yield _evento("token", {"texto": texto})

            estado = agente.get_state(config).values
            fontes = []
            if "responder" in caminho:
                fontes = [
                    {"documento": d.metadata["documento"], "secao": d.metadata["secao"]}
                    for d in estado.get("trechos") or []
                ]
            yield _evento("fim", {"resposta": estado["resposta"], "caminho": caminho, "fontes": fontes})
        except Exception:
            yield _evento("erro", {"detalhe": "Não foi possível processar sua mensagem agora."})

    return StreamingResponse(gerar(), media_type="text/event-stream")