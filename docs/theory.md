# Theory

This page explains what the program computes. The complete rule set, with the cells of the original spreadsheet it was derived from, is in the [model specification](MODEL_SPEC.md).

## The idea
The domain is cut into cubes of 1 mm. Each cube is a control volume with one concentration \(C\). In every time step each cube exchanges solute with its six neighbours, in proportion to the concentration difference. This is a **finite-volume** scheme, **explicit** in time. Solute that leaves one cell enters the next, so mass is conserved.

Units: length in mm, time in minutes. All coefficients are per time step.

## Mass-transfer coefficients
For sand and for the membrane separately,

\[
K = \frac{D\,\phi}{L\,\tau}
\]

with the diffusion coefficient \(D\), the porosity \(\phi\), the length \(L\) over which it acts (for sand the cell size, for the membrane its thickness) and the tortuosity \(\tau\). The sorption of the sand is described by the retardation

\[
R = \phi + \rho_b K_d
\]

with the bulk density \(\rho_b\) and the sorption coefficient \(K_d\). The coefficients used in a cell update are

\[
k_s = \frac{K_s}{R}, \qquad k_m = \frac{K_m}{R}
\]

for sand and membrane.

## Update rule for a sand cell
For a fluid cell \(c\) with concentration \(C_c\),

\[
C_c^{\,n+1} = C_c + k_s \sum_{m \in N(c)} (C_m - C_c) \;+\; k_m\,(C_M - C_c)\;+\; v\,(C_{\mathrm{IROW}+1} - C_c)
\]

- \(N(c)\) are the face neighbours that are not solid; boundary cells count as neighbours.
- The \(k_m\) term exists only for the cell at \(\mathrm{ICOL}=1\) under a membrane face, where the neighbour towards the source is the source cell \(M\).
- At a **hole** the source cell touches the sand directly, so the term uses \(k_s\) instead of \(k_m\). A **closed** face has no source neighbour.
- The last term is a first-order upwind advection toward lower \(\mathrm{IROW}\) with the Courant number \(v\) per step. It is switched off in the Reduced_Matrix case (\(v = 0\)).

All cells are updated from the old values, so the order of the cells does not matter.

## The source cell
The source is one fully mixed volume \(V\) with concentration \(C_M\):

\[
C_M^{\,n+1} = C_M - \frac{K_m}{V}\sum_{f} \left(C_M - C_f\right)
\]

summed over the membrane faces \(f\), where \(C_f\) is the concentration of the sand cell under the face. For hole faces \(K_s\) replaces \(K_m\). The retardation does not enter the source balance, because the source holds only solution.

## Boundary cells
The outer cells of the box (`IDOMAIN = 2`) are not part of the medium. After each step, from the new interior values, each boundary cell gets

\[
C_b = f \cdot C_{\mathrm{inward}}
\]

with a factor \(f\) per side. With \(f = 0.82\), as in the spreadsheet, the outer layer holds 82% of the cell next to it, so a little solute drains out through every outer side. `FIXED value` sets a constant and `NOFLOW` is \(f = 1\). The rules are in [Input files](INPUT_SPEC.md#bnd-boundary-cells-and-exceptions).

## Stability
The scheme is explicit, so the time step cannot be too large. The new value is a weighted mean of old values, and the weight a cell keeps of its own old value must not be negative:

\[
1 - 6\,k_s - v \;\ge\; 0
\]

With \(k_s = 0.015/0.3 = 0.05\) the sum is \(6 k_s = 0.30\), well inside the limit. A larger diffusion coefficient, a longer step or a smaller retardation raises \(k_s\). At start-up the program computes the largest coefficient sum over all cells, including the cells at the membrane and the source cell, and stops when it exceeds 1 (`--force` overrides).

## Mass balance
In a sealed box (no boundary cells) the mass \(V\,C_M + R\sum_c C_c\) over the fluid cells stays constant to rounding error. The tests check this, and the long-time concentration against the analytic value \(V C_{M,0} / (V + R\,N_\mathrm{fluid})\). With boundary factors below 1 the box loses mass through its outer sides by design.

## Cubic cells and one membrane plane
The membrane is not made of cells. It is a resistance on the plane between the source and \(\mathrm{ICOL}=1\). All cells are 1 mm cubes and the sand is uniform. These limits are listed in [Limits and FAQ](faq.md).
