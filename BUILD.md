# Building memdif3d

Requirements: a Fortran 2008 compiler (gfortran 13 or newer, or Intel ifx), CMake 3.22 or newer, and make. Python 3 is only needed for the reference checks in `tools/`.

## Linux
```
cmake --preset gfortran_release_linux
cmake --build build/release
ctest --test-dir build/release --output-on-failure
build/release/memdif3d --version
```
Debug build (array bounds checks, floating-point traps): use `gfortran_debug_linux`.

Without presets:
```
cmake -B build -D CMAKE_Fortran_COMPILER=gfortran -D CMAKE_BUILD_TYPE=Release
cmake --build build
```

## Intel ifx (Linux)
```
source /opt/intel/oneapi/setvars.sh
cmake --preset ifx_release
cmake --build build/ifx_release
```
The Intel runtime is linked statically.

## Python tools
`conda env create -f environment.yml && conda activate memdif3d` installs numpy, matplotlib and Pillow for `tools/animate_field.py`. The input converter and the prototype solver need only the Python standard library.

## Stability
The scheme is explicit. At start the program prints the largest coefficient sum and stops if it is above 1 (diffusion too large, retardation too small, velocity or step too big). `--force` runs anyway.

## Tests
`ctest` runs the version checks, the input-file check, a full regression (field and probe output against a Python prototype, restart and `--fresh`), tests on other geometries (off-centre source, sorption, advection, a sealed box with an analytic end state, the stability guard) and a smoke test of the animation script (skipped without matplotlib). It needs Python 3.

## Windows (MSYS2 UCRT64 shell)
```
pacman -S mingw-w64-ucrt-x86_64-gcc-fortran mingw-w64-ucrt-x86_64-cmake make
cmake --preset gfortran_release_windows
cmake --build build/release
```

## Banner text
The start-up banner shows version, git tag, compiler, build type, OS, build time and the lab / contact lines. Set the developer lines when configuring (or change the defaults near the top of `CMakeLists.txt`); empty values are left out:
```
cmake --preset gfortran_release_linux -D MEMDIF3D_DEPARTMENT="Department of ..." -D MEMDIF3D_CONTACT="name@ttu.edu"
```
Other variables: `MEMDIF3D_AUTHOR`, `MEMDIF3D_INSTITUTION`. The build time is the time CMake was configured.

## Options
- `-D MEMDIF3D_OPENMP=ON` builds with OpenMP.

## Releases
Push a tag to build Linux (gfortran, ifx) and Windows executables and attach them to a GitHub release:
```
git tag v0.1.0 && git push origin v0.1.0
```
