# memdif3d: notes for Claude Code

Fortran program for diffusion from a fully mixed source cell through a membrane into a porous medium (explicit finite volume). Read `docs/DEVELOPMENT.md` first: status, conventions, validation, next steps. Model definition: `docs/MODEL_SPEC.md`; input files: `docs/INPUT_SPEC.md`; evidence of agreement with the spreadsheet: `docs/VALIDATION.md`.

## When the user says "resume"
1. Read `docs/DEVELOPMENT.md` and `docs/VALIDATION.md`; run `git log --oneline -10` and `git status`.
2. Build and test: `cmake --preset gfortran_release_linux && cmake --build build/release && ctest --test-dir build/release --output-on-failure` (6 tests; `animate_smoke` skips without matplotlib).
3. Tell the user where things stand and the open items, then ask what to do next.
The author's longer log may exist as `WORKING.md` in an Obsidian vault folder `00_projects/3d_nonzeroboundry`; ask for the vault path if it is not among the added folders. The Excel files, the voice recording and run outputs are not in the repo.

## Working rules
- Layout uses MODFLOW names: ILAY (the old slices, Y), IROW (rows, X), ICOL (away from the source, Z); 1-based, arrays ICOL fastest, cell ids `ilay irow icol`, ICOL = 1 touches the membrane.
- Keep `ref_step.py`, `memdif_proto.py` and the Fortran in step: tests compare them (tolerance 1e-12).
- Run simulations in their own folder (outputs go to the current directory); never commit `daily_output/`, GIFs or build folders.
- Do not push, tag or publish without the user's go-ahead. Authentication: SSH key per computer.
- Banner and contact lines come from CMake variables `MEMDIF3D_*` in `CMakeLists.txt`.
