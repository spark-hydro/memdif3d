#!/usr/bin/env python3
"""Convert a memdif3d input set from the old axis layout (NX NY NZ; arrays IZ fastest, then IX, then IY;
cell ids "ix iy iz") to the MODFLOW layout (NLAY NROW NCOL; arrays ICOL fastest, then IROW, then ILAY;
cell ids "ilay irow icol").

    python3 convert_layout.py OLD_DIR NEW_DIR

Mapping: IX -> IROW, IY -> ICOL, IZ -> ILAY (IZ = 1 touches the membrane, so ILAY = 1 does). Directions
+X -X +Y -Y +Z -Z become +ROW -ROW +COL -COL +LAY -LAY. Values are copied as text, so nothing is rounded.
Face lines ("ix iy" = "irow icol") keep their order. Restart files of old runs cannot be used afterwards.
"""
import os
import re
import shutil
import sys

DIRS = {'+X': '+ROW', '-X': '-ROW', '+Y': '+COL', '-Y': '-COL', '+Z': '+LAY', '-Z': '-LAY'}
COMMENTS = {
    '# Array order: IZ fastest, then IX, then IY. IZ = 1 touches the membrane.':
        '# Array order: ICOL fastest, then IROW, then ILAY (MODFLOW order). ILAY = 1 touches the membrane.',
    '# Upwind term VELOCITY * (C(IX+1) - C) where ADVMASK = 1. VELOCITY is per time step.':
        '# Upwind term VELOCITY * (C(IROW+1) - C) where ADVMASK = 1. VELOCITY is per time step.',
    '#   COPY  = factor * new value of the cell (sx sy sz)      FIXED = constant':
        '#   cell ids are: ilay irow icol.   COPY = factor * new value of the cell (slay srow scol)   FIXED = constant',
    '#   default: the 6 face neighbours that are not solid; IZ = 1 under a source face looks at the source.':
        '#   default: the 6 face neighbours that are not solid; ILAY = 1 under a source face looks at the source.',
    '# One fully mixed source cell. Its faces touch IZ = 1 of the listed (IX, IY) columns.':
        '# One fully mixed source cell. Its faces touch ILAY = 1 of the listed (IROW, ICOL) cells.',
}


def array_block(lines, nx, ny, nz):
    """lines of a griddata block (key line included) -> same block in the new layout"""
    out, vals, key = [], [], None
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith('#'):
            continue
        if key is None:
            key = s
            continue
        if s.upper() == 'INTERNAL':
            continue
        vals.extend(s.split())
    if len(vals) != nx * ny * nz:
        sys.exit(f'array {key}: {len(vals)} values, expected {nx * ny * nz}')
    old = lambda x, y, z: vals[z + nz * (x + nx * y)]            # 0-based, IZ fastest, then IX, then IY   # noqa: E731
    out = [f'  {key}', '    INTERNAL']
    for il in range(nz):
        out.append(f'    # ILAY {il + 1}  (rows IROW 1..{nx}, columns ICOL 1..{ny})')
        for ir in range(nx):
            out.append('    ' + ' '.join(old(ir, ic, il) for ic in range(ny)))
    return out


def convert_arrays(text, dims):
    nx, ny, nz = dims
    lines = text.split('\n')
    out, i = [], 0
    while i < len(lines):
        s = lines[i].strip()
        if re.fullmatch(r'(IDOMAIN|STRT|ADVMASK)', s):
            j = i + 1
            while lines[j].strip() != 'END griddata':
                j += 1
            out.extend(array_block(lines[i:j], nx, ny, nz))
            i = j
            continue
        out.append(lines[i])
        i += 1
    return '\n'.join(out)


def convert_bnd(text):
    out, mode = [], None
    for ln in text.split('\n'):
        s = ln.strip()
        if s.startswith('BEGIN '):
            mode = s.split()[1]
        elif s.startswith('END '):
            mode = None
        elif s and not s.startswith('#') and mode == 'ghosts':
            w = s.split()
            x, y, z = w[:3]
            if w[3].upper() == 'FIXED':
                ln = f'  {z} {x} {y} FIXED {w[4]}'
            else:
                ln = f'  {z} {x} {y} COPY {w[6]} {w[4]} {w[5]} {w[7]}'
        elif s and not s.startswith('#') and mode == 'neighbor_overrides':
            w = s.split()
            x, y, z, d = w[:4]
            ln = f'  {z} {x} {y} {DIRS[d.upper()]} {w[4]}'
            if w[4].upper() == 'SET':
                ln += f' {w[7]} {w[5]} {w[6]}'
        out.append(ln)
    return '\n'.join(out)


def convert_oc(text):
    out, mode = [], None
    for ln in text.split('\n'):
        s = ln.strip()
        if s.startswith('BEGIN '):
            mode = s.split()[1]
        elif s.startswith('END '):
            mode = None
        elif mode == 'probes' and re.fullmatch(r'\d+\s+\d+\s+\d+', s):
            x, y, z = s.split()
            ln = f'  {z} {x} {y}'
        out.append(ln)
    return '\n'.join(out)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    old, new = sys.argv[1:]
    shutil.copytree(old, new, dirs_exist_ok=True)
    files = {os.path.splitext(f)[1]: os.path.join(new, f) for f in os.listdir(new)}
    dis = open(files['.dis']).read()
    m = {k: int(re.search(rf'^\s*{k}\s+(\d+)', dis, re.M).group(1)) for k in ('NX', 'NY', 'NZ')}
    dims = (m['NX'], m['NY'], m['NZ'])
    for ext, path in files.items():
        text = open(path).read()
        if ext in ('.dis', '.ic', '.adv'):
            text = convert_arrays(text, dims)
        if ext == '.dis':
            text = re.sub(r'  NX \d+\n  NY \d+\n  NZ \d+', f'  NLAY {dims[2]}\n  NROW {dims[0]}\n  NCOL {dims[1]}', text)
        if ext == '.bnd':
            text = convert_bnd(text)
        if ext == '.oc':
            text = convert_oc(text)
        text = '\n'.join(COMMENTS.get(l, l) for l in text.split('\n'))
        open(path, 'w').write(text)
    print(f'converted {old} -> {new}: NLAY {dims[2]} NROW {dims[0]} NCOL {dims[1]}')


if __name__ == '__main__':
    main()
