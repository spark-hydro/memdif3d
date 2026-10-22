# MEMDIF3D model spec for the Fortran port

Extracted from the formulas in `Reduced_Matrix.xlsx` (block 2, rows 50:92, which is "time t+1 from time t = rows 6:48").
**Validated:** the rule set below, including the two spreadsheet quirks in section 6, reproduces every formula cell of the sheet on a random concentration field to rounding error (max abs difference 2e-16 over 28,109 fluid cells, plus the source cell). Scripts are in `tools/`.

**Axis naming follows the voice recording:** each slice is an XZ plane, Z points away from the source cell through the membrane, and the stack of slices is Y.

| Axis | Sheet direction | Range | Size |
|---|---|---|---|
| X | rows of a block (row = 5+X in block t, 49+X in block t+1) | 1..43 | 43 |
| Y | slice = group of columns | 0..28 | 29 |
| Z | column within a slice, 0 touches the membrane | 0..24 | 25 |

(The Python scripts in `tools/` use the older names: their `z` = X here, their `x` = Z here, `y` = Y.)

## 1. Physics in one line
Explicit finite-volume diffusion (plus an upwind advection term along X, currently off) of a conservative/retarded tracer on a 43 x 29 x 25 grid of 1 mm cubes. One fully mixed source cell (V = 5625 mm3) leaks through a membrane face into the sand. Time step = 1 min.

## 2. Parameters (row 1-4 cells the formulas read)
| Symbol | Cell | Value | Meaning |
|---|---|---|---|
| D_m, tau_m, phi_m, l_m | GD1, GD2, GD3, GD4 | 0.125, 1, 0.02, 0.3 | membrane diffusion (1.8/24/60*100), tortuosity, porosity, thickness |
| Km | GG1 | D_m*phi_m/l_m/tau_m = 8.3333e-3 | membrane mass-transfer coefficient |
| D_s, tau_s, phi_s, l_s | GJ1, GJ2, GJ3, GJ4 | 0.125, 2.5, 0.3, 1 | sand diffusion, tortuosity, porosity, path length |
| Ks | GM1 | D_s*phi_s/l_s/tau_s = 0.015 | sand mass-transfer coefficient |
| phi, rho, Kd | GT1, GT2, GT3 | 0.3, 1.6, 0 | porosity, bulk density, sorption Kd |
| R | GV1 | phi + rho*Kd = 0.3 | retardation |
| V | GQ1 | 5625 | source volume = 15 x 15 x 25 |
| v | FZ1 | 0/24/60 = 0 | advection (along X), Courant number per step |

Derived: `ks = Ks/R = 0.05`, `km = Km/R = 0.02778`. Columns DG..DU in rows 1-4 hold an older parameter set that **no formula uses**.

Explicit stability: need `6*ks + |v| <= 1` (and `5*ks + km + ... <= 1` next to the source). Now 0.30. Recheck if D, R or the step change.

## 3. Grid and index mapping
Cell (X, Y, Z). Sheet column of (Y, Z): `col = base(Y) + Z`, with
`base(Y) = 1 + 26*Y` for Y = 0..6; `157 + 27*(Y-6)` for Y = 7..27; `750` for Y = 28.
(Slice stride is 26 columns for Y <= 6, 27 from Y = 6 to 7 up to 27, and 26 from 27 to 28; see quirk 1.)
The M column of slice Y (Y = 7..21) is `base(Y) - 1` (that is Z = -1), rows X = 15..29.

Regions:
- **Footprint** F: `X = 15..29` and `Y = 7..21` (15 x 15 = 225 membrane faces).
- **Source M**: one value `CM`; the sheet repeats it in 225 cells (one per footprint cell, at Z = -1) and they are always equal.
- **Solid plate**: cells with `Z <= 2` that are NOT in F. Constant 0, never updated, never read.
- **Ghost (boundary) cells**: `Y = 0`, `Y = 28`, `X = 1`, `X = 43`, `Z = 24`.
- **Fluid cells**: everything else (`Y = 1..27`, `X = 2..42`, `Z = 0..23`, not solid). Count 28,109.

## 4. Update rule (one step, t -> t+1, using old C for fluid cells)
For each fluid cell, with `u = C(X,Y,Z)`:

