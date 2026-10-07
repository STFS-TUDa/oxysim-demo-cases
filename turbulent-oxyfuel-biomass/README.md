# OXY27 Multiphase Burner (walnut shell oxy-fuel combustion)

Demonstration case for [oxysim-129](https://github.com/STFS-TUDa/oxysim-129),
run with `flameletCloudFoam`: a turbulent (LES, `sigma` subgrid model),
oxy-fuel (27% O2) multi-annular burner firing pulverized walnut shells.
Gas-phase chemistry is closed with a FLUT parametrized by `(Z, Y, YY, ha,
yc, Zvar)` -- two fuel streams (`Y`, `YY` handle multi-fuel blending),
plus a variance-normalized mixture-fraction-variance dimension (`Zvar`,
normalized internally against `Z` by `flut-reader`'s `VarianceNormSpec`).
Walnut particles are tracked as a Lagrangian cloud (`walnutCloud`,
`carbonaceousCloud` / `ReactingMultiphaseParcelSTFS`) undergoing
devolatilization and char oxidation, radiatively coupled to the gas phase
through `fvDOMwsgg` with a binary WSGG absorption/emission model
(gas + particle cloud grey contribution). This case reproduces the 27
vol% O2 operating point studied by Vahl et al. (2026) [[1]](#reference).

## Geometry & boundary conditions

Multi-annular burner: a central particle-carrying jet plus three
concentric oxidizer annuli.

| Patch               | `U`                          | `Z` | `ha`        | `yc`  | Notes |
|---------------------|-------------------------------|-----|-------------|-------|-------|
| `PRIMARY`           | axial, time-ramped table       | 0.0777 | -6.87e6 | 8.39  | Walnut particle injection (`patchInjection`) |
| `STRAIGHTSECONDARY` | fixed, axial                   | 0   | -7.05e6 | 9.10  | Oxidizer |
| `INCLINEDSECONDARY` | axial, time-ramped table        | 0   | -7.05e6 | 9.10  | Oxidizer |
| `TERTIARY`          | axial, time-ramped table        | 0   | -7.05e6 | 9.10  | Oxidizer |
| `SOLSOL`            | zeroGradient                    | zeroGradient | zeroGradient | zeroGradient | Coded wall temperature BC (`TemperatureBC`, fixed 300K here) |
| `OUTOUT`            | zeroGradient                    | zeroGradient | zeroGradient | zeroGradient | Outlet |

There is no direct temperature field solved: `T` is looked up from the
FLUT via `(Z, Y, YY, ha, yc, Zvar)`. The wall-radiation boundary FLUT
(`FLUT_BC.h5`) additionally requires `TemperatureBC` as a hard input
(`ccBoundary` is optional and defaults to zero if absent).

## Case files

The case starts from `6.87/`, a checkpoint of the production run (there is
no `t=0`). `constant/polyMesh/` is tracked via Git LFS, since the case has
no meshing pipeline.

**Mechanism file.**
`Base_PAH_Anisole_mech_noIX_onlyOutputSpecies_N2toCO.yaml` (18 species,
 converted with `ck2yaml` from the Base_PAH_Anisole CHEMKIN files) is used only as a thermodynamic species
database for the particle submodels, not for kinetics. Each of its species
must exist in the FLUT.

The char-oxidation model also needs O2, CO and CO2 in it, plus its
`dummySpecies`: since CO is also a devolatilisation product, the CO
released by char oxidation is booked on the dummy species (`N2` here)
instead of on CO. N2 matches CO's properties.

## How to run it

### 1. Build environment

Build oxysim-129 and set up your environment as described in its
[README](https://github.com/STFS-TUDa/oxysim-129#installation) (including
`scripts/source_local.sh`). Verify with `which flameletCloudFoam`.

### 2. Supply the flamelet tables

`FLUT.h5` (~18GB) and `FLUT_BC.h5` (~11GB) are too large for GitHub and
are published on
[TUdatalib](https://tudatalib.ulb.tu-darmstadt.de/handle/tudatalib/5606).
Place them at `turbulent-oxyfuel-biomass/FLUT.h5` and
`turbulent-oxyfuel-biomass/FLUT_BC.h5`. There are two ways to get them:

**Browser.** Open the link above and download both files,
for example by opening it with a browser in a VNC session on your computing cluster.

**curl.** The repository's API also serves the files directly, so the browser
isn't needed and you can download the files from the CLI:

```bash
cd turbulent-oxyfuel-biomass
B=https://tudatalib.ulb.tu-darmstadt.de/server/api/core/bitstreams
curl -L -C - -o FLUT.h5    $B/725bd6fb-57fd-414b-a55d-48decd151925/content
curl -L -C - -o FLUT_BC.h5 $B/2d35049f-9e5a-4f6e-a9b7-b3b9985eda4a/content
```

- The long IDs are the files' identifiers in the repository (`FLUT.h5`
  and `FLUT_BC.h5` respectively); the URL ends in `/content` for both,
  so `-o` sets the filename.
- `-L` follows redirects.
- `-C -` resumes a partial download: if a transfer of these ~30GB is
  interrupted, re-run the same command and it continues where it stopped.

Check that the downloads are intact HDF5 files:

```bash
file FLUT.h5 FLUT_BC.h5   # should say "Hierarchical Data Format (version 5) data"
```

### 3. Decompose and run

```bash
decomposePar -fileHandler collated -time 6.87
mpirun -n 96 flameletCloudFoam -fileHandler collated -parallel
```

(`decomposeParDict`'s `numberOfSubdomains 96` must match the MPI rank
count.) For a Slurm batch run, copy `submit_template.slm` to
`submit_local.slm` (untracked), adapt it, and `sbatch submit_local.slm`. There is no
`Allrun`/`Allclean` for this case since the mesh is static and there is
no meshing step to script.

### 4. Reconstruct (optional)

Reconstructing a collated case takes very long, and long-running jobs are
not allowed on the login nodes of some HPC systems, so submit it as a
batch job (after copying `reconstruct_template.slm` to
`reconstruct_local.slm` and adapting it):

```bash
./submitReconstruct.sh <time>
```

This submits two independent single-core jobs, `reconstructPar
-no-lagrangian` for the fields and `-no-fields` for the particle cloud, so
the cloud is done while the (longer) field reconstruction is still
running. For the production run this case was taken from, that was about
43 min for the fields and 7 min for the cloud.

## Reference

When citing this case, cite the DOI of these demo cases (see the
[top-level README](../README.md#how-to-cite)) together with the paper below.

1. Vahl et al. (2026) doi:[10.1016/j.fuel.2026.138602](https://doi.org/10.1016/j.fuel.2026.138602) — Large eddy simulations of swirl-stabilised gas-assisted oxy-fuel biomass flames under varying oxygen concentrations; this case reproduces its 27 vol% O2 operating point.
