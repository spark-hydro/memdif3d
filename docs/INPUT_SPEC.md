# memdif3d input files

memdif3d reads plain-text packages in the style of MODFLOW 6. The spreadsheet is never read by the program: `tools/xlsx2memdif.py` extracts a package set from it once. The model equations are in [MODEL_SPEC.md](MODEL_SPEC.md).

## Conventions
- Run: `memdif3d <namefile>`. All package paths in the name file are relative to the name file.
- `#` starts a comment. Blank lines are ignored. Keywords are case-insensitive.
- Blocks: `BEGIN name` ... `END name`.
- **MODFLOW names, indices are 1-based**: `ILAY` = 1..NLAY (layers), `IROW` = 1..NROW (rows), `ICOL` = 1..NCOL (columns). Compared with MODEL_SPEC.md: `ILAY = Y + 1` (the slices), `IROW = X` (the rows), `ICOL = Z + 1` (away from the source). `ICOL = 1` is the cell that touches the membrane. A layer is the plan view from the top: rows down, columns across (one tile of the spreadsheet). A cell id on a line is written in MODFLOW 6 order, `ilay irow icol`; a face is `ilay irow` (the cell at `ICOL = 1` under it).
- **Arrays** (`IDOMAIN`, `STRT`, `ADVMASK`): the array name, then `INTERNAL`, then NLAY*NROW*NCOL numbers in free format, `ICOL` fastest, then `IROW`, then `ILAY` (the MODFLOW order). The generator writes one line per `IROW` and a comment per `ILAY`, so every layer is a tile with the rows down and `ICOL` across.
- Units: length mm, time minutes. Coefficients are per time step.

## Name file `*.nam`
```
BEGIN options
  TITLE text
END options
BEGIN packages
  TDIS  file     DIS  file     IC  file     DSP  file     MST  file
  SRC   file     ADV  file     BND file     OC   file      (one per line)
END packages
```

## TDIS
```
BEGIN options   TIME_UNITS minutes   END options
BEGIN timing    STEP_LENGTH 1.0   STEPS_PER_PERIOD 1440   NPERIODS 28   END timing
```
A period is one day. The restart and daily outputs are written at the end of each period.

## DIS
`BEGIN dimensions` with `NLAY`, `NROW`, `NCOL`; `BEGIN griddata` with `IDOMAIN`:
`1` fluid cell (updated by the diffusion rule), `0` solid (never used), `2` boundary cell (set by BND).

## IC
`BEGIN griddata` with `STRT`: concentration of every cell at the start (boundary cells included, because fluid cells read them in the first step).

## DSP (sand and membrane diffusion)
Blocks `sand` and `membrane`, each with `DIFFUSION`, `TORTUOSITY`, `POROSITY`, `LENGTH`. The program computes `K = DIFFUSION * POROSITY / LENGTH / TORTUOSITY`.

## MST (retardation)
`BEGIN options` with `POROSITY`, `BULK_DENSITY`, `KD`: `R = POROSITY + BULK_DENSITY * KD`. The coefficients used in the update are `ks = K_sand / R` and `km = K_membrane / R`. (The source-cell update uses `K_membrane` without `R`, see MODEL_SPEC.md section 4.)

## SRC (the fully mixed source cell)
`BEGIN source` with `VOLUME` and `START_CONC`. `BEGIN faces` holds the array `FACES`, a map of the plane `ICOL = 1`: NLAY lines of NROW values (one line per `ILAY`, `IROW` across, so the membrane pattern can be read and edited directly). Each value is what the source meets at that cell:

| value | meaning |
|---|---|
| 0 | no face (solid plate; the cell has no source neighbour) |
| 1 | membrane: transfer with the membrane coefficient `K_membrane` |
| 2 | hole: no membrane; the source touches the sand directly, with the sand coefficient `K_sand` (the source-cell update uses `K_sand` for it, without `R`, like `K_membrane` for the membrane) |
| 3 | closed: impermeable (no transfer, like a wall) |

A face (1, 2 or 3) needs `IDOMAIN = 1` in the cell at `ICOL = 1` under it. `tools/make_holes.py` writes a copy of a set with a regular pattern of holes, e.g. `--pitch 3 --size 1` gives `-0--0--0-` along every third row. The old format (a line `ilay irow [TYPE]` per face) is not read any more; `tools/convert_input.py` converts it.

## ADV (advection along X)
`BEGIN options` with `VELOCITY` (per time step). `BEGIN griddata` with `ADVMASK` (1 = add `VELOCITY * (C(IROW+1) - C)` to this cell).

