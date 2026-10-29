Example input sets go here.

`reduced_matrix/` is the Reduced_Matrix case (files `rm.nam`, `rm.dis`, `rm.ic`, `rm.dsp`, `rm.mst`, `rm.src`, `rm.adv`, `rm.bnd`, `rm.oc`, `rm.tdis`), generated from the corrected spreadsheet:

    python tools/xlsx2memdif.py Reduced_Matrix_fixed.xlsx data/reduced_matrix --name rm

The model of the original spreadsheet, which has two mistakes, is made with `python tools/xlsx2memdif.py Reduced_Matrix.xlsx data/original --name rm`. The formats are described in `docs/INPUT_SPEC.md`.
