"""Motor de regressao DeepEval: avalia o chat Flowise e compara com baseline."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

from eval.flowise_client import query_flowise_sync
from eval.llm_config import configure_deepeval_local_llm, get_judge_model
from eval.load_dataset import golden_dataset_path, is_dry_run, load_goldens_raw

configure_deepeval_local_llm()

DEFAULT_RESULTS_DIR = Path("data/deepeval_results")
BASELINE_FILE = "regression_baseline.json"
LATEST_FILE = "regression_latest.json"
REPORT_FILE = "regression_report.json"

REGRESSION_SCORE_DROP = float(os.getenv("DEEPEVAL_REGRESSION_SCORE_DROP", "0.08"))


def regression_metric() -> GEval:
    """Metrica GEval focada em detectar regressao vs golden expected_output."""
    return GEval(
        name="Regressao (resposta vs golden)",
        criteria=(
            "Avalie se houve REGRESSAO: a resposta atual perdeu qualidade factual, "
            "omitiu conceitos essenciais da referencia ou contradiz o expected output. "
            "Score alto = sem regressao (resposta equivalente ou melhor). "
            "Score baixo = regressao clara. Nao exija texto identico; compare semantica."
        ),
        evaluation_params=[
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        threshold=float(os.getenv("DEEPEVAL_REGRESSION_THRESHOLD", "0.7")),
        model=get_judge_model(),
        async_mode=False,
    )


def results_dir() -> Path:
    override = os.getenv("DEEPEVAL_RESULTS_FOLDER", "").strip()
    path = Path(override) if override else DEFAULT_RESULTS_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class CaseResult:
    golden_id: str
    input: str
    expected_output: str
    actual_output: str
    score: float
    passed: bool
    reason: str
    duration_ms: int


@dataclass
class RegressionRun:
    run_id: str
    created_at: str
    chatflow_target: str
    metric_name: str
    metric_threshold: float
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    mean_score: float
    duration_ms: int
    cases: list[CaseResult] = field(default_factory=list)
    regressions_vs_baseline: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _evaluate_case(metric: GEval, golden: dict, *, dry_run: bool) -> CaseResult:
    question = golden["input"]
    expected = golden.get("expected_output", "")
    golden_id = str(golden.get("id", question[:48]))
    t0 = time.perf_counter()
    if dry_run:
        actual = expected
    else:
        actual = query_flowise_sync(question, streaming=False)
    test_case = LLMTestCase(
        input=question,
        actual_output=actual,
        expected_output=expected,
    )
    metric.measure(test_case)
    elapsed = int((time.perf_counter() - t0) * 1000)
    return CaseResult(
        golden_id=golden_id,
        input=question,
        expected_output=expected,
        actual_output=actual,
        score=float(metric.score or 0.0),
        passed=bool(metric.is_successful()),
        reason=str(metric.reason or ""),
        duration_ms=elapsed,
    )


def compare_with_baseline(
    current: RegressionRun,
    baseline: RegressionRun | None,
    *,
    score_drop: float = REGRESSION_SCORE_DROP,
) -> list[dict[str, Any]]:
    if not baseline:
        return []
    baseline_by_id = {c.golden_id: c for c in baseline.cases}
    regressions: list[dict[str, Any]] = []
    for case in current.cases:
        prev = baseline_by_id.get(case.golden_id)
        if not prev:
            continue
        delta = round(case.score - prev.score, 4)
        if delta < -score_drop or (prev.passed and not case.passed):
            regressions.append(
                {
                    "golden_id": case.golden_id,
                    "input_preview": case.input[:120],
                    "baseline_score": prev.score,
                    "current_score": case.score,
                    "score_delta": delta,
                    "baseline_passed": prev.passed,
                    "current_passed": case.passed,
                    "reason": case.reason,
                }
            )
    return regressions


def run_regression_eval(
    *,
    limit: int | None = None,
    golden_ids: list[str] | None = None,
    save_baseline: bool = False,
    compare_baseline: bool = True,
    dataset_path: Path | None = None,
) -> RegressionRun:
    metric = regression_metric()
    goldens = load_goldens_raw(dataset_path)
    if golden_ids:
        wanted = set(golden_ids)
        goldens = [g for g in goldens if str(g.get("id", "")) in wanted]
    if limit is not None and limit > 0:
        goldens = goldens[:limit]

    dry_run = is_dry_run()
    chatflow = os.getenv("FLOWISE_API_URL", "")
    t0 = time.perf_counter()
    cases: list[CaseResult] = []
    for index, golden in enumerate(goldens, start=1):
        case = _evaluate_case(metric, golden, dry_run=dry_run)
        cases.append(case)
        label = golden.get("id", f"case_{index}")
        status = "OK" if case.passed else "FAIL"
        print(
            f"[{index}/{len(goldens)}] {label}: score={case.score:.2f} "
            f"({status}) em {case.duration_ms}ms"
        )

    passed = sum(1 for c in cases if c.passed)
    failed = len(cases) - passed
    mean_score = sum(c.score for c in cases) / len(cases) if cases else 0.0
    run = RegressionRun(
        run_id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc).isoformat(),
        chatflow_target=chatflow,
        metric_name=metric.name,
        metric_threshold=float(metric.threshold or 0.7),
        total_cases=len(cases),
        passed_cases=passed,
        failed_cases=failed,
        pass_rate=round(passed / len(cases), 4) if cases else 0.0,
        mean_score=round(mean_score, 4),
        duration_ms=int((time.perf_counter() - t0) * 1000),
        cases=cases,
    )

    baseline = load_baseline() if compare_baseline else None
    run.regressions_vs_baseline = compare_with_baseline(run, baseline)

    out_dir = results_dir()
    latest_path = out_dir / LATEST_FILE
    report_path = out_dir / REPORT_FILE
    latest_path.write_text(json.dumps(run.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    report = {
        "summary": {
            "run_id": run.run_id,
            "pass_rate": run.pass_rate,
            "mean_score": run.mean_score,
            "regressions_detected": len(run.regressions_vs_baseline),
            "dataset": str(dataset_path or golden_dataset_path()),
        },
        "regressions": run.regressions_vs_baseline,
        "failed_cases": [
            asdict(c)
            for c in cases
            if not c.passed
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if save_baseline:
        save_baseline_run(run)

    return run


def save_baseline_run(run: RegressionRun) -> Path:
    path = results_dir() / BASELINE_FILE
    path.write_text(json.dumps(run.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_baseline() -> RegressionRun | None:
    path = results_dir() / BASELINE_FILE
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = [CaseResult(**row) for row in payload.get("cases", [])]
    payload["cases"] = cases
    return RegressionRun(**payload)


def load_latest_report() -> dict[str, Any] | None:
    path = results_dir() / REPORT_FILE
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_single(question: str, expected_output: str, *, golden_id: str = "adhoc") -> CaseResult:
    metric = regression_metric()
    golden = {"id": golden_id, "input": question, "expected_output": expected_output}
    return _evaluate_case(metric, golden, dry_run=is_dry_run())
