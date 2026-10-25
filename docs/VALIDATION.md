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

## 3. VBA macro output (Day_001.xlsx, 2026-10-24)
`excel/DailyRun.bas` was run in Excel for 10 steps (`STEPS_PER_DAY = 10`, `TOTAL_DAYS = 1`). The workbook it started from held the state of memdif3d step 1020 (the macro's source value at minute 1, 0.9111050245470296, equals memdif3d step 1021 exactly), so the Day file is compared with memdif3d after 1030 steps from the initial state:

| comparison | max abs difference |
|---|---|
| all 31,175 cells of Day_001.xlsx | 3.3e-16 |
| ghost cells | 2.8e-17 |
| source value, each of the 10 minutes of the Minutes sheet | 1.1e-16 |

Reproduce with `memdif3d data/reduced_matrix/memdif3d.nam --nperiods 1 --steps-per-period 1030 --fresh` and `python3 tools/compare_excel_block.py Day_001.xlsx field_001.csv --first-row 6 --nam data/reduced_matrix/memdif3d.nam`. The state block of `Reduced_Matrix.xlsm` (kept next to the other Excel files, last saved 2026-10-22) is itself a macro result: it equals memdif3d after **32,820 steps** (22.8 days) from the initial state, max abs difference 6.9e-17 over all cells (ghosts 8.7e-18, source 0.139704403392094 in both). The macro overwrites that block in place on every run, so a clean run must start from `Reduced_Matrix.xlsx`, not from this file. Reproduce with `--steps-per-period 32820` and `compare_excel_block.py Reduced_Matrix.xlsm field_001.csv --first-row 6 ...`.

## 3b. The two spreadsheet irregularities
`data/reduced_matrix_intended` removes them (docs/DEVELOPMENT.md). Against the sheet-exact set: after 576 steps the source is 0.939863 against 0.939861 and the largest cell difference is 9e-3 (peak 0.75), in slice 27 near the membrane; after 28 days the source is 0.0914 against 0.0899 and the largest difference is 3e-3 (peak 0.076), at the far boundary cells that were fixed at 0. The intended set is checked against the prototype and restart by the ctest `run_reduced_matrix_intended`; it cannot be checked against Excel because the sheet contains the irregularities.

## 4. Independent physics checks (tests/test_cases.py)
Sealed box: mass conserved to 5e-15 and the end state equals the analytic uniform concentration V*CM0 / (V + R*Nfluid). Off-centre source with sorption, advection and neighbour overrides: Fortran equals the Python prototype to 1e-16.

## Not covered
A full 1440-step VBA day from the initial state has not been compared (only the 10 steps in section 3); sorption (Kd > 0) and advection are tested against the prototype only, not against a spreadsheet run.
