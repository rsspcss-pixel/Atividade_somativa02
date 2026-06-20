# Avaliacao e golden dataset

## Golden dataset

Arquivo: [`golden_dataset.json`](golden_dataset.json)

- **41 casos** (`id`, `input`, `expected_output`, `context` opcional)
- Temas: lotes minimos, armazenagem, validade, perfil Lumina, negociacao com fornecedores
- Minimo exigido pela atividade: 31 goldens

## Testes

| Arquivo | Tipo | Comando |
|---------|------|---------|
| [`../test_guardrails.py`](../test_guardrails.py) | Unitario (guardrails, API security) | `python -m pytest test_guardrails.py -q` |
| [`test_assistente_negociacao.py`](test_assistente_negociacao.py) | DeepEval parametrizado (41 goldens) | Ver abaixo |

### Guardrails (rapido, sem LLM)

```powershell
cd Flowise/docker/streamlit
python -m pytest test_guardrails.py -q
```

### DeepEval + regressao (Docker, requer LM Studio + Flowise)

```powershell
cd Flowise/docker
.\start-stack.ps1
.\run-eval.ps1              # avaliacao completa
.\run-eval.ps1 -DryRun      # smoke (metricas, sem Flowise)
.\run-regression-agent.ps1 -Limit 5
```

Equivalente manual:

```powershell
docker compose --profile eval run --rm streamlit-eval
```

## Metricas

Configuradas em [`metrics.py`](metrics.py). Judge local: [`llm_config.py`](llm_config.py) (`nvidia/nemotron-3-nano-4b` via LM Studio).
