# Development notes (read this when resuming on another computer)

## Set up
```
git clone <repo url> && cd memdif3d
conda env create -f environment.yml && conda activate memdif3d     # Python tools only
cmake --preset gfortran_release_linux && cmake --build build/release
ctest --test-dir build/release --output-on-failure                 # 6 tests, animate_smoke skips without matplotlib
```
Tools needed: gfortran 13+ (or Intel ifx), CMake 3.22+, make, Python 3. See BUILD.md.

## What this is
memdif3d simulates diffusion from a fully mixed source cell through a membrane into a porous medium (explicit finite volume, 1 mm cells, 1 minute steps). It replaces a spreadsheet model (Reduced_Matrix.xlsx / 3d_nonzeroboundry.xlsx) that was run in pieces by hand. The program reads MODFLOW 6 style text packages (docs/INPUT_SPEC.md) and never reads Excel; `tools/xlsx2memdif.py` converts the spreadsheet once.

## Conventions
- MODFLOW names: NLAY x NROW x NCOL = 29 x 43 x 25, arrays ICOL fastest then IROW then ILAY, cell ids `ilay irow icol` (docs/INPUT_SPEC.md). Mapping to the lab's axes in docs/MODEL_SPEC.md: ILAY = Y + 1 (slices), IROW = X, ICOL = Z + 1 (away from the source; ICOL = 1 touches the membrane). The array order is the old one, only the names changed. The Python tools keep tuples (x, y, z) = (row, lay, col). Old sets (NX NY NZ, `# IY` tiles) convert with `tools/convert_layout.py`; old restart files are refused.
- Run each simulation in its own folder: outputs go to the current directory.
- The two irregularities of the spreadsheet (slice Y = 27 off-by-one, constant-0 edge cells in slices 20 and 26) are kept on purpose in `data/reduced_matrix` (861 `neighbor_overrides`, 82 `FIXED` boundary cells in its `.bnd`), because that set reproduces Excel to 2e-16. `data/reduced_matrix_intended` is the same case without them (`tools/make_intended_set.py`); after 28 days the source concentration is 0.0914 instead of 0.0899. Use the intended set for new work unless you compare with the spreadsheet.

## Validation status
- Spreadsheet formulas == memdif3d rule on random fields (2e-16).
- 576 steps equal the last block of 3d_nonzeroboundry.xlsx to 2.2e-16 over all cells (docs/VALIDATION.md).
- Sealed box: mass conserved to 5e-15, analytic end state reached. Off-centre source with sorption and advection: equals the Python prototype.
- VBA macro (excel/DailyRun.bas): 10 steps and the 32,820-step state saved in Reduced_Matrix.xlsm equal memdif3d to 3e-16 (docs/VALIDATION.md section 3). Not yet compared: a full 1440-step day, sorption and advection against a spreadsheet.

## Known limits (by design, so far)
One source cell touching ICOL = 1; one uniform sand and membrane; cubic cells; advection only toward lower IROW; explicit scheme (the program stops when the coefficient sum is above 1; `--force` overrides).

## Ideas / next steps
- Compare a full 1440-step VBA day with `field_001.csv` (tools/compare_excel_block.py works on any block of a sheet).
- A small step-by-step interface (initialise / advance / get / set) for coupling with other models or Python.
- Heterogeneous soil layers, other source geometries, binary output, OpenMP tuning.
- Confirm the GitHub Actions workflows (build.yml, release.yml) after the first push; the Windows job has never run.
