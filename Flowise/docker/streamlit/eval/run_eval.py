#!/usr/bin/env python3
"""Executa avaliacao DeepEval completa contra o Flowise usando o golden dataset."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local")
except ImportError:
    pass

from deepeval import evaluate

from eval.llm_config import configure_deepeval_local_llm, judge_model_summary
from eval.load_dataset import build_test_cases, golden_dataset_path, is_dry_run, load_goldens_raw
from eval.metrics import DEFAULT_METRICS, LOCAL_JUDGE_ASYNC_CONFIG, REGRESSION_ONLY_METRICS
from eval.regression import run_regression_eval

configure_deepeval_local_llm()


def _regression_mode() -> bool:
    return os.getenv("DEEPEVAL_REGRESSION_MODE", "").strip().lower() in {"1", "true", "yes"}


def main() -> int:
    dataset_path = golden_dataset_path()
    goldens = load_goldens_raw(dataset_path)
    print(f"Golden dataset: {dataset_path} ({len(goldens)} goldens)")
    if is_dry_run():
        print("Modo DEEPEVAL_DRY_RUN=1: actual_output = expected_output (sem chamar Flowise).")

    if _regression_mode():
        limit_raw = os.getenv("DEEPEVAL_REGRESSION_LIMIT", "").strip()
        limit = int(limit_raw) if limit_raw.isdigit() else None
        save_baseline = os.getenv("DEEPEVAL_SAVE_BASELINE", "").strip().lower() in {"1", "true", "yes"}
        print(f"Modo regressao: metrica GEval + comparacao com baseline (limit={limit or 'todos'})")
        run = run_regression_eval(limit=limit, save_baseline=save_baseline)
        print(
            f"Regressao concluida: pass_rate={run.pass_rate:.2%}, "
            f"mean_score={run.mean_score:.2f}, "
            f"regressions={len(run.regressions_vs_baseline)}"
        )
        return 0

    metrics = REGRESSION_ONLY_METRICS if os.getenv("DEEPEVAL_METRICS", "").strip() == "regression" else DEFAULT_METRICS
    test_cases = build_test_cases(dataset_path)
    identifier = os.getenv("DEEPEVAL_RUN_IDENTIFIER", "assistente-negociacao-flowise")
    print(f"LLM judge (metricas): {judge_model_summary()}")
    print(
        f"Iniciando evaluate() com {len(test_cases)} casos, "
        f"{len(metrics)} metricas GEval (serial, judge local)..."
    )
    evaluate(
        test_cases=test_cases,
        metrics=metrics,
        identifier=identifier,
        async_config=LOCAL_JUDGE_ASYNC_CONFIG,
    )
    print("Avaliacao concluida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
