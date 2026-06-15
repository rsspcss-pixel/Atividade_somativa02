"""Carrega o dataset UCI Default of Credit Card Clients."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from ml.paths import DATA_CACHE_PATH

UCI_XLS_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/00350/"
    "default%20of%20credit%20card%20clients.xls"
)
UCI_ZIP_URL = "https://archive.ics.uci.edu/static/public/350/default+of+credit+card+clients.zip"

FEATURE_COLUMNS = [
    "LIMIT_BAL",
    "SEX",
    "EDUCATION",
    "MARRIAGE",
    "AGE",
    "PAY_0",
    "PAY_2",
    "PAY_3",
    "PAY_4",
    "PAY_5",
    "PAY_6",
    "BILL_AMT1",
    "BILL_AMT2",
    "BILL_AMT3",
    "BILL_AMT4",
    "BILL_AMT5",
    "BILL_AMT6",
    "PAY_AMT1",
    "PAY_AMT2",
    "PAY_AMT3",
    "PAY_AMT4",
    "PAY_AMT5",
    "PAY_AMT6",
]

TARGET_COLUMN = "default_payment_next_month"
TARGET_COLUMN_UCI = "default payment next month"


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {col: col.strip().replace(" ", "_") for col in df.columns}
    out = df.rename(columns=renamed)
    if TARGET_COLUMN_UCI.replace(" ", "_") in out.columns:
        out = out.rename(columns={TARGET_COLUMN_UCI.replace(" ", "_"): TARGET_COLUMN})
    elif "Y" in out.columns:
        out = out.rename(columns={"Y": TARGET_COLUMN})
    return out


def _fetch_from_openml() -> pd.DataFrame:
    from sklearn.datasets import fetch_openml

    bunch = fetch_openml(data_id=42477, as_frame=True, parser="auto")
    df = bunch.data.join(bunch.target)
    df = _normalize_columns(df)
    if "ID" in df.columns:
        df = df.drop(columns=["ID"])
    if TARGET_COLUMN not in df.columns and bunch.target.name:
        target_name = bunch.target.name.strip().replace(" ", "_")
        if target_name in df.columns:
            df = df.rename(columns={target_name: TARGET_COLUMN})
    df[TARGET_COLUMN] = pd.to_numeric(df[TARGET_COLUMN], errors="coerce").astype("Int64")
    return df


def _fetch_from_uci_zip() -> pd.DataFrame:
    import zipfile

    import requests

    response = requests.get(UCI_ZIP_URL, timeout=120)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        xls_name = next(n for n in zf.namelist() if n.lower().endswith(".xls"))
        raw = pd.read_excel(io.BytesIO(zf.read(xls_name)), header=1)
    return _parse_uci_raw(raw)


def _fetch_from_uci_xls() -> pd.DataFrame:
    import requests

    response = requests.get(UCI_XLS_URL, timeout=120)
    response.raise_for_status()
    raw = pd.read_excel(io.BytesIO(response.content), header=1)
    return _parse_uci_raw(raw)


def _parse_uci_raw(raw: pd.DataFrame) -> pd.DataFrame:
    raw = _normalize_columns(raw)
    if "ID" in raw.columns:
        raw = raw.drop(columns=["ID"])
    x_cols = [c for c in raw.columns if c.startswith("X") and c[1:].isdigit()]
    if len(x_cols) >= 23:
        mapping = {f"X{i}": FEATURE_COLUMNS[i - 1] for i in range(1, 24)}
        raw = raw.rename(columns=mapping)
    if TARGET_COLUMN not in raw.columns:
        for candidate in ("default_payment_next_month", "Y"):
            if candidate in raw.columns:
                raw = raw.rename(columns={candidate: TARGET_COLUMN})
                break
    raw[TARGET_COLUMN] = pd.to_numeric(raw[TARGET_COLUMN], errors="coerce").astype("Int64")
    return raw


def load_uci_credit_default(cache_path: Path | None = None) -> pd.DataFrame:
    """Retorna DataFrame com features UCI e coluna alvo binaria."""
    cache = cache_path or DATA_CACHE_PATH
    if cache.exists():
        df = pd.read_csv(cache)
        df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)
        return df

    errors: list[str] = []
    for loader_name, loader in (
        ("openml", _fetch_from_openml),
        ("uci_zip", _fetch_from_uci_zip),
        ("uci_xls", _fetch_from_uci_xls),
    ):
        try:
            df = loader()
            missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
            if missing:
                raise ValueError(f"Colunas ausentes apos {loader_name}: {missing}")
            df = df[FEATURE_COLUMNS + [TARGET_COLUMN]].dropna()
            df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)
            cache.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(cache, index=False)
            return df
        except Exception as exc:
            errors.append(f"{loader_name}: {exc}")

    raise RuntimeError("Nao foi possivel carregar o dataset UCI. " + " | ".join(errors))


def get_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    x = df[FEATURE_COLUMNS].copy()
    y = df[TARGET_COLUMN].astype(int)
    return x, y
