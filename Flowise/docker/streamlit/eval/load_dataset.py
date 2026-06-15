"""Carrega o golden dataset e monta casos de teste DeepEval."""

from __future__ import annotations

import json
import os
from pathlib import Path

from deepeval.dataset import EvaluationDataset, Golden
from deepeval.test_case import LLMTestCase

from eval.flowise_client import query_flowise_sync

GOLDEN_DATASET_PATH = Path(__file__).resolve().parent / "golden_dataset.json"
MIN_GOLDENS = 31


def golden_dataset_path() -> Path:
    override = os.getenv("DEEPEVAL_GOLDEN_DATASET", "").strip()
    return Path(override) if override else GOLDEN_DATASET_PATH


def load_goldens_raw(path: Path | None = None) -> list[dict]:
    dataset_path = path or golden_dataset_path()
    with dataset_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Formato invalido em {dataset_path}: esperado array JSON.")
    if len(payload) < MIN_GOLDENS:
        raise ValueError(
            f"Golden dataset deve ter ao menos {MIN_GOLDENS} entradas; encontrado {len(payload)}."
        )
    return payload


def load_evaluation_dataset(path: Path | None = None) -> EvaluationDataset:
    dataset = EvaluationDataset()
    for row in load_goldens_raw(path):
        dataset.add_golden(
            Golden(
                input=row["input"],
                expected_output=row.get("expected_output"),
                context=row.get("context"),
            )
        )
    return dataset


def is_dry_run() -> bool:
    return os.getenv("DEEPEVAL_DRY_RUN", "").strip().lower() in {"1", "true", "yes"}


def generate_actual_output(question: str, *, dry_run_expected: str | None = None) -> str:
    if is_dry_run():
        if not dry_run_expected:
            raise RuntimeError("DEEPEVAL_DRY_RUN exige expected_output no golden.")
        return dry_run_expected
    return query_flowise_sync(question, streaming=False)


def build_test_cases(path: Path | None = None) -> list[LLMTestCase]:
    goldens = load_goldens_raw(path)
    test_cases: list[LLMTestCase] = []
    for index, golden in enumerate(goldens, start=1):
        question = golden["input"]
        expected = golden.get("expected_output", "")
        actual = generate_actual_output(question, dry_run_expected=expected)
        test_cases.append(
            LLMTestCase(
                input=question,
                actual_output=actual,
                expected_output=expected,
            )
        )
        label = golden.get("id", f"golden_{index:02d}")
        print(f"[{index}/{len(goldens)}] {label}: resposta obtida ({len(actual)} chars)")
    return test_cases
