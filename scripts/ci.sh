#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
bash fetch_data.sh
python build_warehouse.py
python run.py
python validation/validate_warehouse.py
python validation/validate.py
python late_risk.py
python -m pytest -q
python decision_brief.py
