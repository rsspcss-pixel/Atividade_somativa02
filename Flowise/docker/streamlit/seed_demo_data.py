"""
Valida e prepara dados demo (documentos + CSV) para o chat Lumina Cosmetics.

Uso (na pasta docker/streamlit):
  python seed_demo_data.py
  python seed_demo_data.py --generate-csv   # gera insumos_cosmeticos_02..05 se ausentes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app_paths import DATA_DIR, APP_ROOT

if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from demo_assets import dataset_files, ensure_dataset, ensure_ml_model
REQUIRED_DOCS = (
    "perfil_empresa_lumina_cosmetics.txt",
    "guia_gestao_lotes_minimos_compra.txt",
    "catalogo_insumos_destaque_lumina.txt",
    "parametros_custo_armazenagem_e_servicos_logisticos.txt",
    "guia_prazo_validade_e_permanencia_estoque.txt",
)
DOCS_DIR = DATA_DIR / "documentos_negociacao"


def ensure_documents() -> list[str]:
    missing = [name for name in REQUIRED_DOCS if not (DOCS_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Documentos ausentes em {DOCS_DIR}: {missing}")
    return REQUIRED_DOCS


def ensure_csv(min_files: int = 1) -> list[Path]:
    files = dataset_files()
    if len(files) < min_files:
        files = ensure_dataset(rows=800, files=max(min_files, 2))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara dados demo Lumina Cosmetics")
    parser.add_argument("--generate-csv", action="store_true", help="Forca geracao de CSV se ausente")
    parser.add_argument("--train-ml", action="store_true", help="Treina modelo ML")
    args = parser.parse_args()

    if args.generate_csv and not dataset_files():
        ensure_dataset(rows=800, files=2)

    docs = ensure_documents()
    csv_files = ensure_csv()
    if args.train_ml:
        ensure_ml_model(force=True)
    else:
        ensure_ml_model()
    total_rows = 0
    for path in csv_files:
        with path.open(encoding="utf-8") as fh:
            total_rows += max(0, sum(1 for _ in fh) - 1)

    print(f"OK: {len(docs)} documentos de conhecimento")
    print(f"OK: {len(csv_files)} arquivo(s) CSV, ~{total_rows} linhas de insumos")
    from ml.paths import MODEL_PATH

    print(f"OK: modelo ML em {MODEL_PATH} ({'existe' if MODEL_PATH.exists() else 'ausente'})")
    for doc in docs:
        size = (DOCS_DIR / doc).stat().st_size
        print(f"  - {doc} ({size} bytes)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
