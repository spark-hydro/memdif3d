# tools
Python (stdlib only) used to extract and validate the model spec. Run from a scratch folder, not the vault.
1. `expand_formulas.py`: expands shared formulas of `Reduced_Matrix.xlsx` and writes `cells.json` + `pats.json` in the current folder.
2. `ref_step.py`: pure-Python reference of one model step (spec in `../MODEL_SPEC.md`); run alone it compares step 1 with Excel's cached values.
3. `test_vs_excel.py`: evaluates Excel's actual formulas on a random field and compares with `ref_step.py` (expect max diff ~1e-16).
Paths are hard-coded to `/home/spark/Documents/Andrew/Reduced_Matrix.xlsx`; edit if it moves.

Axis names: the scripts use `z` = rows, `x` = column within a slice, `y` = slice. `../MODEL_SPEC.md` uses the voice-recording names: X = rows (script `z`), Z = column within a slice (script `x`), Y = slice.

4. `xlsx2memdif.py`: reads the spreadsheet and writes the memdif3d text input set (see `../docs/INPUT_SPEC.md`).
5. `memdif_proto.py`: reads only the text files and runs a step; compares with `ref_step.py` (used by ctest).
