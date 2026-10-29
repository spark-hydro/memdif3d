# Install and build

## Requirements
- a Fortran 2008 compiler: gfortran 13 or newer, or Intel ifx
- CMake 3.22 or newer, and make
- Python 3 for the tools and the tests (numpy, matplotlib and Pillow for the animations, plotly for the interactive 3D pictures)

## Linux
```bash
cmake --preset gfortran_release_linux
cmake --build build/release
ctest --test-dir build/release --output-on-failure
build/release/memdif3d --version
```

The tests take about 15 seconds. A debug build (array bounds checks, floating-point traps) uses the preset `gfortran_debug_linux`. Without presets:

```bash
cmake -B build -D CMAKE_Fortran_COMPILER=gfortran -D CMAKE_BUILD_TYPE=Release
cmake --build build
```

## Intel ifx (Linux)
```bash
source /opt/intel/oneapi/setvars.sh
cmake --preset ifx_release
cmake --build build/ifx_release
```

The Intel runtime is linked statically.

## Windows
In an MSYS2 UCRT64 shell:

```bash
pacman -S mingw-w64-ucrt-x86_64-gcc-fortran mingw-w64-ucrt-x86_64-cmake make
cmake --preset gfortran_release_windows
cmake --build build/release
```

The Windows build has not been run on GitHub yet.

## Docker
A container image with the model and the Python tools avoids all of this: see [Run with Docker](docker.md).

## Python environment for the tools
```bash
conda env create -f environment.yml
conda activate memdif3d
```

This installs numpy, matplotlib, Pillow and plotly. The input converters and the prototype solver need only the Python standard library.

## Tests
`ctest` runs the version checks, the input-file check, a full regression of the field and probe output against a Python prototype (with restart and `--fresh`), tests on other geometries (off-centre source, sorption, advection, holes, a sealed box with an analytic end state, bad input, the stability guard) and a smoke test of the animation script.

## Building this manual
```bash
pip install -r requirements-docs.txt
mkdocs serve        # preview at http://127.0.0.1:8000
mkdocs build --strict
```
