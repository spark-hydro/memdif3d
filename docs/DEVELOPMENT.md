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
- MODFLOW names: NLAY x NROW x NCOL = 29 x 43 x 25, arrays ICOL fastest then IROW then ILAY, cell ids `ilay irow icol` (docs/INPUT_SPEC.md). Mapping to the lab's axes in docs/MODEL_SPEC.md: ILAY = Y + 1 (slices), IROW = X, ICOL = Z + 1 (away from the source; ICOL = 1 touches the membrane). The array order is the old one, only the names changed. The Python tools keep tuples (x, y, z) = (row, lay, col). Sets in the older layout (NX NY NZ, `# IY` tiles) belong to the `excel-layout` branch; old restart files are refused.
- Run each simulation in its own folder: outputs go to the current directory.
- The input set is `data/reduced_matrix` (files `rm.*`), generated from the corrected workbook with `python tools/xlsx2memdif.py Reduced_Matrix_fixed.xlsx data/reduced_matrix --name rm`. The original workbook has two mistakes (slice Y = 27 reads its neighbour one position off, constant-0 edge cells in slices 20 and 26), confirmed by the author of the sheet; `tools/fix_reduced_matrix_xlsx.py` writes the corrected workbook (macro: `excel/DailyRun_fixed.bas`). The model of the original workbook (for comparing with the old Excel files) is made with `python tools/xlsx2memdif.py Reduced_Matrix.xlsx data/original --name rm`: it has 84 `boundary_cells` exceptions and 861 `neighbor_overrides` that carry the mistakes, and after 28 days its source is 0.0899 instead of 0.0914.

## Input formats
The membrane is a `FACES` map (0 none, 1 membrane, 2 hole, 3 closed) and the boundary is five side rules (`IROW=1 COPY 0.82` ...) plus optional exceptions, see docs/INPUT_SPEC.md. `tools/convert_input.py` converts the older list formats; the rules reproduce the spreadsheet set exactly (84 exceptions: the 82 typed zeros and 2 corner cells).

## Validation status
- Spreadsheet formulas == memdif3d rule on random fields (2e-16).
- 576 steps equal the last block of 3d_nonzeroboundry.xlsx to 2.2e-16 over all cells (docs/VALIDATION.md).
- Sealed box: mass conserved to 5e-15, analytic end state reached. Off-centre source with sorption and advection: equals the Python prototype.
- VBA macro (excel/DailyRun.bas): 10 steps and the 32,820-step state saved in Reduced_Matrix.xlsm equal memdif3d to 3e-16 when it is run on the model of the original workbook (docs/VALIDATION.md section 3). The corrected workbook with `excel/DailyRun_fixed.bas`: a full 1440-step day equals `data/reduced_matrix` to 3e-16 (section 3c). Not yet compared: sorption and advection against a spreadsheet.

## Known limits (by design, so far)
One source cell touching ICOL = 1; one uniform sand and membrane; cubic cells; advection only toward lower IROW; explicit scheme (the program stops when the coefficient sum is above 1; `--force` overrides).

## Ideas / next steps
- Compare a full 1440-step VBA day with `field_001.csv` (tools/compare_excel_block.py works on any block of a sheet).
- A small step-by-step interface (initialise / advance / get / set) for coupling with other models or Python.
- Heterogeneous soil layers, other source geometries, binary output, OpenMP tuning.
- Validate sorption (Kd > 0) and advection against a spreadsheet run; find a reference for the holes.
- Independent verification for a paper: an analytic benchmark, grid and time-step convergence, a comparison with another code.
- A box generator (`tools/make_box_model.py`): one command writes a complete input set for a box with a rectangular source footprint.
- A real membrane layer with its own cell size (needs non-uniform cells along `ICOL`).
- The Windows program is built by CI but has not been run on a Windows computer.
