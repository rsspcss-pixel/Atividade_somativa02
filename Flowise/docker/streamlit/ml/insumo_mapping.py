"""
Mapeia um registro de insumo cosmetico (DuckDB/CSV) para o espaco de features do UCI.

Contextualizacao pedagogica (como na videoaula de condomínios):
- LIMIT_BAL ~ volume financeiro anual do SKU (consumo x custo)
- PAY_* ~ historico de "atraso" derivado do indice de reajuste e cobertura de lote
- BILL_AMT* ~ valor de estoque implicito pelo lote minimo
- PAY_AMT* ~ pagamentos / consumo recente
- default no UCI ~ risco de renegociacao urgente no dominio de compras
"""

from __future__ import annotations

from ml.load_data import FEATURE_COLUMNS

CRITICIDADE_MAP = {"baixa": 1, "media": 2, "alta": 3}


def _num(value, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and value != value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def insumo_to_uci_features(row: dict) -> dict[str, float]:
    consumo_6m = _num(row.get("consumo_medio_6m"), 100.0)
    consumo_12m = _num(row.get("consumo_medio_12m"), consumo_6m * 1.8)
    custo = _num(row.get("custo_aquisicao_unitario"), 50.0)
    lote = _num(row.get("lote_minimo_compra"), 100.0)
    prazo = _num(row.get("prazo_entrega_dias"), 30.0)
    reajuste = _num(row.get("indice_reajuste_12m"), 0.05)

    impacto_anual = max(consumo_12m * custo, 1.0)
    cobertura_meses = lote / max(consumo_6m, 1.0)
    estoque_valor = lote * custo
    consumo_mensal_valor = (consumo_6m / 6.0) * custo

    crit = str(row.get("criticidade_insumo", "media")).lower()
    education = CRITICIDADE_MAP.get(crit, 2)

    # PAY status UCI: -1=pay duly, 0=revolving, 1..9=delay months — proxy via reajuste/cobertura
    if reajuste > 0.15 or cobertura_meses > 3:
        pay_status = min(6, int(cobertura_meses))
    elif reajuste < 0:
        pay_status = -1
    else:
        pay_status = 0

    bill_base = estoque_valor
    pay_base = consumo_mensal_valor

    features = {
        "LIMIT_BAL": min(impacto_anual * 1.2, 1_000_000),
        "SEX": 1,
        "EDUCATION": education,
        "MARRIAGE": 1,
        "AGE": min(max(int(prazo), 21), 79),
        "PAY_0": pay_status,
        "PAY_2": max(pay_status - 1, -2),
        "PAY_3": pay_status,
        "PAY_4": min(pay_status + 1, 8),
        "PAY_5": pay_status,
        "PAY_6": max(pay_status - 1, -2),
        "BILL_AMT1": bill_base,
        "BILL_AMT2": bill_base * 0.95,
        "BILL_AMT3": bill_base * 0.9,
        "BILL_AMT4": bill_base * 0.88,
        "BILL_AMT5": bill_base * 0.85,
        "BILL_AMT6": bill_base * 0.82,
        "PAY_AMT1": pay_base,
        "PAY_AMT2": pay_base * 0.9,
        "PAY_AMT3": pay_base * 1.05,
        "PAY_AMT4": pay_base * 0.95,
        "PAY_AMT5": pay_base * 1.0,
        "PAY_AMT6": pay_base * 0.85,
    }
    return {k: features[k] for k in FEATURE_COLUMNS}
