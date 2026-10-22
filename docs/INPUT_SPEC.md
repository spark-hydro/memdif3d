# memdif3d input files

memdif3d reads plain-text packages in the style of MODFLOW 6. The spreadsheet is never read by the program: `tools/xlsx2memdif.py` extracts a package set from it once. The model equations are in [MODEL_SPEC.md](MODEL_SPEC.md).

## Conventions
- Run: `memdif3d <namefile>`. All package paths in the name file are relative to the name file.
- `#` starts a comment. Blank lines are ignored. Keywords are case-insensitive.
- Blocks: `BEGIN name` ... `END name`.
- **Indices are 1-based**: `IX` = 1..NX (rows, X), `IY` = 1..NY (slices, Y), `IZ` = 1..NZ (columns, Z). Compared with MODEL_SPEC.md: `IX = X`, `IY = Y + 1`, `IZ = Z + 1`. `IZ = 1` is the cell that touches the membrane.
- **Arrays** (`IDOMAIN`, `STRT`, `ADVMASK`): the array name, then `INTERNAL`, then NX*NY*NZ numbers in free format, `IZ` fastest, then `IX`, then `IY`. The generator writes one line per `IX` and a comment per `IY`, so every slice looks like a tile of the spreadsheet.
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
`BEGIN dimensions` with `NX`, `NY`, `NZ`; `BEGIN griddata` with `IDOMAIN`:
`1` fluid cell (updated by the diffusion rule), `0` solid (never used), `2` ghost cell (set by BND).

## IC
`BEGIN griddata` with `STRT`: concentration of every cell at the start (ghost cells included, because fluid cells read them in the first step).

## DSP (sand and membrane diffusion)
Blocks `sand` and `membrane`, each with `DIFFUSION`, `TORTUOSITY`, `POROSITY`, `LENGTH`. The program computes `K = DIFFUSION * POROSITY / LENGTH / TORTUOSITY`.

## MST (retardation)
`BEGIN options` with `POROSITY`, `BULK_DENSITY`, `KD`: `R = POROSITY + BULK_DENSITY * KD`. The coefficients used in the update are `ks = K_sand / R` and `km = K_membrane / R`. (The source-cell update uses `K_membrane` without `R`, see MODEL_SPEC.md section 4.)

## SRC (the fully mixed source cell)
`BEGIN source` with `VOLUME` and `START_CONC`. `BEGIN faces`: one `IX IY` pair per membrane face; each face touches the cell at `IZ = 1` of that column.

## ADV (advection along X)
`BEGIN options` with `VELOCITY` (per time step). `BEGIN griddata` with `ADVMASK` (1 = add `VELOCITY * (C(IX+1) - C)` to this cell).

## BND (ghost cells and exceptions)
```
BEGIN ghosts          # evaluated in file order, after the fluid cells and the source
  ix iy iz FIXED value
  ix iy iz COPY sx sy sz factor      # value = factor * new value of cell (sx sy sz)
END ghosts
BEGIN neighbor_overrides
  ix iy iz DIR OMIT                  # fluid cell has no neighbour in direction DIR
  ix iy iz DIR SOURCE                # neighbour is the source cell (coefficient km)
  ix iy iz DIR SET tx ty tz          # neighbour is cell (tx ty tz) instead of the default
END neighbor_overrides
```
`DIR` is one of `+X -X +Y -Y +Z -Z`. **Default neighbours** of a fluid cell: the six face neighbours that are not solid; the `-Z` neighbour of an `IZ = 1` cell under a source face is the source. `FIXED` lines come first in the file so that `COPY` lines can read them. The list `neighbor_overrides` is how the two spreadsheet irregularities (MODEL_SPEC.md section 6) are carried: delete those lines to follow the intended pattern instead.

## OC (output control)
`BEGIN options` with `DAILY_FIELD FILEOUT name`, `PROBES FILEOUT name`, `RESTART FILEOUT name`; `BEGIN probes` lists `SOURCE` or `ix iy iz` cells written every time step. `{period}` in a file name is replaced by the period number. (Output is not implemented yet.)

## Generating and checking a set
```
python3 tools/xlsx2memdif.py Reduced_Matrix.xlsx data/reduced_matrix
python3 tools/memdif_proto.py data/reduced_matrix/memdif3d.nam
```
`xlsx2memdif.py` derives the grid, domain codes, ghost rules, overrides, parameters and initial state from the sheet formulas and stops with a message if the sheet has a pattern it does not understand. `memdif_proto.py` reads only the text files, runs one step on a random field and compares with `tools/ref_step.py` (which was checked against the sheet formulas); it prints a difference of 0 for the Reduced_Matrix set.
