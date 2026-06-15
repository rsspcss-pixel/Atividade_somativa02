"""Consulta insumos cosmeticos via DuckDB in-memory (sem lock com Streamlit)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import duckdb

INSUMO_COLUMNS = """
    id_insumo, insumo, categoria, fornecedor, lote_minimo_compra,
    consumo_medio_6m, consumo_medio_12m, custo_aquisicao_unitario,
    prazo_entrega_dias, indice_reajuste_12m, criticidade_insumo
"""

COLUMN_NAMES = [c.strip() for c in INSUMO_COLUMNS.replace("\n", " ").split(",")]


def _dataset_files(source_dir: str) -> list[Path]:
    source = Path(source_dir)
    cosmeticos = sorted(source.glob("insumos_cosmeticos_*.csv"))
    return cosmeticos or sorted(source.glob("produtos_*.csv"))


def _sql_array(paths: list[Path]) -> str:
    escaped = [str(p.resolve()).replace("\\", "/").replace("'", "''") for p in paths]
    return ", ".join(f"'{item}'" for item in escaped)


@lru_cache(maxsize=4)
def _connection(files_key: str) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(database=":memory:")
    files = [Path(p) for p in files_key.split("|") if p]
    if not files:
        raise FileNotFoundError("Nenhum arquivo CSV configurado")
    files_sql = _sql_array(files)
    conn.execute(
        f"""
        CREATE OR REPLACE VIEW vw_produtos_demo AS
        SELECT * FROM read_csv_auto([{files_sql}], union_by_name=true, sample_size=-1)
        """
    )
    return conn


def _get_view(source_dir: str = "data") -> duckdb.DuckDBPyConnection:
    files = _dataset_files(source_dir)
    if not files:
        raise FileNotFoundError(f"Nenhum CSV em {source_dir}")
    key = "|".join(str(f.resolve()) for f in files)
    return _connection(key)


def find_insumo_by_id(id_insumo: str, source_dir: str = "data") -> dict | None:
    conn = _get_view(source_dir)
    row = conn.execute(
        f"""
        SELECT {INSUMO_COLUMNS}
        FROM vw_produtos_demo
        WHERE id_insumo = ?
        LIMIT 1
        """,
        [id_insumo.strip()],
    ).fetchone()
    if not row:
        return None
    return enrich_insumo_row(dict(zip(COLUMN_NAMES, row)))


def enrich_insumo_row(row: dict) -> dict:
    consumo_6m = float(row.get("consumo_medio_6m") or 0)
    consumo_12m = float(row.get("consumo_medio_12m") or 0)
    custo = float(row.get("custo_aquisicao_unitario") or 0)
    lote = float(row.get("lote_minimo_compra") or 0)
    return {
        **row,
        "impacto_financeiro_anual": round(consumo_12m * custo, 2),
        "cobertura_lote_meses": round(lote / consumo_6m, 2) if consumo_6m > 0 else None,
    }


def search_insumos(query: str, limit: int = 10, source_dir: str = "data") -> list[dict]:
    conn = _get_view(source_dir)
    pattern = f"%{query.strip().lower()}%"
    rows = conn.execute(
        f"""
        SELECT {INSUMO_COLUMNS}
        FROM vw_produtos_demo
        WHERE lower(insumo) LIKE ? OR lower(fornecedor) LIKE ? OR lower(id_insumo) LIKE ?
        ORDER BY consumo_medio_12m * custo_aquisicao_unitario DESC
        LIMIT ?
        """,
        [pattern, pattern, pattern, limit],
    ).fetchall()
    return [enrich_insumo_row(dict(zip(COLUMN_NAMES, row))) for row in rows]


def resolve_insumo_row(
    *,
    id_insumo: str | None = None,
    insumo: str | None = None,
    fornecedor: str | None = None,
    source_dir: str = "data",
) -> dict:
    if id_insumo:
        found = find_insumo_by_id(id_insumo, source_dir)
        if found:
            return found
        raise ValueError(f"Insumo nao encontrado: id={id_insumo}")

    if insumo:
        matches = search_insumos(insumo, limit=20, source_dir=source_dir)
        if fornecedor:
            f_low = fornecedor.strip().lower()
            matches = [m for m in matches if f_low in str(m.get("fornecedor", "")).lower()]
        if not matches:
            raise ValueError(f"Insumo nao encontrado: nome={insumo}")
        return matches[0]

    raise ValueError("Informe id_insumo ou insumo (nome) para classificacao.")
