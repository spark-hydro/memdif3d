# Validation against the spreadsheet

The repository holds one input set, `data/reduced_matrix` (files `rm.*`). It is made from the spreadsheet model `Reduced_Matrix_fixed.xlsx`:

```
python3 tools/xlsx2memdif.py Reduced_Matrix_fixed.xlsx data/reduced_matrix --name rm
```

The converter reads the grid, the domain codes, the boundary rules, the parameters and the initial state from the formulas of the sheet and stops with a message if it finds a pattern it does not understand. For this workbook it finds the five boundary rules and no exceptions and no neighbour overrides. The spreadsheet files are not in the repository.

## 1. One step, formulas
LibreOffice recalculates the workbook's own formulas on a random concentration field, and every cell is compared with the prototype step of `data/reduced_matrix` (`tools/memdif_proto.py`, which reads the same text files as the Fortran program):

| comparison | max abs difference |
|---|---|
| sand cells | 7.8e-16 |
| boundary cells | 6.7e-16 |
| source cell | 3.3e-16 |

No cell differs by more than 1e-12. The prototype step is the reference rule of `tools/ref_step.py`, which was checked against the 28,559 formulas of the sheet (`tools/test_vs_excel.py`).

## 2. VBA macro output (Excel, 2026-10-28/29)
`excel/DailyRun_fixed.bas` was run in Excel on Windows, in a macro-enabled copy of the workbook, from the initial state. The Day files are compared with memdif3d on `data/reduced_matrix` (`compare_excel_block.py Day_...xlsx field_001.csv --first-row 6 --fixed-layout`):

| run | all cells | boundary cells | source |
|---|---|---|---|
| 10 steps | 5.6e-17 | 0 | equal to 15 digits |
| 1440 steps (one day) | 2.8e-16 | 4.2e-17 | 0.886681363528 in both |

For the one-day run the `Minutes` sheet (probe cell / 5625) agrees with the Fortran probe file in all 1440 minutes to 1.1e-16. The Day files are not in the repository.

The minutes output (`MINUTES` block, `DIGITS 16`, `FROM` = `TO` = the step) gives the same two comparisons: 10 steps 5.6e-17 (boundary cells 0) and 1440 steps 2.8e-16 (boundary cells 4.2e-17), the same numbers as the field file. A test (`minutes_output`) also checks that the minutes file equals the snapshot files exactly at 16 digits.

## 3. Independent physics checks (tests/test_cases.py)
Sealed box: mass conserved to 5e-15 and the end state equals the analytic uniform concentration V*CM0 / (V + R*Nfluid). Off-centre source with sorption, advection and neighbour overrides: Fortran equals the Python prototype to 1e-16. The input set is checked against the prototype, the restart and `--fresh` by the ctests `input_files_reproduce_reference` and `run_reduced_matrix`.

## Not covered
Sorption (Kd > 0), advection and the holes are tested against the prototype and the sealed box only, not against a spreadsheet run.
