#!/usr/bin/env bash
set -euo pipefail

# Run from the RescueMesh application directory (the directory containing main.py).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "$ROOT/.." && pwd)"
OUT="$PROJECT_ROOT/RescueMesh_submission.zip"

cd "$ROOT"
rm -f "$OUT"

zip -r "$OUT" \
  main.py config.py scenario.py scenario_generator.py simulation.py \
  classical_solver.py quantum_solver.py qubo_model.py evaluation.py \
  graph_generator.py visualization.py requirements.txt README.md \
  scenarios tests report results \
  -x "*/__pycache__/*" "*.pyc" "*.pyo" "*.DS_Store" \
     "*/.venv/*" "*/venv/*" "*/.pytest_cache/*"

echo "Created: $OUT"
echo "Review the archive contents before submission:"
unzip -l "$OUT"
