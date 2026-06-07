"""Testes DeepEval parametrizados a partir do golden dataset (deepeval test run)."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local")
except ImportError:
    pass

from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from eval.llm_config import configure_deepeval_local_llm
from eval.load_dataset import generate_actual_output, load_goldens_raw
from eval.metrics import DEFAULT_METRICS

configure_deepeval_local_llm()


@lru_cache(maxsize=1)
def _goldens() -> tuple[dict, ...]:
    return tuple(load_goldens_raw())


def _golden_id(golden: dict) -> str:
    return str(golden.get("id", golden["input"][:48]))


@pytest.mark.parametrize("golden", _goldens(), ids=_golden_id)
def test_assistente_negociacao_golden(golden: dict):
    question = golden["input"]
    expected = golden.get("expected_output", "")
    actual = generate_actual_output(question, dry_run_expected=expected)
    test_case = LLMTestCase(
        input=question,
        actual_output=actual,
        expected_output=expected,
    )
    assert_test(test_case, DEFAULT_METRICS, run_async=False)
