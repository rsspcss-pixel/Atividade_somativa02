# Atividade Somativa 02 — Assistente de Negociação

Projeto acadêmico com **Flowise** (agentes de IA), **Streamlit** (interface de chat) e APIs auxiliares (ML, DeepEval).

## URLs locais (após subir o stack)

| Serviço | URL |
|---------|-----|
| **Streamlit (chat)** | http://localhost:8502 |
| **Flowise (configurar agentes)** | http://localhost:3000 |
| ML API | http://localhost:8503 |

## Início rápido (Docker)

```powershell
cd Flowise/docker
.\setup.ps1              # cria .env a partir dos exemplos
.\start-stack.ps1        # LM Studio + Docker Compose + bootstrap do agentflow
```

Sem LM Studio (só testar interface, chat pode não responder ao LLM):

```powershell
.\start-stack.ps1 -SkipLmStudio
```

## Streamlit Cloud

1. Faça push deste repositório para o GitHub.
2. Acesse [share.streamlit.io](https://share.streamlit.io) e conecte o repositório `Atividade_somativa02`.
3. Configure:
   - **Main file path:** `Flowise/docker/streamlit/app.py`
   - **Branch:** `main`
4. Em **Settings → Secrets**, cole (com sua chave OpenAI):

```toml
CHAT_BACKEND = "openai"
OPENAI_API_KEY = "sk-..."
OPENAI_CHAT_MODEL = "gpt-4o-mini"
CHROMA_ENABLED = "0"
```

Guia completo: [Flowise/docs/deploy-streamlit-cloud.md](Flowise/docs/deploy-streamlit-cloud.md)

```powershell
cd Flowise/docker
.\deploy-streamlit-cloud.ps1 -OpenCloud
```

## Estrutura principal

```
Flowise/
  docker/
    setup.ps1                 # prepara .env
    start-stack.ps1           # sobe stack completo
    bootstrap-flowise.ps1     # instala agentflow no banco Flowise
    streamlit/app.py          # app Streamlit (chat)
    flowise/
      install_negociacao_agent.py
      tools/*.json
  docs/
    seguranca-llm.md
    guardrails-demo.md
```

## Chat não responde?

1. Confirme que o Flowise está no ar: http://localhost:3000/api/v1/ping
2. Execute o bootstrap: `.\bootstrap-flowise.ps1`
3. No Flowise, crie credencial **OpenAI API** apontando para o LM Studio:
   - Base URL: `http://host.docker.internal:1234/v1`
   - API Key: `lm-studio`
4. Verifique `streamlit/.env`:
   - `FLOWISE_API_URL` com o ID do chatflow correto
   - `FLOWISE_API_TOKEN=local-dev` (se o chatflow não tiver API key atribuída)

## Dataset e Machine Learning

Na pasta `Flowise/docker/streamlit`:

```powershell
python demo_assets.py          # gera CSV (se faltar) + treina modelo ML
python seed_demo_data.py --train-ml
```

O app prepara automaticamente dataset e modelo na inicialização. O classificador fica em `ml/models/risco_renegociacao.pkl`.

## Documentação adicional

- [docs/deploy-streamlit-cloud.md](Flowise/docs/deploy-streamlit-cloud.md) — deploy no share.streamlit.io
- [docs/deploy-flowise-public.md](Flowise/docs/deploy-flowise-public.md) — Flowise publico (opcional)
- [docs/seguranca-llm.md](Flowise/docs/seguranca-llm.md) — segurança e guardrails
- [docs/guardrails-demo.md](Flowise/docs/guardrails-demo.md) — demonstração antes/depois
