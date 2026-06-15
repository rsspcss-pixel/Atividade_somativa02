"""Caminhos absolutos do app (independente do diretorio de execucao)."""

from __future__ import annotations

from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = APP_ROOT / "data"
ML_MODELS_DIR = APP_ROOT / "ml" / "models"


def resolve_app_path(relative: str | Path) -> Path:
    """Resolve path relativo a pasta do app.py (nao ao cwd)."""
    path = Path(relative)
    if path.is_absolute():
        return path
    return (APP_ROOT / path).resolve()
