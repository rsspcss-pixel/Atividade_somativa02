"""Metricas DeepEval padrao para o assistente de negociacao."""

from deepeval.evaluate import AsyncConfig
from deepeval.metrics import GEval
from deepeval.test_case import SingleTurnParams

from eval.llm_config import get_judge_model
from eval.regression import regression_metric

_JUDGE = get_judge_model()
REGRESSAO_GEVal = regression_metric()

# Judge local: apenas GEval (menos chamadas LLM que Answer Relevancy / Faithfulness).
CORRETUDE_GEVal = GEval(
    name="Corretude (conhecimento de negociacao)",
    criteria=(
        "A resposta esta correta e alinhada com a expected output "
        "(compras, armazenagem, validade, negociacao)?"
    ),
    evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT],
    threshold=0.65,
    model=_JUDGE,
    async_mode=False,
)

ESTILO_ABNT_GEVal = GEval(
    name="Estilo formal em portugues (ABNT)",
    criteria=(
        "Portugues formal e claro, termos tecnicos adequados. "
        "Nao penalize acentos ausentes se expected output tambem nao tiver."
    ),
    evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT],
    threshold=0.6,
    model=_JUDGE,
    async_mode=False,
)

DEFAULT_METRICS = [REGRESSAO_GEVal, CORRETUDE_GEVal, ESTILO_ABNT_GEVal]

# Avaliacao rapida (CI/smoke): apenas metrica de regressao.
REGRESSION_ONLY_METRICS = [REGRESSAO_GEVal]

# Um golden por vez; dentro de cada golden as metricas rodam em serie (run_async=False).
LOCAL_JUDGE_ASYNC_CONFIG = AsyncConfig(run_async=False, max_concurrent=1)
