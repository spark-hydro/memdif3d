# tools

Python scripts for the input files, pictures, animations and checks. The list with what each script does and how to run it is in the manual: [docs/tools.md](../docs/tools.md) (online: https://memdif3d.readthedocs.io/en/latest/tools/).

Two notes that are not in the manual:

- `expand_formulas.py`, `ref_step.py` and `test_vs_excel.py` check the model specification against the formulas of the spreadsheet. Run them from a scratch folder, not the repository: `python3 expand_formulas.py Reduced_Matrix.xlsx` writes `cells.json` and `pats.json` into the current folder, then `PYTHONPATH=<repo>/tools python3 <repo>/tools/test_vs_excel.py` compares Excel's formulas on a random field with `ref_step.py` (expect a maximum difference of about 1e-16).
- Axis names: these three scripts use the older names, `z` = rows, `x` = column within a slice, `y` = slice. `docs/MODEL_SPEC.md` gives the lab's names (X = rows, Z = away from the source, Y = slice) and the MODFLOW names (IROW, ICOL, ILAY). The other scripts work with the MODFLOW names.
