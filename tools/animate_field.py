#!/usr/bin/env python3
"""Animated GIF of the memdif3d daily field files, with a face view and/or a side view.

    python3 animate_field.py RUN_DIR --nam path/to/memdif3d.nam --out solute.gif
    python3 animate_field.py RUN_DIR --side off              # face view only
    python3 animate_field.py RUN_DIR --face off --log        # side view only, log colour scale

Needs: numpy, matplotlib, Pillow   (pip install numpy matplotlib pillow)

Views (axis names follow docs/MODEL_SPEC.md: X = rows = IROW, Y = slices = ILAY, Z = away from the source = ICOL)
  face  XY plane at one Z layer (default: the first layer beyond the plate; --face-z 1 shows the
        cells touching the membrane); the white dashed box is the source footprint.
  side  a section through the source: --side-plane xz (default, one slice = one tile of the
        spreadsheet) or yz. The source cell is drawn as an extra column on the left.
Frames are the field_*.csv files of RUN_DIR (one per period); with --nam the initial state is
added as the first frame. Solid cells are grey; boundary cells are hidden unless --show-boundary.
"""
import argparse
import glob
import os
import re
import sys

try:
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import colors
    from matplotlib.animation import FuncAnimation, PillowWriter
    from matplotlib.patches import Rectangle
except ImportError as e:                       # pragma: no cover
    sys.exit(f'animate_field.py needs numpy, matplotlib and Pillow ({e}). Install: pip install numpy matplotlib pillow')


def on_off(s):
    s = s.lower()
    if s in ('on', 'yes', 'true', '1'):
        return True
    if s in ('off', 'no', 'false', '0'):
        return False
    raise argparse.ArgumentTypeError('use on or off')


