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
- **Deploy na AWS com Terraform**: ECS Fargate atrás de um ALB, RDS PostgreSQL com pgvector em sub-redes isoladas, segredos no Secrets Manager e estado remoto no S3.
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
| Infra | Docker, Docker Compose, GitHub Actions, Terraform |
| Nuvem | AWS: VPC, ALB, ECS Fargate, RDS, ECR, Secrets Manager, CloudWatch, S3 |

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

## Deploy na AWS

A aplicação foi publicada na AWS com toda a infraestrutura escrita em **Terraform** (pasta `infra/`), criada com `terraform apply`, testada e removida com `terraform destroy` na mesma sessão.

```mermaid
flowchart LR
    U[Internet] -->|HTTP 80| ALB
    subgraph VPC["VPC 10.0.0.0/16, duas zonas de disponibilidade"]
        subgraph PUB["Sub-redes públicas"]
            ALB[Application Load Balancer] -->|8000| ECS[ECS Fargate<br/>container do agente]
        end
        subgraph DB["Sub-redes do banco, sem rota para a internet"]
            RDS[(RDS PostgreSQL 17<br/>+ pgvector)]
        end
        ECS -->|5432| RDS
    end
    ECS -->|443| EXT[Gemini · Hugging Face · LangSmith]
    ECR[ECR] -.imagem.-> ECS
    SM[Secrets Manager] -.segredos.-> ECS
    ECS -.logs.-> CW[CloudWatch Logs]
```

| Peça | Papel |
|---|---|
| **VPC** em 2 zonas | sub-redes públicas para o balanceador e o container; sub-redes do banco sem nenhuma rota para fora |
| **ALB** | endereço público, health check em `/health` e distribuição entre containers |
| **ECS Fargate** | roda o container sem servidor para gerenciar, com rollback automático se um deploy falhar |
| **RDS PostgreSQL 17** | banco gerenciado, criptografado, inacessível pela internet |
| **ECR** | registro privado da imagem, com scan de vulnerabilidades a cada envio |
| **Secrets Manager** | chaves da aplicação e senha do banco, injetadas no container em tempo de execução |
| **CloudWatch Logs** | logs do container com retenção de 7 dias |
| **S3** (bootstrap) | estado remoto do Terraform, versionado, criptografado e com trava |

**Segurança na nuvem**

- **Security groups encadeados**: a internet só alcança o ALB (porta 80), o container só aceita o ALB (8000) e o banco só aceita o container (5432). As regras referenciam outros security groups, não IPs.
- **Nenhum segredo na imagem nem no código.** A senha do banco é gerada pelo próprio RDS (`manage_master_user_password`) e nunca aparece no Terraform. As chaves da aplicação vão do `.env` local direto para o Secrets Manager por um script, sem passar pelo estado do Terraform.
- **Menor privilégio**: uma role de execução que só lê os dois segredos do projeto e baixa a imagem, e uma role da tarefa separada para o container.
- **IP real do cliente**: o uvicorn confia no cabeçalho `X-Forwarded-For` apenas vindo da VPC, para o rate limit enxergar o usuário, e não o balanceador.
- **Modelos com versão fixada** por hash de commit, baixados do Hugging Face na inicialização.

**Como foi feito o deploy**

```bash
cd infra/bootstrap && terraform apply          # uma vez: bucket do estado remoto
cd .. && terraform apply -var="tarefas=0"      # infraestrutura sem container
python infra/enviar_segredos.py                # chaves do .env para o Secrets Manager
docker build -t <ecr>:v1 . && docker push <ecr>:v1
terraform apply                                # liga o container
terraform destroy                              # remove tudo ao final
```

Na primeira inicialização, o container cria as tabelas no RDS vazio, faz a ingestão das políticas e carrega os modelos. Do primeiro script SQL ao servidor pronto, levou menos de 1 minuto:

```
Apply complete! Resources: 38 added, 0 changed, 0 destroyed.

Outputs:
cluster     = "novabyte-cluster"
ecr         = "<conta>.dkr.ecr.us-east-1.amazonaws.com/novabyte-app"
url         = "http://novabyte-alb-<id>.us-east-1.elb.amazonaws.com"
```

Ao final da sessão, tudo foi removido com um comando:

```
Destroy complete! Resources: 38 destroyed.
```

![Chat rodando na AWS](docs/aws/05-chat-aws.png)

![Mapa da VPC](docs/aws/02-vpc.png)

![Serviço no ECS com o alvo saudável no balanceador](docs/aws/03-ecs.png)

![Logs da inicialização no CloudWatch](docs/aws/07-logs.png)

![Banco no RDS](docs/aws/06-rds.png)

**Latência em produção, medida no LangSmith**

![Trace na AWS](docs/aws/08-langsmith.png)

| Etapa | Local (PC) | AWS (Fargate, 2 vCPU) |
|---|---|---|
| Guardrail (Prompt Guard) | ~0,3 s | 0,27 s |
| Roteador (Gemini) | 1,0 s | 6,7 s |
| Rerank (CPU) | rápido com o modelo aquecido | 8,3 s |
| Resposta (Gemini) | 0,6 s | 6,6 s |

Dois gargalos com causas diferentes: o **rerank** é limitado pela CPU da tarefa, e as chamadas ao **Gemini** variaram do lado do provedor (plano gratuito, sem garantia de latência), já que a rede da AWS não explica um aumento dessa ordem. O CloudWatch mostrou uso de memória de cerca de 16% dos 8 GB e pico de CPU de 49% na inicialização. Próximos ajustes: mais vCPU ou menos candidatos para o rerank, validados pelo eval de retrieval, e uma tarefa com menos memória.

**Custo e decisões**

A infraestrutura custa cerca de US$ 0,17 por hora e foi destruída ao final da sessão. Para manter a demo simples e barata, ficaram de fora, como evoluções para produção:

- **NAT Gateway e sub-redes privadas para o app**: hoje o container fica numa sub-rede pública, protegido pelo security group que só aceita o ALB.
- **EFS** para guardar os modelos entre execuções, em vez de baixá-los a cada inicialização.
- **HTTPS** com domínio próprio, Route 53 e certificado do ACM.
- **Deploy contínuo** pelo GitHub Actions com OIDC, sem chaves da AWS guardadas no GitHub.
- **Região sa-east-1** em produção, por residência de dados (LGPD); na demo, us-east-1 por custo.

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
```

Na primeira subida, o banco é criado e populado, as políticas são indexadas e os modelos locais são baixados, tudo automaticamente (alguns minutos). Acompanhe com `docker compose logs -f app` até aparecer `Application startup complete`.

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
infra/              Terraform da AWS (bootstrap do estado remoto e arquitetura)
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
