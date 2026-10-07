# Visualization

Jupyter notebooks for plotting the output of both demonstration cases. They
read the VTK files that each case's `system/controlDict` writes into its
`postProcessing/` directory, so run the case first (or point a notebook at
existing output).

| Notebook | Reads |
|---|---|
| [`laminar_coal.ipynb`](laminar_coal.ipynb) | `laminar-coal/postProcessing/writeSurface/*/slice.vtp`, `laminar-coal/postProcessing/writeCloud/coalCloud.vtp.series` |
| [`turbulent_oxyfuel_biomass.ipynb`](turbulent_oxyfuel_biomass.ipynb) | `turbulent-oxyfuel-biomass/postProcessing/writeSurface/*/slice_y.vtp`, `turbulent-oxyfuel-biomass/postProcessing/writeCloud/walnutCloud.vtp.series` |

Shared loading and plotting code lives in [`oxysim_viz.py`](oxysim_viz.py).
Slices are contoured on their own mesh triangulation, so non-fluid regions
(e.g. the burner block) stay empty instead of being interpolated over.

## Setup

```bash
cd visualization
./setup_env.sh            # creates .venv, installs requirements.txt, registers the "oxysim-viz" kernel
env -u PYTHONPATH .venv/bin/jupyter lab
```

Select the `oxysim-viz` kernel. `PYTHONPATH` is unset on purpose: an HPC
`module load` (e.g. ParaView) can put an incompatible `vtk` build ahead of
the venv's own, which breaks `import pyvista`.

## Pointing a notebook at other output

Each notebook has a `CASE` variable at the top (default: the case directory
in this repo) and a `TIME` variable (`None` = latest available). `CASE` can
also be overridden with the environment variables `OXYSIM_LAMINAR_CASE` and
`OXYSIM_TURBULENT_CASE`.
