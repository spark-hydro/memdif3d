# tools
Python (stdlib only) used to extract and validate the model spec. Run from a scratch folder, not the vault.
1. `expand_formulas.py`: expands shared formulas of `Reduced_Matrix.xlsx` and writes `cells.json` + `pats.json` in the current folder.
2. `ref_step.py`: pure-Python reference of one model step (spec in `../MODEL_SPEC.md`); run alone it compares step 1 with Excel's cached values.
3. `test_vs_excel.py`: evaluates Excel's actual formulas on a random field and compares with `ref_step.py` (expect max diff ~1e-16).
Paths are hard-coded to `/home/spark/Documents/Andrew/Reduced_Matrix.xlsx`; edit if it moves.

Axis names: the scripts use `z` = rows, `x` = column within a slice, `y` = slice. `../MODEL_SPEC.md` uses the voice-recording names: X = rows (script `z`), Z = column within a slice (script `x`), Y = slice.

4. `xlsx2memdif.py`: reads the spreadsheet and writes the memdif3d text input set (see `../docs/INPUT_SPEC.md`).
5. `memdif_proto.py`: reads only the text files and runs a step; compares with `ref_step.py` (used by ctest).
6. `make_test_case.py`: writes small synthetic input sets (`open`, `closed`) for tests/test_cases.py.
7. `animate_field.py`: animated GIFs of the field files (face and/or side view); needs numpy, matplotlib, Pillow.
8. `animate_3d.py`: interactive 3D animation as one HTML file (drag to rotate while it plays); needs numpy, plotly.
9. `make_holes.py`: copies an input set and punches holes in the membrane (`HOLE` / `CLOSED` faces in the SRC file).
10. `plot_domain.py`: to-scale picture of source, membrane, sand, plate and ghost cells from the input files (side, zoom, plan); needs numpy, matplotlib.
11. `animate_compare.py`: GIF with two runs side by side (face and side view) plus their difference, e.g. without and with holes; needs numpy, matplotlib, Pillow.
12. `plot_domain_3d.py`: interactive 3D picture of the domain (source, membrane, plate, sand, ghost cells, and the side/face cut planes); needs plotly.
13. `convert_layout.py`: renames an input set from NX NY NZ (`# IY` tiles, cell ids x y z) to the MODFLOW names (NLAY NROW NCOL, `# ILAY` tiles, cell ids `ilay irow icol`).
14. `make_intended_set.py`: copies the Reduced_Matrix set and removes the two spreadsheet irregularities (861 overrides, 82 fixed boundary cells).
