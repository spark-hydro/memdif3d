#!/usr/bin/env python3
"""Animated GIF that compares two runs side by side (e.g. without and with membrane holes).

    python3 animate_compare.py RUN_A RUN_B --nam-a A.nam --nam-b B.nam --pattern 'snap_*.csv' --out compare.gif

Rows: face view (XY at one Z layer) and side view (XZ section through the source). Columns: run A,
run B, and B - A (red = B higher). Both runs need the same grid and the same frame files, so make them
with the same --snapshot-every and period length. Colour scales are shared between A and B.

Needs: numpy, matplotlib, Pillow
"""
import argparse
import glob
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Rectangle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from animate_field import read_field  # noqa: E402
import memdif_proto as P              # noqa: E402


def load(run, nam, pattern, every):
    files = sorted(glob.glob(os.path.join(run, pattern)))[::max(every, 1)]
    if not files:
        sys.exit(f'no files {pattern} in {run}')
    frames = [read_field(f) for f in files]
    m = P.Model(nam)
    ny, nx, nz = frames[0][0].shape
    hidden = np.ones((ny, nx, nz), bool)
    c0 = np.zeros((ny, nx, nz))
    for (x, iy, iz), code in m.idom.items():
        hidden[iy - 1, x - 1, iz - 1] = code != 1
        c0[iy - 1, x - 1, iz - 1] = m.c0[(x, iy, iz)]
    frames.insert(0, (c0, dict(period=0, step=0, minutes=0.0, cm=m.cm0)))
    return m, frames, hidden


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run_a')
    ap.add_argument('run_b')
    ap.add_argument('--nam-a', required=True)
    ap.add_argument('--nam-b', required=True)
    ap.add_argument('--label-a', default='without holes')
    ap.add_argument('--label-b', default='with holes')
    ap.add_argument('--pattern', default='field_*.csv')
    ap.add_argument('--every', type=int, default=1)
    ap.add_argument('--face-z', type=int, default=1, help='ICOL layer of the face view (default 1, touching the membrane)')
    ap.add_argument('--slice', type=int, default=None, help='ILAY of the side view (default: source centre)')
    ap.add_argument('--zmax', type=int, default=12, help='side view shows ICOL = 1..zmax (default 12)')
    ap.add_argument('--log', action='store_true')
    ap.add_argument('--vmax', type=float, default=None)
    ap.add_argument('--cmap', default='viridis')
    ap.add_argument('--fps', type=float, default=4.0)
    ap.add_argument('--dpi', type=int, default=80)
    ap.add_argument('--out', default='compare.gif')
    a = ap.parse_args()

    ma, fa, hid = load(a.run_a, a.nam_a, a.pattern, a.every)
    mb, fb, hidb = load(a.run_b, a.nam_b, a.pattern, a.every)
    if len(fa) != len(fb) or fa[0][0].shape != fb[0][0].shape or (hid != hidb).any():
        sys.exit('the two runs must have the same grid, domain and number of frames')
    ny, nx, nz = fa[0][0].shape
    faces = list(ma.faces)
    fx, fy = sorted(f[0] for f in faces), sorted(f[1] for f in faces)
    box = (fx[0], fx[-1], fy[0], fy[-1])
    iy = a.slice or fy[len(fy) // 2]
    zc = min(a.zmax, nz)

    vmax = a.vmax or max(max(np.nanmax(np.where(hid, np.nan, f[0])) for f in fr) for fr in (fa, fb))
    vmin = vmax * 1e-4 if a.log else 0.0
    norm = colors.LogNorm(vmin=vmin, vmax=vmax) if a.log else colors.Normalize(vmin=vmin, vmax=vmax)
    cmap = plt.get_cmap(a.cmap).copy()
    cmap.set_bad('#c8c8c8')

    dmax = max(np.nanmax(np.abs(np.where(hid, np.nan, x[0] - y[0]))) for x, y in zip(fa, fb)) or 1.0
    dnorm = colors.Normalize(vmin=-dmax, vmax=dmax)
    dmap = plt.get_cmap('RdBu_r').copy()
    dmap.set_bad('#c8c8c8')

    def face(arr):
        return np.where(hid[:, :, a.face_z - 1], np.nan, arr[:, :, a.face_z - 1])

    def side(arr, cm):
        img = np.where(hid[iy - 1, :, :zc], np.nan, arr[iy - 1, :, :zc])
        src = np.full((nx, 1), np.nan)
        src[box[0] - 1:box[1]] = cm
        return np.hstack([src, img])

    def shaped(v):
        return np.where(v < vmin, vmin, v) if a.log else v

    fig, ax = plt.subplots(2, 3, figsize=(13, 8.2), constrained_layout=True)
    ims = {}
    ext_f = (0.5, nx + 0.5, 0.5, ny + 0.5)
    ext_s = (-0.5, zc + 0.5, 0.5, nx + 0.5)
    a0, b0 = fa[0], fb[0]
    for j, (fr, lab) in enumerate(((a0, a.label_a), (b0, a.label_b))):
        ims['f', j] = ax[0, j].imshow(shaped(face(fr[0])), origin='lower', cmap=cmap, norm=norm, extent=ext_f, interpolation='nearest')
        ims['s', j] = ax[1, j].imshow(shaped(side(fr[0], fr[1]['cm'])), origin='lower', cmap=cmap, norm=norm, extent=ext_s, interpolation='nearest')
        ax[0, j].set_title(f'{lab}: face (XY, ICOL = {a.face_z})', fontsize=9)
        ax[1, j].set_title(f'{lab}: side (XZ, ILAY = {iy})', fontsize=9)
    ims['f', 2] = ax[0, 2].imshow(face(a0[0] * 0), origin='lower', cmap=dmap, norm=dnorm, extent=ext_f, interpolation='nearest')
    ims['s', 2] = ax[1, 2].imshow(side(a0[0] * 0, 0.0), origin='lower', cmap=dmap, norm=dnorm, extent=ext_s, interpolation='nearest')
    ax[0, 2].set_title('difference: face', fontsize=9)
    ax[1, 2].set_title('difference: side', fontsize=9)
    for j in range(3):
        ax[0, j].set_xlabel('IROW (row)')
        ax[0, j].set_ylabel('ILAY (column)')
        ax[0, j].add_patch(Rectangle((box[0] - 0.5, box[2] - 0.5), box[1] - box[0] + 1, box[3] - box[2] + 1, fill=False, ec='white', ls='--', lw=1))
        ax[1, j].axvline(0.5, color='white', lw=0.8)
        ax[1, j].set_xlabel('ICOL (0 = source cell)')
        ax[1, j].set_ylabel('IROW (row)')
    cb = fig.colorbar(ims['f', 0], ax=ax[:, :2], shrink=0.8)
    cb.set_label('concentration' + (' (log)' if a.log else ''))
    cd = fig.colorbar(ims['f', 2], ax=ax[:, 2], shrink=0.8)
    cd.set_label('difference')
    title = fig.suptitle('', fontsize=12)

    def update(i):
        (A, ia), (B, ib) = fa[i], fb[i]
        ims['f', 0].set_data(shaped(face(A)))
        ims['s', 0].set_data(shaped(side(A, ia['cm'])))
        ims['f', 1].set_data(shaped(face(B)))
        ims['s', 1].set_data(shaped(side(B, ib['cm'])))
        ims['f', 2].set_data(face(B - A))
        ims['s', 2].set_data(side(B - A, ib['cm'] - ia['cm']))
        title.set_text(f"t = {ia['minutes']:.0f} min ({ia['minutes'] / 60:.2f} h)    source CM: {ia['cm']:.5f} vs {ib['cm']:.5f}")
        return list(ims.values())

    FuncAnimation(fig, update, frames=len(fa), blit=False).save(a.out, writer=PillowWriter(fps=a.fps), dpi=a.dpi)
    print(f'wrote {a.out}: {len(fa)} frames')


if __name__ == '__main__':
    main()
