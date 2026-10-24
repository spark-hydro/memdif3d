# memdif3d input files

memdif3d reads plain-text packages in the style of MODFLOW 6. The spreadsheet is never read by the program: `tools/xlsx2memdif.py` extracts a package set from it once. The model equations are in [MODEL_SPEC.md](MODEL_SPEC.md).

## Conventions
- Run: `memdif3d <namefile>`. All package paths in the name file are relative to the name file.
- `#` starts a comment. Blank lines are ignored. Keywords are case-insensitive.
- Blocks: `BEGIN name` ... `END name`.
- **MODFLOW layout, indices are 1-based**: `ILAY` = 1..NLAY (layers, away from the source), `IROW` = 1..NROW (rows), `ICOL` = 1..NCOL (columns). `ILAY = 1` is the layer that touches the membrane. Compared with MODEL_SPEC.md: `IROW = X`, `ICOL = Y + 1`, `ILAY = Z + 1`. A cell id on a line is written in MODFLOW 6 order, `ilay irow icol`; a face is `irow icol`.
- **Arrays** (`IDOMAIN`, `STRT`, `ADVMASK`): the array name, then `INTERNAL`, then NLAY*NROW*NCOL numbers in free format, `ICOL` fastest, then `IROW`, then `ILAY` (the MODFLOW order). The generator writes one line per `IROW` and a comment per `ILAY`, so every layer is a plan view (rows down, columns across).
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
`1` fluid cell (updated by the diffusion rule), `0` solid (never used), `2` ghost cell (set by BND).

## IC
`BEGIN griddata` with `STRT`: concentration of every cell at the start (ghost cells included, because fluid cells read them in the first step).

## DSP (sand and membrane diffusion)
Blocks `sand` and `membrane`, each with `DIFFUSION`, `TORTUOSITY`, `POROSITY`, `LENGTH`. The program computes `K = DIFFUSION * POROSITY / LENGTH / TORTUOSITY`.

## MST (retardation)
`BEGIN options` with `POROSITY`, `BULK_DENSITY`, `KD`: `R = POROSITY + BULK_DENSITY * KD`. The coefficients used in the update are `ks = K_sand / R` and `km = K_membrane / R`. (The source-cell update uses `K_membrane` without `R`, see MODEL_SPEC.md section 4.)

## SRC (the fully mixed source cell)
`BEGIN source` with `VOLUME` and `START_CONC`. `BEGIN faces`: one `IROW ICOL [TYPE]` line per face of the source; each face touches the cell at `ILAY = 1` under it. `TYPE` is optional:
- `MEMBRANE` (default): transfer through the membrane, coefficient `K_membrane`.
- `HOLE`: no membrane at this face. The source touches the sand directly, with the sand coefficient `K_sand` (the source-cell update uses `K_sand` for it, without `R`, like `K_membrane` for the membrane).
- `CLOSED`: impermeable face (no transfer, like a wall).
`tools/make_holes.py` writes a copy of a set with a regular pattern of holes, e.g. `--pitch 3 --size 1` gives `-0--0--0-` along every third row.

## ADV (advection along X)
`BEGIN options` with `VELOCITY` (per time step). `BEGIN griddata` with `ADVMASK` (1 = add `VELOCITY * (C(IROW+1) - C)` to this cell).

## BND (ghost cells and exceptions)
```
BEGIN ghosts          # evaluated in file order, after the fluid cells and the source
  ilay irow icol FIXED value
  ilay irow icol COPY slay srow scol factor      # value = factor * new value of cell (slay srow scol)
END ghosts
BEGIN neighbor_overrides
  ilay irow icol DIR OMIT                  # fluid cell has no neighbour in direction DIR
  ilay irow icol DIR SOURCE                # neighbour is the source cell (coefficient km)
  ilay irow icol DIR SET tlay trow tcol    # neighbour is cell (tlay trow tcol) instead of the default
END neighbor_overrides
```
`DIR` is one of `+ROW -ROW +COL -COL +LAY -LAY`. **Default neighbours** of a fluid cell: the six face neighbours that are not solid; the `-LAY` neighbour of an `ILAY = 1` cell under a source face is the source. `FIXED` lines come first in the file so that `COPY` lines can read them. The list `neighbor_overrides` is how the two spreadsheet irregularities (MODEL_SPEC.md section 6) are carried: delete those lines to follow the intended pattern instead.

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
  1 22 15
END probes
```
All three outputs are optional. File names are relative to the directory the program is started from. `{period}` in a name is replaced by the period (day) number, zero padded to 3 digits.
- **DAILY_FIELD:** the whole concentration field at the end of each period, as comma-separated text: a `# ILAY n` line per layer, then one line per `IROW` with the `ICOL` values. Ghost and solid cells are included.
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
python3 tools/memdif_proto.py data/reduced_matrix/memdif3d.nam
```
`xlsx2memdif.py` derives the grid, domain codes, ghost rules, overrides, parameters and initial state from the sheet formulas and stops with a message if the sheet has a pattern it does not understand. `memdif_proto.py` reads only the text files, runs one step on a random field and compares with `tools/ref_step.py` (which was checked against the sheet formulas); it prints a difference of 0 for the Reduced_Matrix set.
