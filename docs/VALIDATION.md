# Validation against the spreadsheet

The repository holds one input set, `data/reduced_matrix` (files `rm.*`), made from the **corrected** workbook `Reduced_Matrix_fixed.xlsx` (see section 3c). The comparisons in sections 1 to 3b were made with the original workbook, which has two mistakes (confirmed by the author of the sheet). To repeat them, make the model of the original workbook:

```
python3 tools/xlsx2memdif.py Reduced_Matrix.xlsx data/original --name rm
```

This set has the five boundary rules plus 84 `boundary_cells` exceptions and 861 `neighbor_overrides`, which carry the mistakes, so that it reproduces the original workbook exactly. The commands below call it `data/original/rm.nam`. The corrected workbook comes from `python3 tools/fix_reduced_matrix_xlsx.py Reduced_Matrix.xlsx Reduced_Matrix_fixed.xlsx`.

## 1. One step, formulas (Reduced_Matrix.xlsx)
Excel's own 28,559 formulas, evaluated on a random concentration field, give the same new field as the memdif3d rule: max abs difference 2e-16 over all cells and the source cell (`tools/test_vs_excel.py`, `tools/ref_step.py` with its original-workbook mistakes switched on). From the initial state, the first step also equals the values cached in the sheet (source cell 0.9996666667, 225 nonzero cells).

## 2. Long run (3d_nonzeroboundry.xlsx, 2026-10-22)
The large workbook (460 MB, 50,736 rows, same parameters as Reduced_Matrix) was read as a stream. About half of its time blocks are empty, so its last block (rows 50694:50736) is not step 1152. memdif3d run for **576 steps** (1 min each) from the same initial state reproduces that last block:

| comparison | max abs difference |
|---|---|
| all 31,175 cells | 2.2e-16 |
| boundary cells (4,481) | 1.4e-17 |
| source cell | 0.939861192439379 in both |

The step count was found by scanning (575 and 577 steps differ by 2e-4), which also shows how sharply the comparison discriminates. Reproduce with

```
memdif3d data/original/rm.nam --nperiods 1 --steps-per-period 576 --fresh
python3 tools/compare_excel_block.py 3d_nonzeroboundry.xlsx field_001.csv --first-row 50694 --nam data/original/rm.nam
```

## 3. VBA macro output (Day_001.xlsx, 2026-10-24)
`excel/DailyRun.bas` was run in Excel for 10 steps (`STEPS_PER_DAY = 10`, `TOTAL_DAYS = 1`). The workbook it started from held the state of memdif3d step 1020 (the macro's source value at minute 1, 0.9111050245470296, equals memdif3d step 1021 exactly), so the Day file is compared with memdif3d after 1030 steps from the initial state:

| comparison | max abs difference |
|---|---|
| all 31,175 cells of Day_001.xlsx | 3.3e-16 |
| boundary cells | 2.8e-17 |
| source value, each of the 10 minutes of the Minutes sheet | 1.1e-16 |

Reproduce with `memdif3d data/original/rm.nam --nperiods 1 --steps-per-period 1030 --fresh` and `python3 tools/compare_excel_block.py Day_001.xlsx field_001.csv --first-row 6 --nam data/original/rm.nam`. The state block of `Reduced_Matrix.xlsm` (kept next to the other Excel files, last saved 2026-10-22) is itself a macro result: it equals memdif3d after **32,820 steps** (22.8 days) from the initial state, max abs difference 6.9e-17 over all cells (boundary cells 8.7e-18, source 0.139704403392094 in both). The macro overwrites that block in place on every run, so a clean run must start from `Reduced_Matrix.xlsx`, not from this file. Reproduce with `--steps-per-period 32820` and `compare_excel_block.py Reduced_Matrix.xlsm field_001.csv --first-row 6 ...`.

## 3b. The effect of the two mistakes
Against the corrected set `data/reduced_matrix`, the model of the original workbook gives: after 576 steps a source of 0.939861 against 0.939863 and a largest cell difference of 9e-3 (peak 0.75), in slice 27 near the membrane; after 28 days a source of 0.0899 against 0.0914 and a largest difference of 3e-3 (peak 0.076), at the far boundary cells that were fixed at 0.

## 3c. The corrected workbook (2026-10-28)
The two irregularities were confirmed as mistakes. `tools/fix_reduced_matrix_xlsx.py` writes `Reduced_Matrix_fixed.xlsx`: the last tile moved one column to the right (so every tile is 27 columns after the previous one, and the existing formulas of tile Y = 27 point to the right cells), the 82 typed zeros replaced by `=<left neighbour>*0.82`, and the two corner cells AAS50, AAS92 given the normal formula. The original file is not changed. The checks:

| check | result |
|---|---|
| `xlsx2memdif.py` on the corrected workbook | 0 exceptions and 0 overrides; this is `data/reduced_matrix` |
| LibreOffice recalculates the workbook's own formulas on a random concentration field; every cell compared with the prototype step of `data/reduced_matrix` | max abs difference 7.8e-16 (sand cells), 6.7e-16 (boundary cells), 3.3e-16 (source); 0 cells above 1e-12 |
| control: the original workbook, same procedure | matches `data/original` to 7.8e-16, but not `data/reduced_matrix` (1,976 cells above 1e-12, up to 0.74 in the typed-zero cells and 0.048 in sand cells) |

**Run with the macro in Excel** (Windows, 2026-10-28/29): `excel/DailyRun_fixed.bas` in a macro-enabled copy of the corrected workbook, from the initial state, compared with memdif3d on `data/reduced_matrix` (`compare_excel_block.py Day_...xlsx field_001.csv --first-row 6 --fixed-layout`):

| run | all cells | boundary cells | source |
|---|---|---|---|
| 10 steps | 5.6e-17 | 0 | equal to 15 digits |
| 1440 steps (one day) | 2.8e-16 | 4.2e-17 | 0.886681363528 in both; the `Minutes` sheet (probe cell / 5625) agrees with the Fortran probe file in all 1440 minutes to 1.1e-16 |
| control: the same 1440-step file against `data/original` (the mistakes) | 1.6e-2 | 1.3e-2 | 0.886624 against 0.886681 |

After 10 steps the two models are still identical (the solute has not reached the repaired places); the fix shows from about 700 steps on, so the one-day run is the real test. The Day files are not in the repository.

## 4. Independent physics checks (tests/test_cases.py)
Sealed box: mass conserved to 5e-15 and the end state equals the analytic uniform concentration V*CM0 / (V + R*Nfluid). Off-centre source with sorption, advection and neighbour overrides: Fortran equals the Python prototype to 1e-16. The corrected set is checked against the prototype, the restart and `--fresh` by the ctests `input_files_reproduce_reference` and `run_reduced_matrix`.

## Not covered
Sorption (Kd > 0), advection and the holes are tested against the prototype and the sealed box only, not against a spreadsheet run.
