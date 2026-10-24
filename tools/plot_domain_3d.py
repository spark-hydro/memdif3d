#!/usr/bin/env python3
"""Interactive 3D picture of the model domain from the input files (one HTML file).

    python3 plot_domain_3d.py path/to/memdif3d.nam --out domain3d.html

Boxes (to scale, mm): source cell, membrane faces (red; holes open, closed faces black), solid plate (grey),
sand cells (tan), ghost boundary cells (blue). Two translucent planes mark the cuts used by the 2D views:
the side view (XZ at one IY) and the face view (XY at IZ = 1). Drag to rotate, scroll to zoom.
Axes: x = Z (distance from the membrane, IZ), y = IX (rows), z = IY (slices).

Needs: plotly
"""
import argparse
import os
import sys

import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memdif_proto as P  # noqa: E402


def box(x0, x1, y0, y1, z0, z1, color, opacity, name, show=True):
    X = [x0, x1, x1, x0, x0, x1, x1, x0]
    Y = [y0, y0, y1, y1, y0, y0, y1, y1]
    Z = [z0, z0, z0, z0, z1, z1, z1, z1]
    I = [0, 0, 4, 4, 0, 0, 1, 1, 2, 2, 3, 3]
    J = [1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 0, 4]
    K = [2, 3, 6, 7, 5, 4, 6, 5, 7, 6, 4, 7]
    return go.Mesh3d(x=X, y=Y, z=Z, i=I, j=J, k=K, color=color, opacity=opacity, name=name, showlegend=show,
                     flatshading=True, hoverinfo='name')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('nam')
    ap.add_argument('--out', default='domain3d.html')
    ap.add_argument('--iy', type=int, default=None, help='slice of the side-view plane (default: source centre)')
    a = ap.parse_args()

    m = P.Model(a.nam)
    pk = {w[0].upper(): os.path.join(os.path.dirname(os.path.abspath(a.nam)), w[1]) for w in P.read_blocks(a.nam)['packages']}
    lm = P.scalar(P.read_blocks(pk['DSP'])['membrane'], 'LENGTH')
    fx = sorted({f[0] for f in m.kind})
    fy = sorted({f[1] for f in m.kind})
    iy = a.iy or fy[len(fy) // 2]
    depth = m.V / (len(fx) * len(fy))
    h = 0.5
    code = m.idom
    fl = [p for p, c in code.items() if c == 1]
    sol = [p for p, c in code.items() if c == 0]
    gh = [p for p, c in code.items() if c == 2]
    # plot x = distance from the membrane: cell IZ spans [lm + IZ - 1, lm + IZ]
    zlo = lambda iz: lm + iz - 1                                   # noqa: E731
    xmax = zlo(m.nz) + 1
    fxa, fxb, fya, fyb = fx[0] - h, fx[-1] + h, fy[0] - h, fy[-1] + h

    tr = []
    # sand block (fluid bounding box) and ghost shell (whole grid)
    gx0, gx1 = 0.5, m.nx + 0.5
    gy0, gy1 = 0.5, m.ny + 0.5
    tr.append(box(lm, xmax, gx0, gx1, gy0, gy1, '#7fb2e5', 0.10, 'ghost (boundary) cells'))
    bx = [p[0] for p in fl]; by = [p[1] for p in fl]; bz = [p[2] for p in fl]
    tr.append(box(zlo(min(bz)), zlo(max(bz)) + 1, min(bx) - h, max(bx) + h, min(by) - h, max(by) + h, '#e8c871', 0.18, 'sand (fluid) cells'))
    # solid plate: the rows of cells at IZ = 1 that are solid, in four strips around the footprint
    pz = max(p[2] for p in sol)
    sx0 = min(p[0] for p in sol) - h; sx1 = max(p[0] for p in sol) + h
    sy0 = min(p[1] for p in sol) - h; sy1 = max(p[1] for p in sol) + h
    first = True
    for (xa, xb, ya, yb) in ((sx0, fxa, sy0, sy1), (fxb, sx1, sy0, sy1), (fxa, fxb, sy0, fya), (fxa, fxb, fyb, sy1)):
        if xb > xa and yb > ya:
            tr.append(box(lm, zlo(pz) + 1, xa, xb, ya, yb, '#8c8c8c', 0.85, 'solid plate', first))
            first = False
    # source slab and membrane
    tr.append(box(-depth, 0, fxa, fxb, fya, fyb, '#2f6db0', 0.9, f'source cell ({len(fx)} x {len(fy)} x {depth:g} mm, one value)'))
    kinds = {'MEMBRANE': ('#c0392b', 'membrane face'), 'HOLE': ('#00b050', 'hole (no membrane)'), 'CLOSED': ('#111111', 'closed face')}
    for k, (col, lab) in kinds.items():
        pts = [f for f, kk in m.kind.items() if kk == k]
        if pts:
            tr.append(go.Scatter3d(x=[lm / 2] * len(pts), y=[p[0] for p in pts], z=[p[1] for p in pts], mode='markers', name=lab,
                                   marker=dict(size=3, color=col, symbol='square'), hoverinfo='name'))
    # cut planes
    def plane(pts, color, name):
        x, y, z = zip(*pts)
        return go.Mesh3d(x=x, y=y, z=z, i=[0, 0], j=[1, 2], k=[2, 3], color=color, opacity=0.30, name=name, showlegend=True, hoverinfo='name')
    tr.append(plane([(0, gx0, iy), (xmax, gx0, iy), (xmax, gx1, iy), (0, gx1, iy)], '#ff8c00', f'side-view cut (XZ at IY = {iy})'))
    zf = zlo(1) + 0.5
    tr.append(plane([(zf, gx0, gy0), (zf, gx1, gy0), (zf, gx1, gy1), (zf, gx0, gy1)], '#9b59b6', 'face-view cut (XY at IZ = 1)'))

    fig = go.Figure(tr)
    fig.update_layout(
        title=f'memdif3d domain: {m.nx} x {m.ny} x {m.nz} cells of 1 mm (IX x IY x IZ), membrane {lm:g} mm',
        scene=dict(xaxis=dict(title='Z = IZ, away from the source (mm)'), yaxis=dict(title='X = IX (rows)'),
                   zaxis=dict(title='Y = IY (slices)'), aspectmode='data', camera=dict(eye=dict(x=1.6, y=-1.9, z=1.1))),
        legend=dict(x=0.01, y=0.99), margin=dict(l=0, r=0, t=50, b=0), height=720)
    fig.write_html(a.out, include_plotlyjs=True, full_html=True)
    print(f'wrote {a.out}')


if __name__ == '__main__':
    main()
