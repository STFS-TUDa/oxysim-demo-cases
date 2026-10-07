#!/usr/bin/env bash
# Create the local virtual environment for the visualization notebooks.
#
# Usage:  ./setup_env.sh [python-executable]     (default: python3)
#
# HPC note: an active `module load` (e.g. ParaView) can put an incompatible
# `vtk` build on PYTHONPATH ahead of the venv's own, which breaks
# `import pyvista`. This script and the registered kernel therefore run
# with PYTHONPATH unset.
set -euo pipefail
cd "$(dirname "$0")"

PY="${1:-python3}"
"$PY" -m venv .venv
env -u PYTHONPATH .venv/bin/python -m pip install --upgrade pip
env -u PYTHONPATH .venv/bin/python -m pip install -r requirements.txt
env -u PYTHONPATH .venv/bin/python -m ipykernel install --user \
    --name oxysim-viz --display-name "oxysim-viz"

echo
echo "Done. Start with:  env -u PYTHONPATH .venv/bin/jupyter lab"
