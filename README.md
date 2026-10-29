[![Release](https://img.shields.io/github/v/release/spark-hydro/memdif3d?style=flat-square)](https://github.com/spark-hydro/memdif3d/releases)
[![Docker](https://ghcr-badge.egpl.dev/spark-hydro/memdif3d/latest_tag?trim=major&label=docker&color=%23007ec6)](https://github.com/spark-hydro/memdif3d/pkgs/container/memdif3d)
[![Build](https://img.shields.io/github/actions/workflow/status/spark-hydro/memdif3d/build.yml?branch=main&style=flat-square&label=build%20%2B%20regression%20test)](https://github.com/spark-hydro/memdif3d/actions/workflows/build.yml)
[![Docs](https://readthedocs.org/projects/memdif3d/badge/?version=latest&style=flat-square)](https://memdif3d.readthedocs.io/en/latest/)
[![Downloads](https://img.shields.io/github/downloads/spark-hydro/memdif3d/total?style=flat-square)](https://github.com/spark-hydro/memdif3d/releases)
[![License](https://img.shields.io/github/license/spark-hydro/memdif3d?style=flat-square)](LICENSE)

# memdif3d

Membrane diffusion in 3D: a fully mixed source cell leaks through a membrane into a porous medium, solved with an explicit finite-volume scheme on a regular grid (1 mm cells, 1 minute steps). The membrane can have holes. Input is in MODFLOW 6 style text files. It replaces a spreadsheet model that had to be run in pieces by hand: a 28-day run now takes about 2 seconds on one core.

**Documentation: <https://memdif3d.readthedocs.io/en/latest/>** (quick start, theory, input and output files, how to build your own model, tools, validation)

![The model domain](docs/img/domain.png)

## Status
Version 0.1.1. The solver reproduces the spreadsheet model to rounding error: 2e-16 over all cells after 576 steps against the full workbook, against the output of the daily macro, and against a 32,820-step state saved in the workbook (see [docs/VALIDATION.md](docs/VALIDATION.md)). Sorption, advection and the membrane holes are tested against a Python prototype and a sealed-box mass balance, but not yet against a spreadsheet run.

Current limits: one source cell touching the membrane, one uniform sand and membrane, cubic cells, explicit time stepping. The notes in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) list the next steps.

## Get it
- **Ready-made programs** for Linux, Windows and Intel Linux are on the [releases page](https://github.com/spark-hydro/memdif3d/releases).
- **Docker**, with the Python tools included (see below).
- **From source**: see [BUILD.md](BUILD.md).

## Layout
| Folder | Content |
|---|---|
| `src/` | Fortran source |
| `docs/` | the manual (MkDocs, `mkdocs.yml`) |
| `excel/` | `DailyRun.bas`, VBA that runs the spreadsheet model one day at a time (used to produce reference results) |
| `tools/` | Python: input converters and generators, prototype solver, plots, animations, comparison with the spreadsheet |
| `data/reduced_matrix/` | the example input set (`rm.nam`, `rm.dis`, ...), generated from the corrected workbook `Reduced_Matrix_fixed.xlsx` |
| `tests/` | regression tests (run by `ctest`) |
| `docker/` | files of the Docker images |

## Build
```
cmake --preset gfortran_release_linux
cmake --build build/release
ctest --test-dir build/release --output-on-failure
```

## Docker
A ready-made image holds the model and the Python tools, so nothing but Docker is needed:
```
docker pull ghcr.io/spark-hydro/memdif3d:latest
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work ghcr.io/spark-hydro/memdif3d memdif3d /opt/memdif3d/data/reduced_matrix/rm.nam
```
The image (about 530 MB) includes numpy, matplotlib and plotly for the plotting tools. A small image without them (`:slim`, about 190 MB) installs them on first use. See [docs/docker.md](docs/docker.md).

## Run
```
mkdir run1 && cd run1
../build/release/memdif3d ../data/reduced_matrix/rm.nam
```
Writes `field_001.csv` ... (one per day), `probes_001.csv` ... (one row per minute) and restart files in the current folder. Run the same command again after an interruption to continue from the last finished day; add `--fresh` to start over.

## Pictures and animations
`tools/animate_3d.py` makes an interactive 3D animation (one HTML file; drag to rotate while it plays):
```
python tools/animate_3d.py run1 --nam data/reduced_matrix/rm.nam --log --out solute3d.html
```
`tools/animate_field.py` makes an animated GIF with a face view and a side view, each switched on or off, and `tools/animate_compare.py` puts two runs side by side. Membrane with holes: `python tools/make_holes.py data/reduced_matrix data/holes_p3 --pitch 3 --size 1` writes a new input set (a `FACES` map with holes). The scripts need numpy, matplotlib, Pillow and plotly (`conda env create -f environment.yml`), or use the Docker image. See [docs/tools.md](docs/tools.md).

## Contact
iHydro M&D, CECE Dept., Texas Tech University. Questions and bug reports: [GitHub issues](https://github.com/spark-hydro/memdif3d/issues).

Licensed under the MIT License, see [LICENSE](LICENSE).
