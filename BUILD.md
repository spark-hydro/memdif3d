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

## Tests
`ctest` runs the version checks, the input-file check and a full regression (field and probe output against a Python prototype, restart and `--fresh`). It needs Python 3.

## Windows (MSYS2 UCRT64 shell)
```
pacman -S mingw-w64-ucrt-x86_64-gcc-fortran mingw-w64-ucrt-x86_64-cmake make
cmake --preset gfortran_release_windows
cmake --build build/release
```

## Options
- `-D MEMDIF3D_OPENMP=ON` builds with OpenMP.

## Releases
Push a tag to build Linux (gfortran, ifx) and Windows executables and attach them to a GitHub release:
```
git tag v0.1.0 && git push origin v0.1.0
```
