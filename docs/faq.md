# Limits and FAQ

## Limits of the current version
- **One source cell** that touches `ICOL = 1`.
- **One uniform sand and one membrane**: the same properties everywhere.
- **Cubic cells**: every cell is 1 mm on a side. The membrane is a resistance on one plane, not a layer of cells, so there is no concentration inside it.
- **Flow** only toward lower `IROW`, as a first-order upwind term.
- **Explicit time stepping**: the step is limited by the stability rule (the program checks it and stops).
- **Text output**: fields and restart files are plain text; a binary format is a possible later addition.

## Frequently asked questions

**Why do concentrations fall after about two days?**
The source is a finite batch and the outer boundary cells hold 0.82 times their neighbour, so they drain solute. That is how the spreadsheet works. Use `NOFLOW` for a sealed side.

**What is a boundary cell?**
A cell of the outer layer of the box (`IDOMAIN = 2`). It is not part of the medium. Its value is set after each step from the cell next to it, following the rule of its side.

**What does the stability message mean?**
The program computes the largest coefficient sum over all cells and stops above 1. See [Theory](theory.md#stability). Reduce the step length or the diffusion coefficient, or raise the retardation.

**Can I use my own concentrations at the start?**
Yes. Fill `STRT` in the `.ic` file (every cell, boundary cells included) and `START_CONC` in the `.src` file.

**How do I continue a run?**
Run the same command in the same folder. The program reads the newest restart file and continues with the next period.

**Is the input file format the same as MODFLOW 6?**
It has the same style (blocks, `INTERNAL` arrays, a name file without unit numbers) but it is not compatible. Arrays use the MODFLOW order (column fastest, then row, then layer), and the packages `SRC`, `BND` and `ADV` are specific to this model.

**Why do two input sets exist for the Reduced_Matrix case?**
`data/reduced_matrix` reproduces the spreadsheet exactly, including two irregularities that look like editing mistakes in the sheet. `data/reduced_matrix_intended` is the same case without them. See [Validation](VALIDATION.md).
