"""Shared helpers for the oxysim demo-case notebooks.

Both cases write the same kind of post-processing output:

    <case>/postProcessing/<sampler>/<time>/<surface>.vtp   y=0 slice, gas fields
    <case>/postProcessing/writeCloud/<cloud>.vtp.series    particle clouds

The slice is contoured on its *own* mesh triangulation, so nothing is drawn
outside cells that exist in the sampled surface (no grid interpolation into
burner blocks or other non-fluid regions).
"""
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
import pyvista as pv

# Axis / colorbar labels as "quantity / unit"; unknown fields fall back to their name.
LABELS = {
    "x": "x / mm", "y": "y / mm", "z": "z / mm", "t": "t / s",
    "T": "T$_\\mathrm{gas}$ / K", "Z": "Z", "yc": "y$_c$", "OH": "OH",
    "|U|": "|U| / m s$^{-1}$",
}
# Particle arrays: (colorbar label, factor applied to the raw value)
PARTICLE_LABELS = {
    "T": ("T$_\\mathrm{particle}$ / K", 1.0),
    "d": ("particle d / \u00b5m", 1e6),
}
M_TO_MM = 1e3  # slice/cloud coordinates are in m, plots are in mm


def set_style():
    """Publication look (oxysim.mplstyle): inward ticks on all four edges, serif font.

    Needs no LaTeX installation and no extra package.
    """
    plt.style.use(Path(__file__).with_name("oxysim.mplstyle"))


def sample_times(sampler_dir):
    """Sorted list of (time, dirname) for all numeric time directories."""
    out = []
    for name in os.listdir(sampler_dir):
        try:
            out.append((float(name), name))
        except ValueError:
            continue
    return sorted(out)


def load_slice(case, sampler, surface, time=None):
    """Read one sampled surface; `time=None` takes the latest, otherwise the nearest.

    Returns the triangulated slice with cell data converted to point data,
    and the time actually used.
    """
    sampler_dir = os.path.join(case, "postProcessing", sampler)
    times = sample_times(sampler_dir)
    if not times:
        raise FileNotFoundError(f"no time directories in {sampler_dir}")
    t, name = times[-1] if time is None else min(times, key=lambda tn: abs(tn[0] - time))
    mesh = pv.read(os.path.join(sampler_dir, name, surface))
    return mesh.cell_data_to_point_data().triangulate(), t


def load_cloud(case, sampler, cloud, time):
    """Read the cloud snapshot nearest to `time`; returns (PolyData, time used)."""
    cloud_dir = os.path.join(case, "postProcessing", sampler)
    with open(os.path.join(cloud_dir, f"{cloud}.vtp.series")) as fh:
        files = json.load(fh)["files"]
    best = min(files, key=lambda r: abs(r["time"] - time))
    return pv.read(os.path.join(cloud_dir, best["name"])), best["time"]


def values(mesh, field):
    """Point data by name; `"|U|"` gives the velocity magnitude."""
    if field == "|U|":
        return np.linalg.norm(np.asarray(mesh.point_data["U"], dtype=float), axis=1)
    return np.asarray(mesh.point_data[field], dtype=float)


def _colorbar(ax, mappable, label, y0=0.0, height=1.0):
    """Colorbar in an inset just right of `ax`, spanning [y0, y0 + height] of its height."""
    cax = ax.inset_axes([1.03, y0, 0.04, height])
    return ax.figure.colorbar(mappable, cax=cax, label=label)


def plot_slice(ax, mesh, field, cloud=None, cloud_color=None, plane_tol=None,
               axes=("x", "z"), cmap="viridis", levels=100, label=None,
               particle_cmap="gray_r", particle_size=2.0, particle_size_by=None,
               particle_size_ref=60e-6):
    """Contour `field` of a slice on `ax`, optionally overlaying cloud particles.

    axes       which coordinates go on the horizontal / vertical axis; the
               default puts z (the flow direction) up
    cloud      particle PolyData; only particles with |y| < plane_tol are drawn
    particle_cmap  default gray_r: white = cold, black = hot
    particle_size  constant marker area in pt^2 (used when particle_size_by is None)
    particle_size_by  particle array (e.g. "d") the marker area scales with:
               area [pt^2] = value / particle_size_ref
    particle_size_ref  value that gets a marker area of 1 pt^2 (default 60e-6, i.e.
               a 60 um particle)
    cloud_color  particle array to colour by (e.g. "T"); black if None. With a
               particle colorbar, the gas and particle colorbars are stacked
               (gas on top), each 45% of the axes height; otherwise the gas
               colorbar spans the full axes height.
    """
    idx = {"x": 0, "y": 1, "z": 2}
    h, v = idx[axes[0]], idx[axes[1]]
    pts = mesh.points
    faces = mesh.faces.reshape(-1, 4)[:, 1:]
    # Explicit Triangulation: passing `triangles=` next to x, y, z in
    # tricontourf is silently ignored and falls back to a Delaunay
    # retriangulation of the point cloud, which fills in non-fluid regions.
    triang = mtri.Triangulation(pts[:, h] * M_TO_MM, pts[:, v] * M_TO_MM, triangles=faces)
    tcf = ax.tricontourf(triang, values(mesh, field), levels=levels, cmap=cmap)
    stacked = cloud is not None and cloud.n_points and cloud_color is not None
    gas_slot = (0.55, 0.45) if stacked else (0.0, 1.0)
    _colorbar(ax, tcf, label or LABELS.get(field, field), *gas_slot)

    if cloud is not None and cloud.n_points:
        p = cloud.points
        near = np.abs(p[:, 1]) < plane_tol if plane_tol else np.ones(len(p), bool)
        ph, pv_ = p[near, h] * M_TO_MM, p[near, v] * M_TO_MM
        size = particle_size
        if particle_size_by is not None:
            size = np.asarray(cloud.point_data[particle_size_by], dtype=float)[near] / particle_size_ref
        if cloud_color is None:
            ax.scatter(ph, pv_, c="k", s=size, linewidths=0)
        else:
            plabel, factor = PARTICLE_LABELS.get(cloud_color, (f"particle {cloud_color}", 1.0))
            sc = ax.scatter(ph, pv_, c=np.asarray(cloud.point_data[cloud_color])[near] * factor,
                            cmap=particle_cmap, s=size, edgecolors="none")
            _colorbar(ax, sc, plabel, 0.0, 0.45)

    ax.set_aspect("equal")
    ax.set_xlabel(LABELS[axes[0]])
    ax.set_ylabel(LABELS[axes[1]])
    return tcf
