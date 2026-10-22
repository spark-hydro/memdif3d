# Validation against the spreadsheet

## 1. One step, formulas (Reduced_Matrix.xlsx)
Excel's own 28,559 formulas, evaluated on a random concentration field, give the same new field as the memdif3d rule: max abs difference 2e-16 over all cells and the source cell (`tools/test_vs_excel.py`, `tools/ref_step.py`). From the initial state, the first step also equals the values cached in the sheet (source cell 0.9996666667, 225 nonzero cells).

## 2. Long run (3d_nonzeroboundry.xlsx, 2026-10-22)
The large workbook (460 MB, 50,736 rows, same parameters as Reduced_Matrix) was read as a stream. About half of its time blocks are empty, so its last block (rows 50694:50736) is not step 1152. memdif3d run for **576 steps** (1 min each) from the same initial state reproduces that last block:

| comparison | max abs difference |
|---|---|
| all 31,175 cells | 2.2e-16 |
| ghost cells (4,481) | 1.4e-17 |
| source cell | 0.939861192439379 in both |

The step count was found by scanning (575 and 577 steps differ by 2e-4), which also shows how sharply the comparison discriminates. Reproduce with

```
memdif3d data/reduced_matrix/memdif3d.nam --nperiods 1 --steps-per-period 576 --fresh
python3 tools/compare_excel_block.py 3d_nonzeroboundry.xlsx field_001.csv --first-row 50694 --nam data/reduced_matrix/memdif3d.nam
```

## 3. Independent physics checks (tests/test_cases.py)
Sealed box: mass conserved to 5e-15 and the end state equals the analytic uniform concentration V*CM0 / (V + R*Nfluid). Off-centre source with sorption, advection and neighbour overrides: Fortran equals the Python prototype to 1e-16.

## Not covered
The VBA macro output (`Day_NNN.xlsx`) has not been compared yet; sorption (Kd > 0) and advection are tested against the prototype only, not against a spreadsheet run.