def read_field(path):
    """-> (array[ILAY, IROW, ICOL] = [Y, X, Z], dict(period, step, minutes, cm))"""
    rows, info, cur = [], {}, None
    for line in open(path):
        if line.startswith('#'):
            if line.startswith('# memdif3d field'):
                m = re.search(r'period (\d+), step (\d+), minutes ([\d.]+), CM\s+(\S+)', line)
                info = dict(period=int(m.group(1)), step=int(m.group(2)), minutes=float(m.group(3)), cm=float(m.group(4)))
            elif line.startswith('# ILAY'):
                cur = []
                rows.append(cur)
            continue
        if line.strip():
            cur.append([float(t) for t in line.split(',')])
    return np.array(rows), info                       # [ICOL, IROW, ILAY] = [ILAY, IROW, ICOL]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run_dir', help='folder with field_*.csv')
    ap.add_argument('--nam', help='name file of the run: gives solid/boundary cells, source footprint, initial frame')
    ap.add_argument('--out', default='solute.gif')
    ap.add_argument('--face', type=on_off, default=True, metavar='on|off', help='face view (default on)')
    ap.add_argument('--side', type=on_off, default=True, metavar='on|off', help='side view (default on)')
    ap.add_argument('--face-z', type=int, default=None,
                    help='ICOL layer of the face view (default: first layer where most cells are fluid, or 1)')
    ap.add_argument('--side-plane', choices=['xz', 'yz'], default='xz')
    ap.add_argument('--slice', type=int, default=None, help='ILAY (xz) or IROW (yz) of the side view; default: source centre')
    ap.add_argument('--pattern', default='field_*.csv')
    ap.add_argument('--every', type=int, default=1, help='use every n-th file')
    ap.add_argument('--log', action='store_true', help='logarithmic colour scale')
    ap.add_argument('--vmin', type=float, default=None)
    ap.add_argument('--vmax', type=float, default=None)
    ap.add_argument('--cmap', default='viridis')
    ap.add_argument('--fps', type=float, default=4.0)
    ap.add_argument('--dpi', type=int, default=90)
    ap.add_argument('--show-boundary', action='store_true')
    ap.add_argument('--no-initial', action='store_true', help='do not add the initial state as first frame')
    a = ap.parse_args()
    if not (a.face or a.side):
        sys.exit('nothing to draw: switch at least one of --face / --side on')

    files = sorted(glob.glob(os.path.join(a.run_dir, a.pattern)))[::max(a.every, 1)]
    if not files:
        sys.exit(f'no files {a.pattern} in {a.run_dir}')
    frames = [read_field(f) for f in files]
    ny, nx, nz = frames[0][0].shape

    # geometry from the input files (optional)
    hidden = np.zeros((ny, nx, nz), bool)
    faces, c0 = None, None
    if a.nam:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import memdif_proto as P
        m = P.Model(a.nam)
        if (m.nx, m.ny, m.nz) != (nx, ny, nz):
            sys.exit('name file and field files have different grid sizes')
        for (x, iy, iz), code in m.idom.items():
            if code == 0 or (code == 2 and not a.show_boundary):
                hidden[iy - 1, x - 1, iz - 1] = True
        faces = list(m.faces)                                                   # (IROW, ILAY)
        c0 = np.zeros((ny, nx, nz))
        for (x, iy, iz), v in m.c0.items():
            c0[iy - 1, x - 1, iz - 1] = v
        if not a.no_initial:
            frames.insert(0, (c0, dict(period=0, step=0, minutes=0.0, cm=m.cm0)))
    if a.face_z is None:
        a.face_z = 1
        for z in range(nz):
            if hidden[:, :, z].mean() < 0.5:
                a.face_z = z + 1
                break
    if faces:
        fx = sorted(x for x, _ in faces)
        fy = sorted(y for _, y in faces)
        box = (min(fx), max(fx), min(fy), max(fy))
        cx, cy = fx[len(fx) // 2], fy[len(fy) // 2]
    else:
        box, cx, cy = None, nx // 2 + 1, ny // 2 + 1

    # colour scale from all frames
    allv = [np.where(hidden, np.nan, f[0]) for f in frames]
    vmax = a.vmax if a.vmax is not None else max(np.nanmax(v) for v in allv + [np.array([max(f[1]['cm'] for f in frames)])])
    vmin = a.vmin if a.vmin is not None else (vmax * 1e-4 if a.log else 0.0)
    norm = colors.LogNorm(vmin=vmin, vmax=vmax) if a.log else colors.Normalize(vmin=vmin, vmax=vmax)
    cmap = plt.get_cmap(a.cmap).copy()
    cmap.set_bad('#c8c8c8')

    def shaped(v):
        return np.where(v < vmin, vmin, v) if a.log else v

    def face_img(arr, hid):
        z = a.face_z - 1
        img = np.where(hid[:, :, z], np.nan, arr[:, :, z])           # [ILAY, IROW]
        return shaped(img)

    def side_img(arr, hid, cm):
        if a.side_plane == 'xz':
            k = (a.slice or cy) - 1
            img = np.where(hid[k], np.nan, arr[k])                       # [IROW, ICOL]
            src = np.full((nx, 1), np.nan)
            if box:
                src[box[0] - 1:box[1]] = cm
        else:
            k = (a.slice or cx) - 1
            img = np.where(hid[:, k, :], np.nan, arr[:, k, :])           # [ILAY, ICOL]
            src = np.full((ny, 1), np.nan)
            if box:
                src[box[2] - 1:box[3]] = cm
        return shaped(np.hstack([src, img]))                             # source column first

    n = int(a.face) + int(a.side)
    fig, axes = plt.subplots(1, n, figsize=(4.6 * n + 1.2, 4.6), constrained_layout=True)
    axes = np.atleast_1d(axes)
    arr0, info0 = frames[0]
    ims, ai = {}, 0
    if a.face:
        ax = axes[ai]
        ai += 1
        ims['face'] = ax.imshow(face_img(arr0, hidden), origin='lower', cmap=cmap, norm=norm, aspect='equal',
                                extent=(0.5, nx + 0.5, 0.5, ny + 0.5), interpolation='nearest')
        ax.set_xlabel('IROW (row)')
        ax.set_ylabel('ILAY (column)')
        ax.set_title(f'face view  (XY, ICOL = {a.face_z})', fontsize=10)
        if box:
            ax.add_patch(Rectangle((box[0] - 0.5, box[2] - 0.5), box[1] - box[0] + 1, box[3] - box[2] + 1,
                                   fill=False, ec='white', ls='--', lw=1))
    if a.side:
        ax = axes[ai]
        if a.side_plane == 'xz':
            k, nrow, ylab, what = (a.slice or cy), nx, 'IROW (row)', f'ILAY = {a.slice or cy}'
        else:
            k, nrow, ylab, what = (a.slice or cx), ny, 'ILAY (column)', f'IROW = {a.slice or cx}'
        ims['side'] = ax.imshow(side_img(arr0, hidden, info0['cm']), origin='lower', cmap=cmap, norm=norm, aspect='equal',
                                extent=(-0.5, nz + 0.5, 0.5, nrow + 0.5), interpolation='nearest')
        ax.axvline(0.5, color='white', lw=0.8)
        ax.set_xlabel('ICOL (Z; 0 = source cell)')
        ax.set_ylabel(ylab)
        ax.set_title(f'side view  ({a.side_plane.upper()}, {what})', fontsize=10)
    cb = fig.colorbar(next(iter(ims.values())), ax=list(axes), shrink=0.85)
    cb.set_label('concentration' + (' (log scale)' if a.log else ''))
    title = fig.suptitle('', fontsize=11)

    def label(info):
        day = info['minutes'] / 1440.0
        return f"t = {info['minutes']:.0f} min  ({day:.2f} d)    source CM = {info['cm']:.4f}"

    def update(i):
        arr, info = frames[i]
        if 'face' in ims:
            ims['face'].set_data(face_img(arr, hidden))
        if 'side' in ims:
            ims['side'].set_data(side_img(arr, hidden, info['cm']))
        title.set_text(label(info))
        return list(ims.values()) + [title]

    anim = FuncAnimation(fig, update, frames=len(frames), blit=False)
    anim.save(a.out, writer=PillowWriter(fps=a.fps), dpi=a.dpi)
    print(f'wrote {a.out}: {len(frames)} frames, face {"on" if a.face else "off"}, side {"on" if a.side else "off"}')


if __name__ == '__main__':
    main()
