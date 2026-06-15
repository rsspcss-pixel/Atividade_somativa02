"""
Treina classificador de risco de renegociacao com dataset UCI.

Uso:
    python ml/train_model.py
    python ml/train_model.py --test-size 0.2 --random-state 42
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.load_data import TARGET_COLUMN, get_feature_matrix, load_uci_credit_default
from ml.paths import (
    DATASET_NAME,
    DATASET_SOURCE,
    DATASET_URL,
    DOMAIN_TARGET_LABEL,
    METRICS_PATH,
    MODEL_PATH,
    MODELS_DIR,
)


def train(test_size: float = 0.2, random_state: int = 42) -> dict:
    df = load_uci_credit_default()
    x, y = get_feature_matrix(df)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=10,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)

    y_pred = model.predict(x_test)
    y_proba = model.predict_proba(x_test)[:, 1]

    metrics = {
        "dataset": {
            "name": DATASET_NAME,
            "source": DATASET_SOURCE,
            "url": DATASET_URL,
            "n_records": int(len(df)),
            "n_features": len(x.columns),
            "target_column_uci": TARGET_COLUMN,
            "target_column_domain": DOMAIN_TARGET_LABEL,
            "target_interpretation": (
                "No dominio de compras de insumos cosmeticos, a inadimplencia do cartao (UCI) "
                "foi contextualizada como risco de renegociacao urgente por excesso de estoque "
                "ou pressao de custo."
            ),
            "class_balance": {
                "negativo_sem_risco": int((y == 0).sum()),
                "positivo_risco_alto": int((y == 1).sum()),
            },
        },
        "model": {
            "algorithm": "RandomForestClassifier",
            "n_estimators": 200,
            "max_depth": 12,
            "test_size": test_size,
            "random_state": random_state,
        },
        "metrics": {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(y_test, y_proba)), 4),
        },
        "primary_metric": "recall",
        "primary_metric_rationale": (
            "Em compras de insumos com validade, falhar em detectar um SKU de alto risco "
            "(baixo recall) pode gerar obsolescencia e perda financeira; priorizamos recall "
            "com class_weight balanced, aceitando alguns falsos positivos revisaveis pelo comprador."
        ),
        "feature_columns": list(x.columns),
    }

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    artifact = {
        "model": model,
        "feature_columns": list(x.columns),
        "target_labels": {0: "baixo_risco", 1: "renegociacao_urgente"},
    }
    joblib.dump(artifact, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Treina modelo UCI de risco de renegociacao.")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    metrics = train(test_size=args.test_size, random_state=args.random_state)
    m = metrics["metrics"]
    print(f"Dataset: {metrics['dataset']['n_records']} registros")
    print(
        f"Metricas — accuracy={m['accuracy']}, precision={m['precision']}, "
        f"recall={m['recall']}, f1={m['f1']}, roc_auc={m['roc_auc']}"
    )
    print(f"Modelo salvo em: {MODEL_PATH}")
    print(f"Metricas salvas em: {METRICS_PATH}")


if __name__ == "__main__":
    main()
