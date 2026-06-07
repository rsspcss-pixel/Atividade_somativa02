# Flowise Docker Hub Image

Starts Flowise from [DockerHub Image](https://hub.docker.com/r/flowiseai/flowise)

## Usage

1. Create `.env` file and specify the `PORT` (refer to `.env.example`)
2. Configure Streamlit integration by copying `streamlit/.env.example` to `streamlit/.env` and filling your `FLOWISE_API_TOKEN`
3. `docker compose up -d`
4. Open Flowise in [http://localhost:3000](http://localhost:3000)
5. Open Streamlit chat in [http://localhost:8502](http://localhost:8502) (or set `STREAMLIT_PORT` in `.env`)
6. You can bring the containers down by `docker compose stop`

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
