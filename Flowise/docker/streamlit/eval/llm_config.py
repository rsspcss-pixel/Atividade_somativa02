"""Configuracao do LLM local (LM Studio) para metricas DeepEval."""

from __future__ import annotations

import os
from functools import lru_cache

from deepeval.models import LocalModel

DEFAULT_LOCAL_MODEL = "nvidia/nemotron-3-nano-4b"
DEFAULT_LM_STUDIO_PORT = 1234
DEFAULT_LOCAL_API_KEY = "lm-studio"


def local_model_host() -> str:
    return os.getenv("LOCAL_MODEL_HOST", "localhost").strip() or "localhost"


def local_model_port() -> int:
    raw = os.getenv("LM_STUDIO_PORT", str(DEFAULT_LM_STUDIO_PORT)).strip()
    return int(raw or DEFAULT_LM_STUDIO_PORT)


def default_local_base_url() -> str:
    override = os.getenv("LOCAL_MODEL_BASE_URL", "").strip()
    if override:
        return override.rstrip("/")
    return f"http://{local_model_host()}:{local_model_port()}/v1"


def local_model_name() -> str:
    return os.getenv("LOCAL_MODEL_NAME", DEFAULT_LOCAL_MODEL).strip() or DEFAULT_LOCAL_MODEL


def configure_deepeval_local_llm() -> None:
    """Garante que metricas sem model explicito preferem o adapter local."""
    os.environ.setdefault("USE_LOCAL_MODEL", "1")
    os.environ.setdefault("USE_OPENAI_MODEL", "0")
    os.environ.setdefault("LOCAL_MODEL_NAME", local_model_name())
    os.environ.setdefault("LOCAL_MODEL_BASE_URL", default_local_base_url())
    os.environ.setdefault("LOCAL_MODEL_API_KEY", DEFAULT_LOCAL_API_KEY)
    # Modelos locais pequenos costumam demorar mais que APIs cloud em modo JSON.
    os.environ.setdefault("DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE", "300")


@lru_cache(maxsize=1)
def get_judge_model() -> LocalModel:
    configure_deepeval_local_llm()
    return LocalModel(
        model=local_model_name(),
        base_url=default_local_base_url(),
        api_key=os.getenv("LOCAL_MODEL_API_KEY", DEFAULT_LOCAL_API_KEY),
        format="json",
        temperature=0.0,
    )


def judge_model_summary() -> str:
    model = get_judge_model()
    return f"{model.get_model_name()} @ {default_local_base_url()}"
