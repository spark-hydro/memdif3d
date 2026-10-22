# memdif3d

Membrane diffusion in 3D: a fully mixed source cell leaks through a membrane into a porous medium, solved with an explicit finite-volume scheme on a regular grid (1 mm cells, 1 minute steps). It replaces a spreadsheet model that had to be run in pieces by hand.

**Status: early development.** The solver runs the Reduced_Matrix case (28 days in about 2 s on one core) and passes its regression tests against a Python prototype of the model. It has not yet been compared with a full-length spreadsheet run. The model definition is in [docs/MODEL_SPEC.md](docs/MODEL_SPEC.md), the input files in [docs/INPUT_SPEC.md](docs/INPUT_SPEC.md).

## Layout
| Folder | Content |
|---|---|
| `src/` | Fortran source |
| `docs/` | model specification (`MODEL_SPEC.md`) and input file formats (`INPUT_SPEC.md`) |
| `excel/` | `DailyRun.bas`, VBA that runs the spreadsheet model one day at a time (used to produce reference results) |
| `tools/` | Python: `xlsx2memdif.py` turns the spreadsheet into input files, `memdif_proto.py` is a prototype solver that reads them, `ref_step.py` and `test_vs_excel.py` check the specification |
| `data/reduced_matrix/` | input set generated from `Reduced_Matrix.xlsx` (first test case) |
| `tests/` | regression tests (to come) |

## Build
See [BUILD.md](BUILD.md). Quick start on Linux:
```
cmake --preset gfortran_release_linux
cmake --build build/release
ctest --test-dir build/release --output-on-failure
```

## Run
```
mkdir run1 && cd run1
../build/release/memdif3d ../data/reduced_matrix/memdif3d.nam
```
Writes `field_001.csv` ... (one per day), `probes_001.csv` ... (one row per minute) and restart files in the current folder. Run the same command again after an interruption to continue from the last finished day; add `--fresh` to start over.

## Plan
1. Input in MODFLOW 6 style text packages: done (format, generator, example set, Fortran reader).
2. Solver, daily output, probes, restart: done.
3. Compare a long run with the spreadsheet / VBA daily files; more example cases (sorption, advection, other geometries).
4. OpenMP tuning; optional binary output.

Licensed under the MIT License, see [LICENSE](LICENSE).
