"""
Garante dataset CSV e modelo ML prontos antes do app usar DuckDB / predicao.

Uso:
  python demo_assets.py
  python demo_assets.py --force-train
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app_paths import APP_ROOT, DATA_DIR, ML_MODELS_DIR, resolve_app_path

if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


def _candidate_data_dirs(source_dir: Path | None = None) -> list[Path]:
    if source_dir is not None:
        return [source_dir]
    return [DATA_DIR, resolve_app_path("data")]


def dataset_files(source_dir: Path | None = None) -> list[Path]:
    for root in _candidate_data_dirs(source_dir):
        if not root.is_dir():
            continue
        cosmeticos = sorted(root.glob("insumos_cosmeticos_*.csv"))
        if cosmeticos:
            return cosmeticos
        produtos = sorted(root.glob("produtos_*.csv"))
        if produtos:
            return produtos
    return []


def ensure_dataset(*, rows: int = 5000, files: int = 5) -> list[Path]:
    existing = dataset_files()
    if existing:
        return existing

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    import generate_mock_data

    generate_mock_data.ROWS_PER_FILE = rows
    generate_mock_data.FILES_TO_GENERATE = files
    generate_mock_data.OUTPUT_DIR = DATA_DIR
    generate_mock_data.main()
    created = dataset_files()
    if not created:
        raise FileNotFoundError(f"Falha ao gerar CSV em {DATA_DIR}")
    return created


def ensure_ml_model(*, force: bool = False) -> Path:
    from ml.paths import METRICS_PATH, MODEL_PATH

    if MODEL_PATH.exists() and METRICS_PATH.exists() and not force:
        return MODEL_PATH

    from ml.train_model import train

    train()
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Treino concluido mas modelo ausente: {MODEL_PATH}")
    return MODEL_PATH


def ensure_all(*, force_train: bool = False) -> dict:
    csv_files = ensure_dataset()
    model_path = ensure_ml_model(force=force_train)
    return {
        "data_dir": str(DATA_DIR),
        "csv_files": [str(p) for p in csv_files],
        "model_path": str(model_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara dataset e modelo ML")
    parser.add_argument("--force-train", action="store_true")
    parser.add_argument("--rows", type=int, default=800)
    parser.add_argument("--files", type=int, default=2)
    args = parser.parse_args()

    if not dataset_files():
        ensure_dataset(rows=args.rows, files=args.files)
    else:
        print(f"Dataset OK: {len(dataset_files())} arquivo(s)")

    model = ensure_ml_model(force=args.force_train)
    print(f"Modelo ML OK: {model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
