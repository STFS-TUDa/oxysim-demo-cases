# Flat Flame Burner (LiPND diffusion flame, 0.95 stoichiometry)

This is the **Flat Flame Burner** demonstration case for
[oxysim-129](https://github.com/STFS-TUDa/oxysim-129),
run with `flameletCloudFoam`: a laminar, well-defined hot post-flame gas
stream (methane combustion products, ~1838 K) into which coal particles
are injected. Gas-phase chemistry is closed with a **non-premixed** FLUT
(coal volatiles as fuel, the hot methane product stream as oxidizer) --
with a single fuel stream, no multi-fuel blending dimensions (`Y`, `YY`)
are needed, making this the simplest possible `flameletCloudFoam`
configuration. Coal particles are tracked as a Lagrangian cloud
(devolatilization only -- char oxidation is disabled in this case) that
exchanges mass/energy source terms with the gas phase. The configuration
follows the flat flame burner studied by Nicolai et al. (2021)
[[1]](#reference).

## Geometry & boundary conditions

Axisymmetric-ish square-cross-section channel, 22mm x 22mm x 20mm
(`system/blockMeshDict`, 70x70x105 cells, graded toward the centerline).
Coal particles are injected on a small circular patch (`injectionPatch`,
1mm radius, cut out of the inlet) at the domain center; the hot carrier
gas enters through the rest of the inlet.

| Patch            | `U`             | `Z` | `ha`         | `yc`  |
|-------------------|-----------------|-----|--------------|-------|
| `INLET`           | (0, 0, 1.7) m/s | 0   | -162.2 kJ/kg | 0.193 |
| `injectionPatch`  | (0, 0, 1.7) m/s | 0   | -162.2 kJ/kg | 0.193 |
| `WALL`            | slip            | zeroGradient | zeroGradient | zeroGradient |
| `OUTLET`          | zeroGradient    | zeroGradient | zeroGradient | zeroGradient |

Both `INLET` and `injectionPatch` carry the same `Z`, `ha`, and `yc`.
`Z = 0` places this boundary on the pure-oxidizer side of the flamelet
manifold -- but the nonzero `yc` and this particular `ha` together
correspond to hot, **already-burnt** methane-air combustion products, not
cold or unreacted oxidizer. There is no direct temperature boundary
condition anywhere in this case: T is looked up from the FLUT via
`(Z, ha, yc)`, so `ha` is set to the specific value that reproduces the
correct post-flame temperature (~1838 K).

## Results

`system/controlDict` writes a y=0 centerline slice (`writeSurface`: U,
yc, Z, T, OH) and the coal cloud particle positions (`writeCloud`) at
every `postProcessing` interval, independent of the field-write interval.
The notebook [`visualization/laminar_coal.ipynb`](../visualization/laminar_coal.ipynb)
plots these files. The maximum T, Z, and `yc` over the slice climb sharply
over the first few steps as the flame cone establishes, then plateau (with
some fluctuation) once the flame reaches its sustained state (T stabilizes
around ~2184 K).

## How to run it

### 1. Build environment

Build oxysim-129 and set up your environment as described in its
[README](https://github.com/STFS-TUDa/oxysim-129#installation) (including
`scripts/source_local.sh`). Verify with `which flameletCloudFoam`.

### 2. Pull the case's flamelet table

The flamelet lookup table (~1GB) is tracked via Git LFS. Confirm it
actually pulled down real data, not a pointer file:

```bash
git lfs install   # one-time per machine
git lfs pull
file FLUT.h5   # should say "Hierarchical Data Format (version 5) data"
```

Its three input dimensions -- in table order, `Z` (mixture fraction), `ha`
(enthalpy, stored/un-normalized internally as `Hnorm`), `yc` (progress
variable, stored/un-normalized internally as `cc`) -- must match
`inputVariablesFlameletTable (Z ha yc)` in `constant/flameletProperties`
**in that order**. If you swap in a different FLUT, re-check that order
against the table's own metadata (`FLUT::LookupTable::getInputVariables()`),
don't assume it matches.

### 3. Build the mesh and run

```bash
./Allrun
```

which does, in order:

1. `blockMesh` -- reads `system/blockMeshDict` directly.
2. `topoSet` + `createPatch -overwrite` -- cuts the 1mm-radius
   `injectionPatch` out of the inlet (`system/topoSetDict`'s
   `injectionCells` faceSet). This **must** run before `decomposePar`:
   every field in `0/` and `constant/coalCloudProperties`'s
   `patch injectionPatch` entry reference a patch that doesn't exist until
   this step runs.
3. `decomposePar` -- 20-way, `method scotch`.
4. `flameletCloudFoam -parallel`, then `reconstructPar -latestTime`.

Takes about two hours on 20 cores (for a Slurm
batch run, copy `submit_template.slm` to `submit_local.slm` and adapt it --
`numberOfSubdomains` in `decomposeParDict` must match `--ntasks-per-node`
there). `./Allclean` removes all generated output and
the mesh.

### Other ways to interact with the case

**Visualizing the results** -- open
[`visualization/laminar_coal.ipynb`](../visualization/laminar_coal.ipynb)
after a run; see [`visualization/README.md`](../visualization/README.md)
for the environment setup.

**Viewing the case in ParaView** -- create a `case.foam` file and open it:

```bash
touch case.foam
paraFoam -case case.foam   # or: paraview case.foam
```

## Setting up the models

### Particle phase: the coal cloud

Three things configure the Lagrangian particle side: declaring the cloud,
picking its devolatilization kinetics, and giving it a mechanism to look
up species enthalpies from -- needed for the heat carried away by the
volatiles it releases.

<details>
<summary><b>1. Declare the cloud in <code>system/controlDict</code></b></summary>

```
clouds
{
    coalCloud    carbonaceousCloud;
}
```

The name (`coalCloud` here) is arbitrary, but every other reference to the
cloud must then match it exactly: the properties file
`constant/<name>Properties` (here `coalCloudProperties`), the `cloud`
entry in the `writeCloud` function object, and every `cloudNames` list in
`flameletProperties` (gas-phase section below).

</details>

<details>
<summary><b>2. Select the devolatilization model and its coefficients</b></summary>

In `constant/coalCloudProperties`, disable the stock OpenFOAM selector and
enable the STFS C2SM extension:

```
devolatilisationModel     none;
devolatilisationModelSTFS C2SM;
```

then provide per-species Arrhenius coefficients for the Kobayashi
competing two-step rates `kappa1 = A1*exp(-E1/(R*Tp))`,
`kappa2 = A2*exp(-E2/(R*Tp))`:

```
C2SMCoeffs
{
    volatileData
    (
        // (species  alpha1  A1      E1        alpha2  A2      E2)
        (H2       0.484 1.65e5 4.8988e7 0.752 4.312e8 1.324e8)
        (H2O      0.484 1.65e5 4.8988e7 0.752 4.312e8 1.324e8)
        // ... one row per released species
    );
    residualCoeff 1e-6;
}
```

`alpha1`/`alpha2` are the fraction of each reaction's converted mass
released as gas rather than retained as char. The species listed here
must match what `speciesWeights` references in the gas-phase section below
-- this is what actually defines the fuel-stream composition.

</details>

<details>
<summary><b>3. Provide a Cantera mechanism for the volatiles' enthalpy</b></summary>

`flameletCloudFoam` takes the gas phase from the FLUT, but the particle
submodels still need per-species thermodynamics, which they get from a
Cantera-format YAML mechanism (`constant/ITV_mechanism.yaml`, set via
`mechanismFile` in `thermophysicalProperties`). Here it supplies molecular
weights and the enthalpy of each released volatile species, needed for the
particle's enthalpy source `cloud.Sha()` (gas-phase section below). It
never touches the mechanism's kinetics: reaction progress comes from the
FLUT, not from integrating this file.

Only the species the cloud releases are needed, and each species in the
file must also exist in `FLUT.h5`. This file carries all 100 FLUT species.
It is the ITV mechanism of Cai et al. (2021) [[2]](#reference), converted
from `ITV.xml` with `ctml2yaml`.

Disable reactions at the phase level so Cantera doesn't build an unused
reaction network at every startup:

```yaml
phases:
- name: gas
  ...
  kinetics: gas
  reactions: none   # not "all" -- chemistry is closed via the FLUT
```

The file still contains its 734 reaction definitions; `reactions: none`
keeps Cantera from loading them. (Verified:
`cantera.Solution("constant/ITV_mechanism.yaml")` reports
`n_species == 100`, `n_reactions == 0`.)

</details>

### Gas phase: the flamelet model

Every FLUT-transported control variable `phi` -- here `Z`, `yc`, and `ha`
-- satisfies the same general scalar transport equation: unsteady transport
plus convection plus diffusion, balanced by a chemical source `omega_phi`
from the FLUT (nonzero only for `yc`) and a particle source `S_phi^p`. See
the [oxysim-129 repository](https://github.com/STFS-TUDa/oxysim-129) for the
full equation.

`constant/flameletProperties` configures both which of these actually get
solved, and how each source term is built:

- `SZ`, `Syc` (`updateType particleSource`): **not** instances of that
  equation themselves. Each time step they're recomputed from scratch as
  the mass- and species-weighted sum of the coal cloud's devolatilization
  source (`cloud.Srho`, `speciesWeights`) -- they only exist to be the
  right-hand side `Z`'s and `yc`'s own equations use.
- `Z` (`updateType unityLewis_particleSource`): the actual transport
  equation for mixture fraction, sourced only by `SZ` -- Z is conserved,
  so there's no chemical source.
- `yc` (`updateType unityLewis_sourceTerm_particleSource`): same transport
  form as `Z`, but with two source terms: the chemical reaction rate
  `omega_yc` looked up from the FLUT, and the particle source `Syc`.
- `ha` (`updateType unityLewis_particleEnthalpySource`): transported
  directly with a particle heat-exchange source computed from the cloud's
  own `Sha()` (not routed through a separate `Sha` field the way `SZ`/`Syc`
  are), using the volatile enthalpies from the Cantera mechanism above. No
  `constant/radiationProperties` file exists in this case, so the
  radiative contribution is always zero -- OpenFOAM defaults to
  `radiationModel none` when the file is absent, it doesn't error.

Concretely:

```
flutFile "FLUT.h5";
inputVariablesFlameletTable (Z ha yc);
variablesToSolve (SZ Z ha Syc yc);

variableEquations
{
    SZ
    {
        updateType     particleSource;
        cloudNames     (coalCloud);
        speciesWeights (...);
    }
    Z
    {
        updateType     unityLewis_particleSource;
    }
    Syc
    {
        updateType     particleSource;
        cloudNames     (coalCloud);
        speciesWeights (...);
    }
    yc
    {
        updateType     unityLewis_sourceTerm_particleSource;
    }
    ha
    {
        updateType     unityLewis_particleEnthalpySource;
        cloudNames     (coalCloud);
    }
}
```

`cloudNames` here must match the name declared under "particle phase"
above. `inputVariablesFlameletTable` must match the table's own input
dimensions in the exact same order. `variablesToSolve` also fixes the
solve order: only the variables listed here are solved at all, and the
particle sources (`SZ`, `Syc`) must come before the fields they feed --
an entry defined under `variableEquations` but left out of
`variablesToSolve` just stays at its zero-initialised default for the
whole run, with no error.

## Case files

- `0/` -- initial conditions.
- `constant/*Properties`, `constant/thermophysicalProperties`,
  `constant/ITV_mechanism.yaml` -- gas and cloud model configuration.
  `thermophysicalProperties` points at `constant/ITV_mechanism.yaml`
  (100 species, matching the FLUT's species set) because
  `flameletCloudFoam` always constructs a `canteraThermo`.
- `system/` -- mesh, numerics, and function-object (`controlDict`) setup.
- `constant/polyMesh/` is generated by `./Allrun`.

## Reference

When citing this case, cite the DOI of these demo cases (see the
[top-level README](../README.md#how-to-cite)) together with paper 1 below.

1. Nicolai et al. (2021) doi:[10.1016/j.proci.2020.06.081](https://doi.org/10.1016/j.proci.2020.06.081) — Numerical investigation of pulverized coal particle group combustion using tabulated chemistry; this case's configuration follows theirs.
2. Cai et al. (2021) doi:[10.1007/s10494-020-00138-w](https://doi.org/10.1007/s10494-020-00138-w) — A Methane Mechanism for Oxy-Fuel Combustion: Extinction Experiments, Model Validation, and Kinetic Analysis; source of `constant/ITV_mechanism.yaml`.
