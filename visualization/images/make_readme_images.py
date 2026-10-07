"""Render the latest time step of each case for the top-level README.

Usage (from visualization/images/, with the venv's Python):
    ../.venv/bin/python make_readme_images.py --laminar PATH --turbulent PATH
The images are written next to this script unless --out is given.

Same plot as the first cell of each notebook: gas temperature on the y=0 slice
with the particle cloud coloured by temperature.
"""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # oxysim_viz.py lives in visualization/
import oxysim_viz as ov  # noqa: E402

CASES = {
    "laminar-coal": dict(samplerSurface="writeSurface", surface="slice.vtp", samplerCloud="writeCloud", cloud="coalCloud",
                         plane_tol=2e-3, figsize=(6, 5), plot=dict(particle_size=8)),
    "turbulent-oxyfuel-biomass": dict(samplerSurface="writeSurface", surface="slice_y.vtp", samplerCloud="writeCloud", cloud="walnutCloud", plane_tol=0.03, figsize=(6, 9), plot=dict(particle_size_by="d")),
}


def render(name, case_dir, out_dir):
    c = CASES[name]
    mesh, t = ov.load_slice(case_dir, c["samplerSurface"], c["surface"])
    cloud, _ = ov.load_cloud(case_dir, c["samplerCloud"], c["cloud"], t)
    fig, ax = plt.subplots(figsize=c["figsize"], dpi=200)
    ov.plot_slice(ax, mesh, "T", cloud=cloud, cloud_color="T", plane_tol=c["plane_tol"],
                  cmap="inferno", **c["plot"])
    out = out_dir / f"{name}.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"{name}: t = {t} s -> {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--laminar", default=HERE.parent.parent / "laminar-coal", type=Path)
    ap.add_argument("--turbulent", default=HERE.parent.parent / "turbulent-oxyfuel-biomass", type=Path)
    ap.add_argument("--out", default=HERE, type=Path)
    args = ap.parse_args()

    ov.set_style()
    args.out.mkdir(exist_ok=True)
    render("laminar-coal", args.laminar, args.out)
    render("turbulent-oxyfuel-biomass", args.turbulent, args.out)


if __name__ == "__main__":
    main()
