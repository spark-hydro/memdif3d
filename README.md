# memdif3d

[![Documentation Status](https://readthedocs.org/projects/memdif3d/badge/?version=latest)](https://memdif3d.readthedocs.io/en/latest/)

**Documentation: <https://memdif3d.readthedocs.io/en/latest/>**

Membrane diffusion in 3D: a fully mixed source cell leaks through a membrane into a porous medium, solved with an explicit finite-volume scheme on a regular grid (1 mm cells, 1 minute steps). It replaces a spreadsheet model that had to be run in pieces by hand.

**Status: early development.** The solver runs the Reduced_Matrix case (28 days in about 2 s on one core) and passes its regression tests against a Python prototype of the model. It has not yet been compared with a full-length spreadsheet run. The model definition is in [docs/MODEL_SPEC.md](docs/MODEL_SPEC.md), the input files in [docs/INPUT_SPEC.md](docs/INPUT_SPEC.md).

**Manual:** the online manual above is built from the pages in `docs/`, which form a manual (quick start, theory, input and output files, how to build your own model, tools, validation). Build it with `pip install -r requirements-docs.txt && mkdocs serve`, see [docs/install.md](docs/install.md).

## Layout
| Folder | Content |
|---|---|
| `src/` | Fortran source |
| `docs/` | the manual (MkDocs, `mkdocs.yml`): quick start, theory, input and output files, build your own model, tools, validation |
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

## Animations
`tools/animate_3d.py` makes an interactive 3D animation (one HTML file; drag to rotate while it plays):
```
python tools/animate_3d.py run1 --nam data/reduced_matrix/memdif3d.nam --log --out solute3d.html
```
Membrane with holes: `python tools/make_holes.py data/reduced_matrix data/holes_p3 --pitch 3 --size 1` writes a new input set (a `FACES` map with holes, see docs/INPUT_SPEC.md).

`tools/animate_field.py` turns the daily field files into an animated GIF, with the face view and the side view each switched on or off:
```
python3 tools/animate_field.py run1 --nam data/reduced_matrix/memdif3d.nam --out solute.gif
python3 tools/animate_field.py run1 --nam data/reduced_matrix/memdif3d.nam --side off        # face view only
python3 tools/animate_field.py run1 --nam data/reduced_matrix/memdif3d.nam --face off --log  # side view, log colours
```
Other options: `--side-plane xz|yz`, `--slice`, `--face-z`, `--vmax`, `--fps`, `--every`. It needs numpy, matplotlib and Pillow: `conda env create -f environment.yml && conda activate memdif3d`. The frames are the field files. For finer time resolution inside a long run use `--snapshot-every 60` (one field file per hour for a 1-minute step) and `--pattern 'snap_*.csv'`.

## Plan
1. Input in MODFLOW 6 style text packages: done (format, generator, example set, Fortran reader).
2. Solver, daily output, probes, restart: done.
3. Compare a long run with the spreadsheet / VBA daily files. Done: tests on a second geometry (off-centre source, sorption, advection) and a sealed box with an analytic answer.
4. OpenMP tuning; optional binary output.

Licensed under the MIT License, see [LICENSE](LICENSE).
