# memdif3d

Membrane diffusion in 3D: a fully mixed source cell leaks through a membrane into a porous medium, solved with an explicit finite-volume scheme on a regular grid (1 mm cells, 1 minute steps). It replaces a spreadsheet model that had to be run in pieces by hand.

**Status: early development.** The program currently builds and reports its version; the solver is not written yet. The model definition is in [docs/MODEL_SPEC.md](docs/MODEL_SPEC.md).

## Layout
| Folder | Content |
|---|---|
| `src/` | Fortran source |
| `docs/` | model specification |
| `excel/` | `DailyRun.bas`, VBA that runs the spreadsheet model one day at a time (used to produce reference results) |
| `tools/` | Python scripts that extract the model from the spreadsheet and check the specification |
| `tests/`, `data/` | regression tests and example inputs (to come) |

## Build
See [BUILD.md](BUILD.md). Quick start on Linux:
```
cmake --preset gfortran_release_linux
cmake --build build/release
ctest --test-dir build/release --output-on-failure
```

## Plan
1. Input in MODFLOW 6 style text packages (name file, TDIS, DIS, IC, DSP/MST, SRC, BND, OC).
2. Solver reproducing the spreadsheet to rounding error.
3. Regression test against the spreadsheet results.

Licensed under the MIT License, see [LICENSE](LICENSE).
