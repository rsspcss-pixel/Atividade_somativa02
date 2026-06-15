"""Inferencia do modelo de risco de renegociacao."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from ml.insumo_mapping import insumo_to_uci_features
from ml.load_data import FEATURE_COLUMNS
from ml.paths import METRICS_PATH, MODEL_PATH


class ModelNotFoundError(FileNotFoundError):
    pass


@lru_cache(maxsize=1)
def _load_artifact() -> dict:
    if not MODEL_PATH.exists():
        raise ModelNotFoundError(
            f"Modelo nao encontrado em {MODEL_PATH}. Execute: python ml/train_model.py"
        )
    return joblib.load(MODEL_PATH)


def load_metrics() -> dict | None:
    if not METRICS_PATH.exists():
        return None
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def model_is_ready() -> bool:
    return MODEL_PATH.exists() and METRICS_PATH.exists()


def _predict_features(features: dict[str, float]) -> dict[str, Any]:
    artifact = _load_artifact()
    model = artifact["model"]
    columns = artifact.get("feature_columns", FEATURE_COLUMNS)
    labels = artifact.get("target_labels", {0: "baixo_risco", 1: "renegociacao_urgente"})

    row = {col: float(features.get(col, 0.0)) for col in columns}
    frame = pd.DataFrame([row], columns=columns)
    pred = int(model.predict(frame)[0])
    proba = float(model.predict_proba(frame)[0][1])

    return {
        "classe": pred,
        "rotulo": labels.get(pred, str(pred)),
        "probabilidade_risco": round(proba, 4),
        "probabilidade_baixo_risco": round(1.0 - proba, 4),
        "features_usadas": row,
    }


def predict_uci_row(features: dict[str, float]) -> dict[str, Any]:
    """Predicao com features no formato UCI (LIMIT_BAL, PAY_0, ...)."""
    return _predict_features(features)


def predict_insumo(row: dict) -> dict[str, Any]:
    """Predicao a partir de um registro de insumo cosmetico (CSV/DuckDB)."""
    mapped = insumo_to_uci_features(row)
    result = _predict_features(mapped)
    result["mapeamento_insumo"] = mapped
    result["insumo"] = row.get("insumo")
    result["id_insumo"] = row.get("id_insumo")
    return result