```
C'(X,Y,Z) = u
          + ks * sum over existing non-solid face neighbours n of (C_n - u)      [X+-1, Y+-1, Z+-1]
          + km * (CM - u)                  only for Z = 0 and (X,Y) in F  (neighbour Z-1 is M)
          + v * (C(X+1,Y,Z) - u)           for every fluid cell EXCEPT Z = 0..2 with (X,Y) in F
```
Neighbour rules: a neighbour is skipped if it is a solid-plate cell or outside the grid; ghost cells count as neighbours (old values). For Z = 0 in F the Z-1 neighbour is M (coefficient km, not ks). For Z = 3 the Z-1 neighbour is Z = 2, fluid only if (X,Y) in F, otherwise solid and skipped.

Source cell:
```
CM' = CM - (Km / V) * sum over (X,Y) in F of ( CM - C(X,Y,0) )
```
(uses Km, not Km/R; 225 terms, old values).

Ghost cells (computed AFTER the new fluid values and the new CM, in this order):
1. `X = 1`, Y = 1..27, Z = 3..23: `0.82 * C'(2,Y,Z)`; `X = 43`: `0.82 * C'(42,Y,Z)`. (Z = 0..2 at X = 1/43 are solid constants 0.)
2. `Z = 24`, Y = 1..27, X = 1..43: `0.82 * C'(X,Y,23)` (see quirk 2).
3. `Y = 0`: `0.82 * C'(X,1,Z)`; `Y = 28`: `0.82 * C'(X,27,Z)`, for all X = 1..43, Z = 0..24 (copies the new slice 1 / 27 incl. ghosts and solid zeros).

Ghost cells at time t+1 therefore depend on t+1 values of their interior neighbour; fluid cells at t+1 read ghost values from time t.

## 5. Initial condition
`CM = 1` (the 225 M cells = 1), all fluid and ghost cells 0. The sheet's `GA17 = $GQ$1` and `GA61 = $GQ$1*GA64` are mass bookkeeping cells (V*C); nothing reads them, so the model does not need them.

## 6. Spreadsheet quirks (replicate for exact agreement, or fix)
The formulas deviate from the pattern in two places. Both are far from the source but they are real, so decide whether the Fortran should copy them (`excel_quirks = .true.`) or follow the intended pattern.
1. **Slice Y = 27 reads slice 28 shifted by one Z.** Its +Y neighbour formula uses a +27 column offset but the last slice stride is 26, so cell (X,27,Z) reads ghost (X,28,Z+1) instead of (X,28,Z). Affects 861 cells (X = 2..42, Z = 3..23).
2. **Z = 24 ghost is a constant 0** (not 0.82*Z23) for slices `Y = 20` and `Y = 26`, rows X = 2..42 (82 cells). Corner rows X = 1 and 43 at Z = 24: slice 20 follows the normal rule (0.82*Z23), slice 26 reads the constant neighbour so it is 0.

## 7. Fortran sketch
- `real(8) :: C(1:43, 0:28, 0:24), Cn(...)`, `logical :: solid(...)`, scalar `CM`. Build `solid` and the footprint mask once. Put Z (contiguous in memory) as the first index if you want the fastest inner loop: `C(0:24, 0:28, 1:43)`.
- Precompute per-cell neighbour flags (or loop over the interior with the solid mask); roughly 28k cells x ~10 flops per step, 40,320 steps for 28 days is about 1.3e9 cell-updates: seconds to a few minutes single-threaded, less with OpenMP.
- Per step: fluid update -> CM -> ghosts (order above) -> swap.
- Output per day: the full field written with the sheet's cell layout (so it can be compared with `Day_NNN.xlsx`), minute-by-minute probe values, and a restart file. Use the same file names as the VBA version.
- Test plan: (1) the t=1 step against the Excel sheet cached values; (2) a few hundred steps against the VBA `Day_001.xlsx` and its Minutes sheet; (3) mass balance: `V*CM + phi-weighted sum of fluid mass` conserved to rounding while ghosts are not absorbing (ghosts at 0.82 are, so check only early).

## 8. About `3d_nonzeroboundry.xlsx` (460 MB)
Streamed, not opened. 50,736 rows, A:ACT, 44-row block period (1152 blocks) like the small file. But it is not a clean continuous chain: formula blocks appear in runs of about 9 every 18 blocks, with zero-valued or empty blocks in between, some formulas reach 440 rows (10 blocks) up, and 13,634 rows are missing entirely. Treat `Reduced_Matrix.xlsx` as the source of truth for the spec; ask the user how the big file was produced before relying on it.
