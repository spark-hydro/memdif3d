# Building memdif3d

The build instructions (Linux with gfortran or Intel ifx, Windows with MSYS2, the Python environment, the tests, the stability check) are in the manual: [docs/install.md](docs/install.md), online at https://memdif3d.readthedocs.io/en/latest/install/.

Quick start on Linux (gfortran 13 or newer, CMake 3.22 or newer, make):

```
cmake --preset gfortran_release_linux
cmake --build build/release
ctest --test-dir build/release --output-on-failure
build/release/memdif3d --version
```

A release is made by pushing a tag `v*`: `git tag -a v0.1.2 -m "..." && git push origin v0.1.2` starts the release workflow (binaries, GitHub release, Docker images).
