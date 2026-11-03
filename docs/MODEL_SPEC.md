# memdif3d model spec for the Fortran port

Extracted from the formulas in `Reduced_Matrix_fixed.xlsx` (block 2, rows 50:92, which is "time t+1 from time t = rows 6:48").
**Validated:** the rule set below, reproduces every formula cell of the sheet on a random concentration field to rounding error (max abs difference 2e-16 over 28,109 fluid cells, plus the source cell). Scripts are in `tools/`.

**MODFLOW names for the same axes:** X = row (IROW = X), Y = layer (ILAY = Y + 1, the slices), Z = column (ICOL = Z + 1, away from the source); the input files use these names (docs/INPUT_SPEC.md). The rest of this note keeps the X, Y, Z names of the recording.

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
`base(Y) = 1 + 26*Y` for Y = 0..6; `157 + 27*(Y-6)` for Y = 7..28.
(Slice stride is 26 columns for Y <= 6 and 27 from Y = 6 onwards.)
The M column of slice Y (Y = 7..21) is `base(Y) - 1` (that is Z = -1), rows X = 15..29.

Regions:
- **Footprint** F: `X = 15..29` and `Y = 7..21` (15 x 15 = 225 membrane faces).
- **Source M**: one value `CM`; the sheet repeats it in 225 cells (one per footprint cell, at Z = -1) and they are always equal.
- **Solid plate**: cells with `Z <= 2` that are NOT in F. Constant 0, never updated, never read.
- **Boundary cells**: `Y = 0`, `Y = 28`, `X = 1`, `X = 43`, `Z = 24`.
- **Fluid cells**: everything else (`Y = 1..27`, `X = 2..42`, `Z = 0..23`, not solid). Count 23,922. With 4,481 boundary cells and 2,772 solid cells this is the whole 43 x 29 x 25 = 31,175 grid.

## 4. Update rule (one step, t -> t+1, using old C for fluid cells)
For each fluid cell, with `u = C(X,Y,Z)`:

```
C'(X,Y,Z) = u
          + ks * sum over existing non-solid face neighbours n of (C_n - u)      [X+-1, Y+-1, Z+-1]
          + km * (CM - u)                  only for Z = 0 and (X,Y) in F  (neighbour Z-1 is M)
          + v * (C(X+1,Y,Z) - u)           for every fluid cell EXCEPT Z = 0..2 with (X,Y) in F
```
Neighbour rules: a neighbour is skipped if it is a solid-plate cell or outside the grid; boundary cells count as neighbours (old values). For Z = 0 in F the Z-1 neighbour is M (coefficient km, not ks). For Z = 3 the Z-1 neighbour is Z = 2, fluid only if (X,Y) in F, otherwise solid and skipped.

Source cell:
```
CM' = CM - (Km / V) * sum over (X,Y) in F of ( CM - C(X,Y,0) )
```
(uses Km, not Km/R; 225 terms, old values).

Boundary cells (computed AFTER the new fluid values and the new CM, in this order):
1. `X = 1`, Y = 1..27, Z = 3..23: `0.82 * C'(2,Y,Z)`; `X = 43`: `0.82 * C'(42,Y,Z)`. (Z = 0..2 at X = 1/43 are solid constants 0.)
2. `Z = 24`, Y = 1..27, X = 1..43: `0.82 * C'(X,Y,23)`.
3. `Y = 0`: `0.82 * C'(X,1,Z)`; `Y = 28`: `0.82 * C'(X,27,Z)`, for all X = 1..43, Z = 0..24 (copies the new slice 1 / 27 incl. boundary cells and solid zeros).

Boundary cells at time t+1 therefore depend on t+1 values of their interior neighbour; fluid cells at t+1 read boundary values from time t.

## 5. Initial condition
`CM = 1` (the 225 M cells = 1), all fluid and boundary cells 0. The sheet's `GA17 = $GQ$1` and `GA61 = $GQ$1*GA64` are mass bookkeeping cells (V*C); nothing reads them, so the model does not need them.