## BND (boundary cells and exceptions)
**Boundary cells** are the cells with `IDOMAIN = 2`, the outer cells of the box. Their values are set after the fluid cells and the source cell, each step, from the cells inside.
```
BEGIN boundary                 # side rules, evaluated in this order
  IROW=1     COPY 0.82
  IROW=NROW  COPY 0.82
  ICOL=NCOL  COPY 0.82
  ILAY=1     COPY 0.82
  ILAY=NLAY  COPY 0.82
END boundary
BEGIN boundary_cells           # optional exceptions, per cell, applied after the rules, in file order
  ilay irow icol FIXED value
  ilay irow icol COPY slay srow scol factor      # value = factor * new value of cell (slay srow scol)
END boundary_cells
BEGIN neighbor_overrides       # optional
  ilay irow icol DIR OMIT                  # fluid cell has no neighbour in direction DIR
  ilay irow icol DIR SOURCE                # neighbour is the source cell (coefficient km)
  ilay irow icol DIR SET tlay trow tcol    # neighbour is cell (tlay trow tcol) instead of the default
END neighbor_overrides
```
**Rules.** A line names a side of the box, `IROW=`, `ICOL=` or `ILAY=` followed by `1`, the last index (`NROW`, `NCOL`, `NLAY` or the number) and one rule:
- `COPY factor`: every boundary cell on that side gets `factor` times the new value of the cell one step inward (normal to the side).
- `FIXED value`: the cell gets the constant.
- `NOFLOW`: the same as `COPY 1.0` (no gradient, no flux through the side).

A cell on two sides (an edge or a corner) takes the rule of the later line, and the cell it reads may itself be a boundary cell set by an earlier line. In the order above this is the spreadsheet's rule (rows first, then the far end, then the layers). A side without a line leaves its boundary cells at their start value (`STRT`); solid cells are never touched; a side index other than 1 or the last index is refused. The five-rule block is the whole boundary of the intended Reduced_Matrix set.

**Exceptions.** `boundary_cells` lines are applied after all rules, so a rule cell that reads an exception cell sees the old value. They carried the boundary mistakes of the original spreadsheet (the 82 typed zeros and the corner cells next to them, MODEL_SPEC.md section 6), and `neighbor_overrides` carried its 861 shifted neighbours. The example set `data/reduced_matrix` needs neither list; they remain useful for any real exception.

`DIR` is one of `+ROW -ROW +LAY -LAY +COL -COL`. **Default neighbours** of a fluid cell: the six face neighbours that are not solid; the `-COL` neighbour of an `ICOL = 1` cell under a source face is the source. The old `BEGIN boundarys` list is not read any more; `tools/convert_input.py` converts it to rules plus exceptions.

## OC (output control)
```
BEGIN options
  DAILY_FIELD  FILEOUT field_{period}.csv
  PROBES       FILEOUT probes_{period}.csv
  RESTART      FILEOUT restart.dat
  SNAPSHOT     FILEOUT snap_{step}.csv  EVERY 60
END options
BEGIN probes        # SOURCE, or "ilay irow icol"; written every time step
  SOURCE
  15 22 1
END probes
```
All three outputs are optional. File names are relative to the directory the program is started from. `{period}` in a name is replaced by the period (day) number, zero padded to 3 digits.
- **DAILY_FIELD:** the whole concentration field at the end of each period, as comma-separated text: a `# ILAY n` line per layer, then one line per `IROW` with the `ICOL` values. Boundary and solid cells are included.
- **SNAPSHOT:** optional. The same field file as DAILY_FIELD, written every `EVERY` time steps inside the run, with `{step}` in the name replaced by the step number (7 digits, so the files sort in time order). Use it for animations with finer frames: `EVERY 60` is one frame per hour for a 1-minute step. Command line: `--snapshot-every N` (default name `snap_{step}.csv`). Disk use is about 0.75 MB per frame for the Reduced_Matrix grid.
- **PROBES:** one row per time step with columns `step,time,<probe...>` (time in minutes; a cell column is named `ilay_irow_icol`). With `{period}` in the name a new file starts every period; without it, one file is kept and appended to after a restart.
- **RESTART:** at the end of every period the full state is written, as text so it can move between computers, alternating between `<name>.1` and `<name>.2` so that a crash during writing never destroys the previous one. On start the newest valid file is used and the run continues with the next period (the log says `restart: continuing after period N`); `--fresh` deletes both files and starts from the initial state. A run whose periods are all finished does nothing.

## Command line
```
memdif3d <namefile> [--fresh] [--force] [--nperiods N] [--steps-per-period N] [--snapshot-every N]
```
`--nperiods` and `--steps-per-period` override TDIS (handy for short tests); `--force` runs despite a failed stability check. Use a separate working directory for each run, because outputs go to the current directory.

## Generating and checking a set
```
python3 tools/xlsx2memdif.py Reduced_Matrix.xlsx data/reduced_matrix
python3 tools/memdif_proto.py data/reduced_matrix/rm.nam
```
`xlsx2memdif.py` derives the grid, domain codes, boundary rules, overrides, parameters and initial state from the sheet formulas and stops with a message if the sheet has a pattern it does not understand. `memdif_proto.py` reads only the text files, runs one step on a random field and compares with `tools/ref_step.py` (which was checked against the sheet formulas); it prints a difference of 0 for the Reduced_Matrix set.
