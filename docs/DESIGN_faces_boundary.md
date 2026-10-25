# Design: faces as an array, boundary as rules (implemented; the format is described in INPUT_SPEC.md)

Goal: a new model (other geometry) should need a map of the membrane and about five boundary lines, not 225 face lines and 4,481 boundary-cell lines. This is the design that was reviewed and implemented; INPUT_SPEC.md is the reference for the formats.

Names: the outer cells of the box are **boundary cells** (`IDOMAIN = 2`, formerly "ghost cells"). Indices are 1-based, MODFLOW names, as in INPUT_SPEC.md (`ILAY` = slices Y, `IROW` = rows X, `ICOL` = away from the source, `ICOL = 1` touches the membrane).

## 1. SRC: the faces become a map
```
BEGIN source
  VOLUME 5625.0
  START_CONC 1.0
END source

BEGIN faces
  FACES
    INTERNAL
    # ILAY 1  (values along IROW 1..43)
    0 0 0 0 0 ...                 <- one line per ILAY, NROW values, IROW fastest
    ...
END faces
```
The map is the plane `ICOL = 1`: NLAY lines of NROW numbers. Each number is what the source meets at that cell:

| value | meaning |
|---|---|
| 0 | no face (solid plate or nothing; the cell has no source neighbour) |
| 1 | membrane (coefficient K_membrane) |
| 2 | hole (no membrane; sand coefficient) |
| 3 | closed (impermeable wall) |

Checks: the map has NLAY*NROW values; a face value 1, 2 or 3 needs `IDOMAIN = 1` in that cell at `ICOL = 1` (else error). The old list format (`ilay irow [TYPE]`) is not read any more; `tools/convert_input.py` converts it. `tools/make_holes.py` writes the map. Still one source cell touching `ICOL = 1`.

## 2. BND: boundary rules
```
BEGIN boundary                 # evaluated in this order, after the fluid cells and the source
  IROW=1     COPY 0.82
  IROW=NROW  COPY 0.82
  ICOL=NCOL  COPY 0.82
  ILAY=1     COPY 0.82
  ILAY=NLAY  COPY 0.82
END boundary
```
Each line names one side of the box and one rule:
- `COPY factor`: every boundary cell (`IDOMAIN = 2`) on that side gets `factor` times the new value of the cell one step inward (normal to the side).
- `FIXED value`: the cell gets the constant.
- `NOFLOW`: the same as `COPY 1.0` (zero gradient, no flux through the side).

A cell on two sides (an edge or a corner) takes the rule of the later line, and its inward neighbour may itself be a boundary cell set by an earlier line. In the order above this is exactly what the spreadsheet does (rows first, then the far end, then the layers, edges copying already-set boundary cells). Sides without a line leave their boundary cells at their start value (`STRT`). Which cells are boundary cells is still given by `IDOMAIN = 2` in the DIS file; a solid cell (0) is never touched.

### Exceptions (optional)
```
BEGIN boundary_cells           # per cell, applied after the rules, in file order
  ilay irow icol FIXED value
  ilay irow icol COPY slay srow scol factor
END boundary_cells
BEGIN neighbor_overrides       # unchanged
  ...
END neighbor_overrides
```
These carry the spreadsheet's two irregularities in `data/reduced_matrix`: the 82 fixed zeros and the 2 corner cells next to them as `boundary_cells`, the 861 shifted neighbours as `neighbor_overrides`. `data/reduced_matrix_intended` has the five rules and no exceptions. A set with only a `boundary_cells` list and no `boundary` block still works (the old explicit list, renamed from `ghosts`).

## 3. Checks that must pass before merging
1. The five rules, expanded by the program, give the same boundary cells and factors as today's explicit list for both Reduced_Matrix sets (compared as sets, plus identical results).
2. A 28-day run of each converted set equals the current results exactly (max abs difference 0.0, probes identical); the 576-step comparison with `3d_nonzeroboundry.xlsx` and the `Day_001.xlsx` comparison stay at 1e-16.
3. All ctests, including the holes tests and the sealed box, with the sets converted; new tests: a wrong face value, a face over a non-fluid cell and a side index that is neither first nor last are refused with a clear message. (A side without a rule line is allowed: its boundary cells keep their start value.)
4. `make_holes.py`, `make_test_case.py`, `xlsx2memdif.py`, `convert_layout.py`, the plot and animation tools read and write the new files.

## 4. Later (not part of this change)
`tools/make_box_model.py`: write a complete input set (DIS, faces map, boundary rules, parameters) for a box with a rectangular source footprint, so a new geometry is one command.

## Open points for you
- Is the side name format `IROW=1`, `IROW=NROW`, `ILAY=1`, `ILAY=NLAY`, `ICOL=NCOL` clear, or do you prefer `-ROW`, `+ROW`, `-LAY`, `+LAY`, `+COL`?
- OK to stop reading the old face list (converter provided), instead of supporting both?
