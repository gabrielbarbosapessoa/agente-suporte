# Agente de suporte NovaByte

[![CI](https://github.com/gabrielbarbosapessoa/agente-suporte/actions/workflows/ci.yml/badge.svg)](https://github.com/gabrielbarbosapessoa/agente-suporte/actions/workflows/ci.yml)

Agente de atendimento ao cliente para um e-commerce de eletrônicos, construído como **Agentic RAG com LangGraph**. Ele responde dúvidas sobre as políticas da loja com citação das fontes, consulta pedidos no banco, calcula direitos do cliente com regras determinísticas e abre devoluções com **aprovação humana** quando o valor é alto. Tudo com guardrails em camadas, observabilidade no LangSmith e evals automatizados.

> A NovaByte é uma loja fictícia. Todos os clientes, pedidos e políticas deste repositório são inventados.

## Demonstração

**Pergunta sobre as políticas.** A resposta chega por streaming, cita os trechos usados e mostra as fontes. Embaixo, o caminho percorrido no grafo e os tempos:

![Pergunta sobre política](docs/politica.png)

**Memória da conversa.** Sem os dados do pedido, o agente pede. Na mensagem seguinte, só com o e-mail, ele recupera o número do pedido pelo histórico, consulta o banco e calcula o atraso em dias úteis com regras determinísticas:

![Memória e consulta de pedido](docs/memoria.png)

**Dados sensíveis.** O CPF é mascarado antes de chegar ao LLM, aos logs e ao banco:

![CPF mascarado](docs/dados_sensiveis.png)

**Prompt injection.** A tentativa é bloqueada no guardrail de entrada, sem nenhuma chamada ao LLM:

![Ataque bloqueado](docs/ataque.png)

**Observabilidade no LangSmith.** Cada nó do grafo com latência e tokens. Na entrada registrada, o CPF já aparece como `[CPF REMOVIDO]`:

![Trace no LangSmith](docs/langsmith.png)

## Destaques

- **Roteamento por intenção** com saída estruturada (Pydantic) e reescrita da pergunta usando o histórico: 95 a 100% de acerto no eval.
- **Busca híbrida** (vetorial HNSW + full-text) fundida por RRF em uma única query SQL, seguida de **rerank** com cross-encoder: 100% de acerto e MRR de 0,80.
- **Regras de negócio fora do LLM**: prazos, limites e atrasos são calculados em Python e entregues prontos ao modelo.
- **Human-in-the-loop**: reembolsos acima de R$ 1.000 pausam um grafo de aprovação (`interrupt`) até o financeiro decidir.
- **Guardrails em camadas**: máscara de PII, regex e o classificador **Llama Prompt Guard 2** na entrada; proteção contra IDOR no acesso aos dados; limpeza de PII na saída.
- **API FastAPI com streaming (SSE)**, tela de chat, chave de API, rate limit e limite diário de uso.
- **Observabilidade e qualidade**: traces no LangSmith, evals de roteador, retrieval, respostas (LLM como juiz) e guardrails, e CI com testes, bandit, pip-audit e gitleaks.

## Arquitetura

```mermaid
flowchart TD
    A[Mensagem do cliente] --> B[Guardrail de entrada<br/>máscara de PII · regex · Prompt Guard]
    B -->|bloqueada| X[Resposta padrão]
    B --> C[Roteador<br/>Gemini + saída estruturada]
    C -->|outro / faltam dados| F[Resposta fixa]
    C -->|política| D[Busca híbrida + rerank]
    C -->|pedido| E[Consulta do pedido<br/>SQL + regras]
    C -->|misto| D
    D -->|misto| E
    C -->|devolução| G[Solicitação de devolução]
    G -->|acima de R$ 1.000| H[Grafo de aprovação<br/>interrupt / resume]
    D --> R[Responder<br/>Gemini com contexto e citações]
    E --> R
    R --> S[Guardrail de saída]
    S --> Z[Resposta ao cliente]
    F --> Z
    G --> Z
```

O estado de cada conversa é salvo no Postgres por `thread_id` (checkpointer do LangGraph). O mesmo banco guarda pedidos, vetores das políticas, memória das conversas e solicitações de devolução.

## Stack

| Camada | Tecnologia |
|---|---|
| Orquestração | LangGraph, LangChain (LCEL) |
| LLM e embeddings | Gemini (`gemini-embedding-001`, 768 dimensões) |
| Banco | PostgreSQL 17 + pgvector (HNSW) + full-text (`tsvector`) |
| Rerank | `BAAI/bge-reranker-v2-m3` (cross-encoder local) |
| Guardrail | `meta-llama/Llama-Prompt-Guard-2-86M` (classificador local) |
| API | FastAPI, SSE, uvicorn |
| Observabilidade | LangSmith |
| Evals | conjunto próprio + DeepEval (LLM como juiz) |
| Infra | Docker, Docker Compose, GitHub Actions |

## Resultados dos evals

**Roteador** (21 casos): 95 a 100% de acerto na intenção, 100% na extração de pedido e e-mail.

**Retrieval** (14 casos com seção esperada):

| Configuração | Acerto (top 4) | MRR |
|---|---|---|
| Híbrida, sem rerank | 100% | 0,774 |
| Híbrida + mMiniLM, com corte de score | 71% | 0,661 |
| Híbrida + mMiniLM, sem corte | 86% | 0,756 |
| **Híbrida + bge-reranker-v2-m3** | **100%** | **0,804** |

O primeiro reranker testado **piorava** o resultado. O eval mostrou isso, e a troca de modelo foi decidida pelos números.

**Guardrail de entrada** (ataques que o regex não detecta e mensagens normais parecidas com ataques):

| | Ataques detectados | Falsos positivos |
|---|---|---|
| Só regex | 0/8 | 0/8 |
| Regex + Prompt Guard | 7/8 | 1/8 |

Latência do Prompt Guard: cerca de 87 ms por mensagem, em CPU. Os ataques que passam são de engenharia social ("sou administrador"), e estão cobertos pelas camadas seguintes: o acesso a pedidos exige número e e-mail do dono, e reembolsos passam por regras e aprovação humana.

**Respostas** (LLM como juiz, com fidelidade, relevância e correção): todos os casos aprovados, exceto um falso negativo do juiz, documentado.

**Custo e latência** (LangSmith): cerca de 1,6 mil tokens e US$ 0,001 por pergunta respondida com contexto. Caminhos com mensagem fixa usam só o roteador (cerca de 350 tokens), e mensagens bloqueadas não chamam nenhum LLM. Com os modelos já carregados, uma resposta completa leva cerca de 6 s, e o streaming mostra o primeiro token bem antes disso.

## Decisões técnicas

- **Roteador em vez de agente ReAct.** O domínio tem poucos caminhos e bem definidos. Um fluxo explícito é mais previsível, mais barato e mais fácil de avaliar do que deixar o LLM escolher ferramentas livremente.
- **Regras em Python, não no prompt.** Prazos e valores são calculados deterministicamente e testados com pytest. O LLM só explica o resultado.
- **Mensagens fixas para ações.** Abrir devolução, pedir dados ou recusar não passa por geração de texto: o resultado é exato e não gasta tokens.
- **Aprovação humana em um grafo separado.** O cliente não fica travado esperando; a decisão do financeiro aparece depois na conversa dele.
- **Memória por janela.** O roteador recebe as últimas 6 mensagens. É mais simples e previsível que um resumo, e suficiente para conversas de atendimento.
- **Streaming e guardrail de saída.** Os tokens chegam antes da checagem final. O evento de fim traz a resposta já verificada, que substitui o texto exibido. Como o LLM nunca recebe dados de outros clientes, o risco residual é baixo.
- **Modelos com versão fixada.** Reranker e Prompt Guard são baixados por hash de commit, o que protege contra alterações no repositório de origem e mantém os evals reproduzíveis.

## Segurança (OWASP Top 10 para LLMs)

| Risco | Mitigação |
|---|---|
| LLM01 Prompt injection | regex + Prompt Guard 2 na entrada; o prompt instrui a ignorar instruções vindas do contexto |
| LLM02 Vazamento de dados sensíveis | CPF e cartão mascarados antes do LLM e do LangSmith; consulta de pedido exige número e e-mail (IDOR); limpeza de PII na saída |
| LLM06 Agência excessiva | o LLM não executa ações; devolução segue regras determinísticas e aprovação humana |
| LLM10 Consumo sem limite | rate limit por IP e limite diário global na API |

No CI: **bandit** (código), **pip-audit** (dependências) e **gitleaks** (segredos no histórico do git).

## Como rodar

Pré-requisitos: Docker e uma chave gratuita da API do Gemini.

```bash
git clone https://github.com/gabrielbarbosapessoa/agente-suporte.git
cd agente-suporte
cp .env.example .env
```

Preencha no `.env` ao menos `GOOGLE_API_KEY`, `POSTGRES_PASSWORD` e `API_KEY`. O Prompt Guard exige aceitar a licença do modelo no Hugging Face e um `HF_TOKEN`; sem isso, use `PROMPT_GUARD_ATIVO=false`.

```bash
docker compose up -d --build
docker compose exec app python -m agente.rag.ingestao
```

Na primeira subida, o banco é criado e populado automaticamente, e os modelos locais são baixados (alguns minutos). Acompanhe com `docker compose logs -f app` até aparecer `Application startup complete`.

Depois, **abra no navegador**:

```
http://localhost:8000
```

É a tela de chat. As sugestões na tela mostram os principais caminhos do agente, e o rodapé traz pedidos de teste (por exemplo, pedido 1 com o e-mail `ana.souza@example.com`). Embaixo de cada resposta aparecem as fontes, o caminho percorrido no grafo e os tempos.

Para usar a API diretamente, a documentação interativa fica em `http://localhost:8000/docs`.

Aprovação de reembolsos pendentes:

```bash
docker compose exec app python -m agente.fluxo.aprovacao listar
docker compose exec app python -m agente.fluxo.aprovacao aprovar 1
```

### Testes e evals (ambiente local)

```bash
pip install -r requirements-dev.txt
pytest
python -m evals.eval_roteador
python -m evals.eval_retrieval
python -m evals.eval_guardrails
python -m evals.eval_respostas
```

## Estrutura

```
agente/
  config.py         configuração lida do .env
  dominio/          modelos e regras de negócio puras
  repositorios/     acesso ao banco (SQL parametrizado)
  rag/              ingestão, busca híbrida e rerank
  fluxo/            roteador, resposta, grafo principal e grafo de aprovação
  seguranca/        guardrails e Prompt Guard
  infra/            pool de conexões, LLM e checkpointer
  interfaces/       API, tela de chat e chat de terminal
data/politicas/     políticas da loja em Markdown
db/                 schema e dados iniciais
evals/              datasets e scripts de avaliação
tests/              testes unitários e de integração
```

## Limitações e próximos passos

- Os datasets de eval são pequenos (21 casos no agente, 16 nos guardrails): os números indicam direção, não estatística.
- O Prompt Guard não detecta engenharia social, e tem um falso positivo conhecido, ambos registrados como `xfail` nos testes.

---

Feito por [Gabriel Barbosa Pessoa](https://github.com/gabrielbarbosapessoa).
