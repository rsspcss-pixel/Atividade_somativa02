"""
API HTTP do agente DeepEval (regressao) para integracao com Flowise.

Endpoints:
    GET  /health
    GET  /eval/regression/report
    POST /eval/regression/run
    POST /eval/regression/single
    POST /eval/regression/baseline
"""

from __future__ import annotations

import json
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from api_security import env_bool, env_int, public_error_detail, require_token_in_production
from eval.regression import (
    evaluate_single,
    load_baseline,
    load_latest_report,
    run_regression_eval,
    save_baseline_run,
)

EVAL_API_TOKEN = os.getenv("EVAL_API_TOKEN", "").strip()
EVAL_API_MAX_LIMIT = env_int("EVAL_API_MAX_LIMIT", 10)
EVAL_API_ALLOW_BASELINE = env_bool("EVAL_API_ALLOW_BASELINE", default=False)

require_token_in_production(EVAL_API_TOKEN, "EVAL_API_TOKEN")

app = FastAPI(
    title="DeepEval Regression Agent API",
    description="Agente de avaliacao por regressao (Flowise + golden dataset)",
    version="1.0.0",
)


def _check_auth(authorization: str | None) -> None:
    if not EVAL_API_TOKEN:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token obrigatorio")
    token = authorization.removeprefix("Bearer ").strip()
    if token != EVAL_API_TOKEN:
        raise HTTPException(status_code=403, detail="Token invalido")


def _cap_regression_limit(requested: int | None) -> int | None:
    if requested is None:
        return None
    return min(requested, EVAL_API_MAX_LIMIT)


class RegressionRunRequest(BaseModel):
    limit: int | None = Field(None, ge=1, le=100, description="Limita numero de goldens")
    golden_ids: list[str] | None = Field(None, description="IDs especificos do golden dataset")
    save_baseline: bool = Field(False, description="Grava resultado como nova baseline")
    compare_baseline: bool = Field(True, description="Compara com baseline anterior")


class RegressionSingleRequest(BaseModel):
    question: str = Field(..., min_length=3)
    expected_output: str = Field(..., min_length=3)
    golden_id: str = Field("adhoc", description="Identificador opcional do caso")


@app.get("/health")
def health() -> dict[str, Any]:
    baseline = load_baseline()
    report = load_latest_report()
    return {
        "status": "ok",
        "agent": "deepeval-regression",
        "has_baseline": baseline is not None,
        "last_report": report.get("summary") if report else None,
        "max_limit": EVAL_API_MAX_LIMIT,
        "baseline_writes_allowed": EVAL_API_ALLOW_BASELINE,
    }


@app.get("/eval/regression/report")
def regression_report(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_auth(authorization)
    report = load_latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="Nenhum relatorio de regressao encontrado.")
    return report


@app.post("/eval/regression/run")
def regression_run(
    body: RegressionRunRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_auth(authorization)
    if body.save_baseline and not EVAL_API_ALLOW_BASELINE:
        raise HTTPException(
            status_code=403,
            detail="save_baseline desabilitado. Defina EVAL_API_ALLOW_BASELINE=1 para permitir.",
        )
    effective_limit = _cap_regression_limit(body.limit)
    try:
        run = run_regression_eval(
            limit=effective_limit,
            golden_ids=body.golden_ids,
            save_baseline=body.save_baseline,
            compare_baseline=body.compare_baseline,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=public_error_detail(exc, context="regression_run"),
        ) from exc
    return {
        "run_id": run.run_id,
        "pass_rate": run.pass_rate,
        "mean_score": run.mean_score,
        "passed_cases": run.passed_cases,
        "failed_cases": run.failed_cases,
        "total_cases": run.total_cases,
        "duration_ms": run.duration_ms,
        "regressions_detected": len(run.regressions_vs_baseline),
        "regressions": run.regressions_vs_baseline,
        "metric": run.metric_name,
        "threshold": run.metric_threshold,
        "limit_applied": effective_limit,
    }


@app.post("/eval/regression/single")
def regression_single(
    body: RegressionSingleRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_auth(authorization)
    try:
        result = evaluate_single(
            body.question,
            body.expected_output,
            golden_id=body.golden_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=public_error_detail(exc, context="regression_single"),
        ) from exc
    return {
        "golden_id": result.golden_id,
        "score": result.score,
        "passed": result.passed,
        "reason": result.reason,
        "duration_ms": result.duration_ms,
        "actual_output_preview": result.actual_output[:500],
    }


@app.post("/eval/regression/baseline")
def regression_save_baseline(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_auth(authorization)
    if not EVAL_API_ALLOW_BASELINE:
        raise HTTPException(
            status_code=403,
            detail="Gravar baseline desabilitado. Defina EVAL_API_ALLOW_BASELINE=1.",
        )
    from eval.regression import LATEST_FILE, RegressionRun, CaseResult, results_dir

    latest = results_dir() / LATEST_FILE
    if not latest.is_file():
        raise HTTPException(status_code=404, detail="Execute /eval/regression/run antes de salvar baseline.")
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
        cases = [CaseResult(**row) for row in payload.get("cases", [])]
        payload["cases"] = cases
        run = RegressionRun(**payload)
        path = save_baseline_run(run)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=public_error_detail(exc, context="regression_baseline"),
        ) from exc
    return {"status": "saved", "baseline_path": str(path), "run_id": run.run_id}
