#!/usr/bin/env python3
"""Interactive 3D animation of the memdif3d field files: one self-contained HTML file.

    python3 animate_3d.py RUN_DIR --nam path/to/memdif3d.nam --out solute3d.html
    python3 animate_3d.py RUN_DIR --nam ... --log --pattern 'snap_*.csv'

Open the HTML in any browser (no server, no internet). Drag to rotate, scroll to zoom, right-drag to
pan; the Play button and the slider run the time series and the view stays where you put it.

Axes (mm): x = distance from the membrane (ICOL), y = IROW (rows), z = ILAY (columns). The source cell is the
slab at x < 0 coloured by its concentration. Little squares at the membrane plane mark the faces:
grey = membrane, red = hole, black = closed. Solid and boundary cells are not drawn.
Frames are the field_*.csv files (one per period); the initial state is added as the first frame.

Needs: numpy, plotly   (pip install numpy plotly)
"""
import argparse
import glob
import os
import sys

try:
    import numpy as np
    import plotly.graph_objects as go
except ImportError as e:                       # pragma: no cover
    sys.exit(f'animate_3d.py needs numpy and plotly ({e}). Install: pip install numpy plotly')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from animate_field import read_field           # noqa: E402
import memdif_proto as P                       # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run_dir', help='folder with field_*.csv')
    ap.add_argument('--nam', required=True, help='name file of the run (geometry, source, initial state)')
    ap.add_argument('--out', default='solute3d.html')
    ap.add_argument('--pattern', default='field_*.csv')
    ap.add_argument('--every', type=int, default=1, help='use every n-th file')
    ap.add_argument('--log', action='store_true', help='logarithmic colour scale')
    ap.add_argument('--vmin', type=float, default=None, help='lowest concentration drawn (default 1e-4 of the maximum with --log, else 0.02 of it)')
    ap.add_argument('--vmax', type=float, default=None)
    ap.add_argument('--opacity', type=float, default=0.12, help='opacity of the cloud (0..1, default 0.12)')
    ap.add_argument('--surfaces', type=int, default=18, help='number of iso-surfaces in the cloud (default 18)')
    ap.add_argument('--cmap', default='Viridis')
    ap.add_argument('--no-initial', action='store_true')
    ap.add_argument('--frame-ms', type=int, default=400, help='display time of one frame in the player')
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.run_dir, a.pattern)))[::max(a.every, 1)]
    if not files:
        sys.exit(f'no files {a.pattern} in {a.run_dir}')
    frames = [read_field(f) for f in files]
    m = P.Model(a.nam)
    ny, nx, nz = frames[0][0].shape
    if (m.nx, m.ny, m.nz) != (nx, ny, nz):
        sys.exit('name file and field files have different grid sizes')
    c0 = np.zeros((ny, nx, nz))
    fluid = np.zeros((ny, nx, nz), bool)
    for (x, iy, iz), v in m.c0.items():
        c0[iy - 1, x - 1, iz - 1] = v
        fluid[iy - 1, x - 1, iz - 1] = m.idom[(x, iy, iz)] == 1
    if not a.no_initial:
        frames.insert(0, (c0, dict(period=0, step=0, minutes=0.0, cm=m.cm0)))

    # crop to the fluid cells; the grid is [ILAY, IROW, ICOL]
    ys, xs, zs = (np.where(fluid.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3))
    sl = (slice(ys[0], ys[-1] + 1), slice(xs[0], xs[-1] + 1), slice(zs[0], zs[-1] + 1))
    msk = fluid[sl]
    gy, gx, gz = np.meshgrid(np.arange(ys[0], ys[-1] + 1) + 1, np.arange(xs[0], xs[-1] + 1) + 1,
                             np.arange(zs[0], zs[-1] + 1) + 1, indexing='ij')

    cmax = max(float(max(f[0][sl][msk].max(), f[1]['cm']) if True else 0) for f in frames)
    vmax = a.vmax or cmax
    vmin = a.vmin or (vmax * (1e-4 if a.log else 0.02))
    if a.log:
        lo, hi = np.log10(vmin), np.log10(vmax)
        conv = lambda v: np.round(np.log10(np.maximum(v, vmin)), 3)                 # noqa: E731
    else:
        lo, hi = vmin, vmax
        conv = lambda v: np.round(np.maximum(v, vmin), 5)                           # noqa: E731

    def cloud(c):
        v = np.where(msk, conv(c[sl]), lo)              # solid and boundary cells sit at the floor: invisible
        return v.ravel()

    # the source slab: x from -1 to 0 under the footprint (cells are 1 mm, centres at integers)
    fx = [f[0] for f in m.faces] or [1]
    fy = [f[1] for f in m.faces] or [1]
    x0, x1 = min(fx) - .5, max(fx) + .5
    y0, y1 = min(fy) - .5, max(fy) + .5
    zt = -1.5
    X = [x0, x1, x1, x0, x0, x1, x1, x0]
    Y = [y0, y0, y1, y1, y0, y0, y1, y1]
    Z = [zt, zt, zt, zt, 0.5, 0.5, 0.5, 0.5]
    tri = dict(i=[0, 0, 4, 4, 0, 0, 1, 1, 2, 2, 3, 3], j=[1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 0, 4],
               k=[2, 3, 6, 7, 5, 4, 6, 5, 7, 6, 4, 7])
    ticks = ''

    def cm_val(f):
        return [float(conv(np.array(f[1]['cm'])))] * 8

    # plot axes: x = distance (ICOL), y = IROW, z = ILAY
    vol = go.Volume(x=gz.ravel(), y=gx.ravel(), z=gy.ravel(), value=cloud(frames[0][0]),
                    isomin=lo + 0.02 * (hi - lo), isomax=hi, surface_count=a.surfaces, opacity=a.opacity,
                    coloraxis='coloraxis', caps=dict(x_show=False, y_show=False, z_show=False), name='solute',
                    showlegend=False)
    src = go.Mesh3d(x=Z, y=X, z=Y, intensity=cm_val(frames[0]), coloraxis='coloraxis', flatshading=True,
                    opacity=1.0, name='source', hoverinfo='skip', **tri)
    traces = [vol, src]
    marks = {'MEMBRANE': ('grey', 'membrane'), 'HOLE': ('red', 'hole'), 'CLOSED': ('black', 'closed')}
    for kind, (col, label) in marks.items():
        pts = [f for f, k in m.kind.items() if k == kind]
        if pts:
            traces.append(go.Scatter3d(x=[0.55] * len(pts), y=[p[0] for p in pts], z=[p[1] for p in pts], mode='markers',
                                       marker=dict(size=3, color=col, symbol='square'), name=label, hoverinfo='skip'))

    def label(info):
        t = info['minutes']
        return f"day {t / 1440:.2f}" if t >= 1440 or t == 0 else f"{t / 60:.1f} h"

    plot_frames = [go.Frame(name=str(i), traces=[0, 1], data=[go.Volume(value=cloud(f[0])), go.Mesh3d(intensity=cm_val(f))])
                   for i, f in enumerate(frames)]
    tv = np.linspace(lo, hi, 6)
    cbar = dict(title='concentration', tickvals=list(tv),
                ticktext=[f'{10 ** t:.2g}' if a.log else f'{t:.2g}' for t in tv])
    steps = [dict(method='animate', label=label(f[1]),
                  args=[[str(i)], dict(mode='immediate', frame=dict(duration=0, redraw=True), transition=dict(duration=0))])
             for i, f in enumerate(frames)]
    play = dict(label='Play', method='animate',
                args=[None, dict(frame=dict(duration=a.frame_ms, redraw=True), transition=dict(duration=0), fromcurrent=True)])
    pause = dict(label='Pause', method='animate',
                 args=[[None], dict(mode='immediate', frame=dict(duration=0, redraw=False), transition=dict(duration=0))])
    zr = [zs[0] + 0.5, zs[-1] + 1.5]
    span = (zr[1] - zr[0] + 1, xs[-1] - xs[0] + 1, ys[-1] - ys[0] + 1)
    fig = go.Figure(data=traces, frames=plot_frames)
    fig.update_layout(
        title=f"memdif3d: {m.nx} x {m.ny} x {m.nz} cells, {len(m.faces)} source faces"
              + (f", {len(m.hset)} holes" if m.hset else ''),
        coloraxis=dict(colorscale=a.cmap, cmin=lo, cmax=hi, colorbar=cbar),
        scene=dict(xaxis=dict(title='distance from membrane, ICOL (mm)', range=[-1.5, zs[-1] + 1.5]),
                   yaxis=dict(title='IROW (mm)'), zaxis=dict(title='ILAY (mm)'),
                   aspectmode='data', camera=dict(eye=dict(x=1.7, y=-1.7, z=1.0))),
        updatemenus=[dict(type='buttons', direction='left', x=0.02, y=0.0, xanchor='left', yanchor='top', pad=dict(t=60),
                          buttons=[play, pause])],
        sliders=[dict(active=0, x=0.18, len=0.8, y=0.0, yanchor='top', pad=dict(t=50),
                      currentvalue=dict(prefix='time: '), steps=steps)],
        margin=dict(l=0, r=0, t=50, b=0), legend=dict(x=0.01, y=0.98), height=720)
    fig.write_html(a.out, include_plotlyjs=True, full_html=True, auto_play=False)
    print(f'{len(frames)} frames, grid {msk.shape[2]}x{msk.shape[1]}x{msk.shape[0]} -> {a.out} '
          f'({os.path.getsize(a.out) / 1e6:.1f} MB)')


if __name__ == '__main__':
    main()
