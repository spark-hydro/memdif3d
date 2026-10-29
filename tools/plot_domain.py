#!/usr/bin/env python3
"""Draw the model domain from the input files, to scale: source, membrane, sand, plate, boundary cells.

    python3 plot_domain.py path/to/rm.nam --out domain.png [--iy 15]

Three panels: side view (XZ section at ILAY, everything to scale in mm), a zoom at the membrane, and a
plan view of the cells that touch the membrane (ICOL = 1). The membrane is not a layer of cells in the
model: it is a mass-transfer resistance between the source and the ICOL = 1 cells. It is drawn here at
its LENGTH from DSP so you can compare it with the 1 mm cells. A hole is a face without membrane.

Needs: numpy, matplotlib
"""
import argparse
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memdif_proto as P  # noqa: E402

COL = dict(sand='#f2dfb0', solid='#8c8c8c', boundary='#bfd9ee', source='#3a78b5', membrane='#c0392b', hole='#ffffff', closed='#222222')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('nam')
    ap.add_argument('--out', default='domain.png')
    ap.add_argument('--iy', type=int, default=None, help='slice of the side view (default: centre of the source)')
    ap.add_argument('--dpi', type=int, default=130)
    a = ap.parse_args()

    m = P.Model(a.nam)
    pk = {w[0].upper(): os.path.join(os.path.dirname(os.path.abspath(a.nam)), w[1]) for w in P.read_blocks(a.nam)['packages']}
    dsp = P.read_blocks(pk['DSP'])
    lm = P.scalar(dsp['membrane'], 'LENGTH')
    ls = P.scalar(dsp['sand'], 'LENGTH')
    fx = sorted({f[0] for f in m.kind})
    fy = sorted({f[1] for f in m.kind})
    iy = a.iy or fy[len(fy) // 2]
    depth = m.V / (len(fx) * len(fy))                     # source depth if it covers the footprint exactly

    fig = plt.figure(figsize=(15, 9.5))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1], width_ratios=[1.6, 1])
    ax = fig.add_subplot(gs[0, :])
    az = fig.add_subplot(gs[1, 0])
    ap_ = fig.add_subplot(gs[1, 1])

    def draw_side(axs, xr=None):
        # x axis: distance from the membrane surface (mm); the sand cell ICOL occupies [lm+(iz-1), lm+iz]
        for ix in range(1, m.nx + 1):
            for z in range(1, m.nz + 1):
                code = m.idom[(ix, iy, z)]
                col = COL['sand'] if code == 1 else COL['boundary'] if code == 2 else COL['solid']
                x0 = lm + (z - 1)
                if xr and (x0 > xr[1] or x0 + 1 < xr[0]):
                    continue
                axs.add_patch(Rectangle((x0, ix - 0.5), 1, 1, fc=col, ec='#9a8f70' if code == 1 else '#7a8a99', lw=0.4))
        axs.add_patch(Rectangle((-depth - 0.0, fx[0] - 0.5), depth, len(fx), fc=COL['source'], ec='k', lw=0.8))
        for ix in fx:
            k = m.kind.get((ix, iy), None)
            if k == 'HOLE':
                continue
            axs.add_patch(Rectangle((0, ix - 0.5), lm, 1, fc=COL['closed'] if k == 'CLOSED' else COL['membrane'], ec='k', lw=0.3))

    draw_side(ax)
    ax.set_xlim(-depth - 2, lm + m.nz + 1)
    ax.set_ylim(0.5, m.nx + 0.5)
    ax.set_aspect('equal')
    ax.set_xlabel('distance from the membrane (mm)  [Z, away from the source]')
    ax.set_ylabel('IROW (rows)')
    ax.set_title(f'Side view, slice ILAY = {iy} (to scale): {m.nx} x {m.ny} x {m.nz} cells of 1 mm; membrane {lm:g} mm;\n'
                 f'source {len(fx)} x {len(fy)} mm footprint, {depth:g} mm deep (V = {m.V:g} mm3)', fontsize=10, pad=12)
    ax.text(-depth / 2, fx[-1] + 2.2, 'source cell\n(one fully mixed value)', ha='center', va='bottom', fontsize=9)

    # zoom at the membrane
    xr = (-3.0, 6.0)
    draw_side(az, xr)
    az.add_patch(Rectangle((-3.0, fx[0] - 0.5), 3.0, len(fx), fc=COL['source'], ec='none'))
    for ix in fx:
        k = m.kind.get((ix, iy))
        if k == 'HOLE':
            continue
        az.add_patch(Rectangle((0, ix - 0.5), lm, 1, fc=COL['closed'] if k == 'CLOSED' else COL['membrane'], ec='k', lw=0.4))
    cx = (fx[0] + fx[-1]) / 2
    az.set_xlim(*xr)
    az.set_ylim(cx - 7.5, cx + 7.5)
    az.set_aspect('equal')
    az.set_xlabel('mm')
    az.set_title(f'Zoom at the membrane: membrane {lm:g} mm thick, sand cells 1 mm. In the model the membrane is a\n'
                 f'resistance between the source and ICOL = 1, not a row of cells.', fontsize=9)

    # plan view at ICOL = 1
    for ix in range(1, m.nx + 1):
        for y in range(1, m.ny + 1):
            code = m.idom[(ix, y, 1)]
            k = m.kind.get((ix, y))
            if k == 'HOLE':
                col = COL['hole']
            elif k == 'CLOSED':
                col = COL['closed']
            elif k == 'MEMBRANE':
                col = COL['membrane']
            else:
                col = COL['sand'] if code == 1 else COL['boundary'] if code == 2 else COL['solid']
            ap_.add_patch(Rectangle((y - 0.5, ix - 0.5), 1, 1, fc=col, ec='#666', lw=0.3))
    ap_.set_xlim(0.5, m.ny + 0.5)
    ap_.set_ylim(0.5, m.nx + 0.5)
    ap_.set_aspect('equal')
    ap_.set_xlabel('ILAY (columns)')
    ap_.set_ylabel('IROW (rows)')
    nh = sum(1 for k in m.kind.values() if k == 'HOLE')
    ap_.set_title(f'Plan view of the ICOL = 1 layer: {len(m.kind)} faces, {nh} holes', fontsize=9)

    items = [Patch(fc=COL['source'], ec='k', label='source cell'), Patch(fc=COL['membrane'], ec='k', label='membrane face')]
    if nh:
        items.append(Patch(fc=COL['hole'], ec='k', label='hole (no membrane)'))
    if any(k == 'CLOSED' for k in m.kind.values()):
        items.append(Patch(fc=COL['closed'], ec='k', label='closed face'))
    items += [Patch(fc=COL['sand'], ec='#9a8f70', label='sand (fluid) cell'), Patch(fc=COL['solid'], ec='k', label='solid plate'),
              Patch(fc=COL['boundary'], ec='#7a8a99', label='boundary cell')]
    fig.legend(handles=items, loc='lower center', ncol=len(items), frameon=False)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(a.out, dpi=a.dpi)
    print(f'{a.out}: membrane {lm:g} mm, sand cells 1 mm, source {depth:g} mm deep, side slice ILAY = {iy}')


if __name__ == '__main__':
    main()
