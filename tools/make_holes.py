#!/usr/bin/env python3
"""Copy a memdif3d input set and punch holes in its membrane.

  python3 tools/make_holes.py data/reduced_matrix data/holes_p3 --pitch 3 --size 1 [--offset 1] [--closed]

The membrane faces of the FACES map in SRC (values 1, 2 or 3 at ICOL = 1) are laid out as a grid; every
PITCH-th face in both directions (starting at OFFSET) opens a square hole of SIZE x SIZE faces (value 2).
A hole connects the source straight to the sand (sand coefficient, no membrane). With --closed the rest
of the membrane is impermeable (value 3), so only the holes transmit; without it the membrane stays as it
is (value 1). For 15 faces, pitch 3, offset 1 one row reads  -0--0--0--0--0-  as in the sketch.
"""
import argparse
import os
import shutil


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src_dir')
    ap.add_argument('out_dir')
    ap.add_argument('--pitch', type=int, default=3, help='distance between holes in faces (default 3)')
    ap.add_argument('--size', type=int, default=1, help='hole edge in faces (default 1)')
    ap.add_argument('--offset', type=int, default=1, help='first hole, faces from the footprint corner (default 1)')
    ap.add_argument('--closed', action='store_true', help='make the membrane between holes impermeable')
    a = ap.parse_args()
    if a.size > a.pitch:
        ap.error('--size must not exceed --pitch')
    shutil.copytree(a.src_dir, a.out_dir, dirs_exist_ok=True)
    src = [f for f in os.listdir(a.out_dir) if f.endswith('.src')]
    if len(src) != 1:
        raise SystemExit('expected exactly one .src file in ' + a.out_dir)
    path = os.path.join(a.out_dir, src[0])
    lines = open(path).read().splitlines()
    i0 = lines.index('BEGIN faces') + 1
    i1 = lines.index('END faces')
    # the map: one line of NROW values per ILAY (comment lines '# ILAY n' are kept)
    rows = [k for k in range(i0, i1) if lines[k].strip() and not lines[k].strip().startswith('#')
            and lines[k].split()[0].upper() not in ('FACES', 'INTERNAL')]
    fmap = [[int(t) for t in lines[k].split()] for k in rows]
    faces = [(ir + 1, il + 1) for il, row in enumerate(fmap) for ir, v in enumerate(row) if v > 0]   # (x, y) = (irow, ilay)
    if not faces:
        raise SystemExit('the FACES map has no faces')
    x0, y0 = min(f[0] for f in faces), min(f[1] for f in faces)

    def is_hole(x, y):
        dx, dy = x - x0 - a.offset, y - y0 - a.offset
        return dx >= 0 and dy >= 0 and dx % a.pitch < a.size and dy % a.pitch < a.size

    nh = nc = 0
    for x, y in faces:
        if is_hole(x, y):
            fmap[y - 1][x - 1] = 2
            nh += 1
        elif a.closed:
            fmap[y - 1][x - 1] = 3
            nc += 1
        else:
            fmap[y - 1][x - 1] = 1
    for k, row in zip(rows, fmap):
        lines[k] = '    ' + ' '.join(str(v) for v in row)
    open(path, 'w').write('\n'.join(lines) + '\n')
    nam = [f for f in os.listdir(a.out_dir) if f.endswith('.nam')][0]
    print(f'{len(faces)} faces: {nh} holes, {nc} closed, {len(faces) - nh - nc} membrane -> {os.path.join(a.out_dir, nam)}')
    xs = sorted({f[0] for f in faces})
    ys = sorted({f[1] for f in faces})
    for y in ys:
        print('  ' + ''.join('0' if is_hole(x, y) else ('#' if a.closed else '-') for x in xs))


if __name__ == '__main__':
    main()
