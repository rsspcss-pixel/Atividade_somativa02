"""
API HTTP do modelo ML para integracao com agentes Flowise.

Endpoints:
    GET  /health
    GET  /metrics
    GET  /insumos/search?q=...
    POST /predict/insumo
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from api_security import env_int, public_error_detail, require_token_in_production
from ml.duckdb_lookup import find_insumo_by_id, resolve_insumo_row, search_insumos
from ml.predict import load_metrics, model_is_ready, predict_insumo, predict_uci_row

ML_API_TOKEN = os.getenv("ML_API_TOKEN", "").strip()
DUCKDB_SOURCE_DIR = os.getenv("DUCKDB_SOURCE_DIR", "data").strip()
ML_API_MAX_QUERY_LEN = env_int("ML_API_MAX_QUERY_LEN", 200)

require_token_in_production(ML_API_TOKEN, "ML_API_TOKEN")

app = FastAPI(
    title="ML Risco Renegociacao API",
    description="Classificador UCI contextualizado para insumos cosmeticos",
    version="1.0.0",
)


def _check_auth(authorization: str | None) -> None:
    if not ML_API_TOKEN:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token obrigatorio")
    token = authorization.removeprefix("Bearer ").strip()
    if token != ML_API_TOKEN:
        raise HTTPException(status_code=403, detail="Token invalido")


class PredictInsumoRequest(BaseModel):
    id_insumo: str | None = Field(None, description="ID do insumo (ex.: INS-01-00042)")
    insumo: str | None = Field(None, description="Nome do insumo para busca")
    fornecedor: str | None = Field(None, description="Filtra fornecedor na busca por nome")
    lote_minimo_compra: float | None = None
    consumo_medio_6m: float | None = None
    consumo_medio_12m: float | None = None
    custo_aquisicao_unitario: float | None = None
    prazo_entrega_dias: float | None = None
    indice_reajuste_12m: float | None = None
    criticidade_insumo: str | None = None


class PredictUciRequest(BaseModel):
    features: dict[str, float]


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "model_ready": model_is_ready()}


@app.get("/metrics")
def metrics(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_auth(authorization)
    data = load_metrics()
    if not data:
        raise HTTPException(status_code=404, detail="Metricas nao encontradas. Execute ml/train_model.py")
    return data


@app.get("/insumos/search")
def insumos_search(
    q: str = Query(..., min_length=1, description="Trecho do nome, fornecedor ou ID"),
    limit: int = Query(10, ge=1, le=50),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_auth(authorization)
    if len(q) > ML_API_MAX_QUERY_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Query excede {ML_API_MAX_QUERY_LEN} caracteres.",
        )
    try:
        items = search_insumos(q, limit=limit, source_dir=DUCKDB_SOURCE_DIR)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=public_error_detail(exc, context="insumos_search"),
        ) from exc
    return {"query": q, "count": len(items), "items": items}


@app.get("/insumos/{id_insumo}")
def insumo_by_id(
    id_insumo: str,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_auth(authorization)
    try:
        item = find_insumo_by_id(id_insumo, source_dir=DUCKDB_SOURCE_DIR)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=404, detail=f"Insumo nao encontrado: {id_insumo}")
    return {"item": item}


@app.post("/predict/insumo")
def predict_insumo_endpoint(
    body: PredictInsumoRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_auth(authorization)
    if not model_is_ready():
        raise HTTPException(
            status_code=503,
            detail="Modelo nao treinado. Execute python ml/train_model.py ou use a aba ML no Streamlit.",
        )

    numeric_fields = {
        "lote_minimo_compra": body.lote_minimo_compra,
        "consumo_medio_6m": body.consumo_medio_6m,
        "consumo_medio_12m": body.consumo_medio_12m,
        "custo_aquisicao_unitario": body.custo_aquisicao_unitario,
        "prazo_entrega_dias": body.prazo_entrega_dias,
        "indice_reajuste_12m": body.indice_reajuste_12m,
        "criticidade_insumo": body.criticidade_insumo,
    }
    has_direct_metrics = any(v is not None for v in numeric_fields.values())

    try:
        if has_direct_metrics and body.insumo:
            row = {"insumo": body.insumo, "id_insumo": body.id_insumo}
            for key, value in numeric_fields.items():
                if value is not None:
                    row[key] = value
        else:
            row = resolve_insumo_row(
                id_insumo=body.id_insumo,
                insumo=body.insumo,
                fornecedor=body.fornecedor,
                source_dir=DUCKDB_SOURCE_DIR,
            )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    result = predict_insumo(row)
    return {
        "insumo_resolvido": {
            "id_insumo": row.get("id_insumo"),
            "insumo": row.get("insumo"),
            "fornecedor": row.get("fornecedor"),
            "categoria": row.get("categoria"),
        },
        "predicao": {
            "classe": result["classe"],
            "rotulo": result["rotulo"],
            "probabilidade_risco": result["probabilidade_risco"],
            "probabilidade_baixo_risco": result["probabilidade_baixo_risco"],
        },
        "recomendacao": (
            "Revisar lote minimo, validade e mesa de negociacao."
            if result["classe"] == 1
            else "Risco baixo; manter monitoramento de giro e validade."
        ),
    }


@app.post("/predict/uci")
def predict_uci_endpoint(
    body: PredictUciRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_auth(authorization)
    if not model_is_ready():
        raise HTTPException(status_code=503, detail="Modelo nao treinado.")
    return predict_uci_row(body.features)
