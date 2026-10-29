# Build your own model

A model is a folder of small text files that a name file lists. The quickest way to a new case is to copy an existing set and change what differs. This page goes from the easy changes to a new grid, with the tools that exist today.

!!! note "Status"
    There is no generator for a new box yet, so a new grid means writing the three array files (`IDOMAIN`, `STRT`, `ADVMASK`) yourself, see step 7. A ready-made box generator is planned. Everything before step 7 needs no programming.

## The files in a set
| File | Holds | Change it to |
|---|---|---|
| `rm.nam` | the list of packages | rename or add a package |
| `.tdis` | step length, steps per period, number of periods | run longer or shorter |
| `.dis` | grid size and `IDOMAIN` | change the geometry |
| `.ic` | start concentration of every cell | start from another state |
| `.dsp`, `.mst` | diffusion, tortuosity, porosity, length; bulk density and Kd | change the materials |
| `.src` | source volume and start concentration, the `FACES` map | change the source and the membrane |
| `.adv` | flow velocity and the mask where it acts | add flow |
| `.bnd` | boundary rules, exceptions, neighbour overrides | change the outer boundary |
| `.oc` | which outputs to write, and the probe cells | change the output |

Details of every file are in [Input files](INPUT_SPEC.md).

## 1. Copy a template
```bash
cp -r data/reduced_matrix data/mycase
```

Use `reduced_matrix` as the template. Its files are called `rm.*`; keep or change the names, but update the package list in the `.nam` file to match.

## 2. Change the run
In `.tdis`: `STEP_LENGTH` (minutes), `STEPS_PER_PERIOD` and `NPERIODS`. For a quick test you do not need to edit anything: `--nperiods 1 --steps-per-period 10`.

## 3. Change the materials
In `.dsp`, set `DIFFUSION`, `TORTUOSITY`, `POROSITY` and `LENGTH` for `sand` and `membrane`; the program computes \(K = D\phi/(L\tau)\). In `.mst`, set `POROSITY`, `BULK_DENSITY` and `KD` for the retardation \(R = \phi + \rho_b K_d\).

After a change, start the program once and read the stability line (`largest coefficient sum`, limit 1). If it is above 1, reduce the step length (or the diffusion coefficient, or raise the retardation).

## 4. Change the source
In `.src`, set `VOLUME` (mm³) and `START_CONC`. Keep the number consistent with the footprint: a 15 × 15 mm footprint with 25 mm depth is 5625 mm³.

## 5. Change the membrane
The `FACES` map in `.src` has one line per layer with one value per row: 0 none, 1 membrane, 2 hole, 3 closed. Edit it by hand, or let a script punch a regular pattern of holes:

```bash
python tools/make_holes.py data/mycase data/mycase_holes --pitch 3 --size 2 --closed
```

`--pitch` is the distance between holes in faces, `--size` the hole edge, `--offset` the first hole, and `--closed` makes the membrane between the holes impermeable. The script prints the pattern. A face needs a fluid cell (`IDOMAIN = 1`) at `ICOL = 1` under it.

## 6. Change the boundary
In `.bnd`, the `boundary` block has one line per side of the box:

```text
BEGIN boundary
  IROW=1     COPY 0.82
  IROW=NROW  COPY 0.82
  ICOL=NCOL  COPY 0.82
  ILAY=1     COPY 0.82
  ILAY=NLAY  COPY 0.82
END boundary
```

Use `COPY factor` for a leaky edge (a factor below 1 drains solute), `NOFLOW` for a sealed wall, `FIXED value` for a constant concentration. A side without a line keeps its start value. For a sealed box, leave out the boundary cells altogether: no `IDOMAIN = 2` cells and an empty `boundary` block. Delete the `boundary_cells` and `neighbor_overrides` lists if your set has them.

## 7. A new grid
Change the dimensions in `.dis` and write the three arrays in the order *column fastest, then row, then layer*, one `# ILAY n` tile per layer. The rules of the Reduced_Matrix set, which you can follow or change:

- **`IDOMAIN`**: `2` for the outermost cells of the box on every side that has a boundary rule, `0` for the solid plate (the cells at `ICOL` 1 to 3 outside the membrane footprint), `1` everywhere else.
- **`STRT`**: 0 in every cell, solid and boundary cells included. The source concentration is `START_CONC` in `.src`, not in the array.
- **`ADVMASK`**: 1 where flow acts (fluid cells except the cells at `ICOL` 1 to 3 under the footprint), 0 elsewhere. With `VELOCITY 0` in `.adv` it has no effect.
- **`FACES`**: a map of the plane `ICOL = 1`, with 1 over the footprint and 0 elsewhere.

`tools/make_test_case.py` writes small complete sets for the tests (an off-centre source, a sealed box) and is a working example of how the arrays are generated; read it as a template.

## 8. Check the set before a long run
1. **Look at it.** `python tools/plot_domain.py data/mycase/rm.nam --out domain.png` draws the geometry to scale (source, membrane faces, plate, sand, boundary cells). `python tools/plot_domain_3d.py ...` makes an interactive 3D version.
2. **Run a few steps.** `memdif3d data/mycase/rm.nam --nperiods 1 --steps-per-period 10` in an empty folder. The log prints the counts of fluid and boundary cells and source faces: they should be what you drew.
3. **Test the mass.** A sealed box (no boundary cells) conserves \(V\,C_M + R\sum C\) to rounding error. A faulty geometry usually shows up here first.
4. **Compare with the prototype.** `python tools/memdif_proto.py` reads the same files with independent code, and `ctest` shows how the regression tests compare it with the Fortran output.

## Tips
- Run every simulation in its own folder.
- Keep one folder for each input set, and give the name file a `TITLE`.
- When a run is finished, running the same command does nothing; use `--fresh` to start again.
