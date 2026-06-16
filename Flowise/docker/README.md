# Flowise Docker Hub Image

Starts Flowise from [DockerHub Image](https://hub.docker.com/r/flowiseai/flowise)

## Usage

1. Prepare environment files (first run):

    ```powershell
    .\setup.ps1
    ```

2. Configure Streamlit integration: `setup.ps1` copies `streamlit/.env.example` → `streamlit/.env` with `FLOWISE_API_TOKEN=local-dev` for local dev.

3. Start the stack:

    ```powershell
    .\start-stack.ps1
    ```

    Or manually: `docker compose up -d` then `.\bootstrap-flowise.ps1`

4. Open Flowise in [http://localhost:3000](http://localhost:3000)
5. Open Streamlit chat in [http://localhost:8502](http://localhost:8502) (or set `STREAMLIT_PORT` in `.env`)
6. You can bring the containers down by `docker compose stop`

### Streamlit Cloud

- **Main file path:** `Flowise/docker/streamlit/app.py`
- **Deploy:** [docs/deploy-streamlit-cloud.md](../docs/deploy-streamlit-cloud.md) — chat via OpenAI (sem Render)
- Run `.\deploy-streamlit-cloud.ps1 -OpenCloud` for checklist and secrets template
- Flowise publico (opcional): [docs/deploy-flowise-public.md](../docs/deploy-flowise-public.md)

## 🌱 Env Variables

If you like to persist your data (flows, logs, credentials, storage), set these variables in the `.env` file inside `docker` folder:

-   DATABASE_PATH=/root/.flowise
-   LOG_PATH=/root/.flowise/logs
-   SECRETKEY_PATH=/root/.flowise
-   BLOB_STORAGE_PATH=/root/.flowise/storage

Flowise also support different environment variables to configure your instance. Read [more](https://docs.flowiseai.com/configuration/environment-variables)

## Segurança (LLM)

Riscos de segurança no uso do assistente (entrada, saída, tools, PII) e plano de guardrails (v1.1): [docs/seguranca-llm.md](../docs/seguranca-llm.md). Em **demo local** (localhost, dados fictícios) a severidade operacional é menor; em **produção** trate os itens de severidade alta antes de liberar usuários reais.

Guardrails implementados e exemplos **antes/depois**: [docs/guardrails-demo.md](../docs/guardrails-demo.md).

```powershell
# Na pasta docker/ (sem Python local):
.\run-guardrails-demo.ps1

# Ou manualmente:
docker compose --profile guardrails run --rm --no-deps streamlit-guardrails
```

## Queue Mode:

### Building from source:

You can build the images for worker and main from scratch with:

```
docker compose -f docker-compose-queue-source.yml up -d
```

Monitor Health:

```
docker compose -f docker-compose-queue-source.yml ps
```

### From pre-built images:

You can also use the pre-built images:

```
docker compose -f docker-compose-queue-prebuilt.yml up -d
```

Monitor Health:

```
docker compose -f docker-compose-queue-prebuilt.yml ps
```
