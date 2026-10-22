#!/usr/bin/env python3
"""Extract a memdif3d text input set from the spreadsheet model (stdlib only).

The sheet holds the model as two stacked blocks: rows b0.. = state at time t (numbers),
rows b1.. = state at t+1 (formulas). The geometry, boundary rules and parameters are derived
from those formulas, not typed in. See ../docs/INPUT_SPEC.md for the file formats.

    python3 xlsx2memdif.py Reduced_Matrix.xlsx ../data/reduced_matrix
"""
import argparse, collections, os, re, sys, zipfile
from xml.etree import ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
A1 = re.compile(r'(\$?)([A-Z]{1,3})(\$?)(\d+)')


def c2n(c):
    n = 0
    for ch in c:
        n = n * 26 + ord(ch) - 64
    return n


def n2c(n):
    s = ''
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def split_addr(a):
    m = re.match(r'([A-Z]+)(\d+)$', a)
    return c2n(m.group(1)), int(m.group(2))


def shift(f, dr, dc):
    def rep(m):
        ca, col, ra, row = m.groups()
        c, r = c2n(col), int(row)
        if not ca:
            c += dc
        if not ra:
            r += dr
        return f"{ca}{n2c(c)}{ra}{r}"
    return A1.sub(rep, f)


def rel(addr, f):
    cc, cr = split_addr(addr)

    def rep(m):
        ca, col, ra, row = m.groups()
        c, r = c2n(col), int(row)
        return (f"R{r}" if ra else f"R[{r - cr}]") + (f"C{c}" if ca else f"C[{c - cc}]")
    return A1.sub(rep, f)


def load_sheet(path):
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    vals, forms, masters = {}, {}, {}
    for row in root.find(NS + 'sheetData'):
        for c in row:
            a = c.get('r')
            v, f = c.find(NS + 'v'), c.find(NS + 'f')
            if v is not None and c.get('t') in (None, 'n'):
                vals[a] = float(v.text)
            if f is None:
                continue
            if f.get('t') == 'shared':
                si = f.get('si')
                if f.text:
                    masters[si] = (a, f.text)
                    forms[a] = f.text
                else:
                    ma, mt = masters[si]
                    (mc, mr), (cc, cr) = split_addr(ma), split_addr(a)
                    forms[a] = shift(mt, cr - mr, cc - mc)
            else:
                forms[a] = f.text
    return vals, forms


GHOST = re.compile(r'^R\[(-?\d+)\]C\[(-?\d+)\]\*([0-9.]+)$')
NBR = re.compile(r'(?:\(R1C(\d+)/R1C(\d+)\)|R1C(\d+)/R1C(\d+))\*\(R\[(-?\d+)\]C\[(-?\d+)\]-R\[(-?\d+)\]C\[0\]\)')
ADV = re.compile(r'R1C(\d+)\*R\[(-?\d+)\]C\[(-?\d+)\]')
SUMT = re.compile(r'([+-]?)SUM\(R\[(-?\d+)\]C\[(-?\d+)\]:R\[(-?\d+)\]C\[(-?\d+)\]\)')
PARAM_D = re.compile(r'^([A-Z]+\d+)\*([A-Z]+\d+)/([A-Z]+\d+)/([A-Z]+\d+)(?:\*1)?$')      # D*phi/l/tau
PARAM_R = re.compile(r'^([A-Z]+\d+)\+([A-Z]+\d+)\*([A-Z]+\d+)$')                         # phi+rho*Kd


def die(msg):
    sys.exit('xlsx2memdif: ' + msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('xlsx')
    ap.add_argument('outdir')
    ap.add_argument('--block0-row', type=int, default=6, help='first row of the state block at time t')
    ap.add_argument('--block1-row', type=int, default=50, help='first row of the block at t+1')
    ap.add_argument('--nrows', type=int, default=43, help='rows per block (X)')
    ap.add_argument('--days', type=int, default=28)
    ap.add_argument('--steps-per-day', type=int, default=1440)
    ap.add_argument('--title', default=None)
    args = ap.parse_args()

    vals, forms = load_sheet(args.xlsx)
    b0, b1, NX = args.block0_row, args.block1_row, args.nrows
    P = b1 - b0

    # ---- tiles (slices): contiguous runs of cells in an ordinary row of block 1
    probe = b1 + 1
    colset = {c2n(re.match(r'[A-Z]+', a).group(0)) for a in vals if split_addr(a)[1] == probe}
    runs, start = [], None
    for c in range(1, max(colset) + 2):
        if c in colset:
            start = c if start is None else start
        elif start is not None:
            runs.append((start, c - 1))
            start = None
    NZ = runs[0][1] - runs[0][0] + 1
    if any(e - s + 1 != NZ for s, e in runs):
        die('tiles have different widths')
    NY = len(runs)
    tile_of_col = {}
    for iy, (s, e) in enumerate(runs, 1):
        for k in range(NZ):
            tile_of_col[s + k] = (iy, k + 1)
    start_col = {iy: s for iy, (s, e) in enumerate(runs, 1)}
    print(f'grid: NX={NX} NY={NY} NZ={NZ}')

    def addr(row, col):
        return n2c(col) + str(row)

    # ---- classify block-1 cells
    ghost_copy, ghost_cell_forms, stencil = {}, {}, {}
    refd = set()
    all_pos = [(x, iy, iz) for x in range(1, NX + 1) for iy in range(1, NY + 1) for iz in range(1, NZ + 1)]

    def target_of(row, col, dr, dc, block_first):
        r, c = row + dr, col + dc
        x = r - block_first + 1
        if c in tile_of_col:
            return (x,) + tile_of_col[c]
        for iy, s in start_col.items():            # column left of a tile start = source column
            if c == s - 1:
                return 'M'
        die(f'reference to column {n2c(c)} outside every tile')

    for (x, iy, iz) in all_pos:
        col = runs[iy - 1][0] + iz - 1
        row = b1 + x - 1
        a = addr(row, col)
        f = forms.get(a)
        if f is None:
            continue
        r = rel(a, f)
        g = GHOST.match(r)
        if g:
            dr, dc, fac = int(g.group(1)), int(g.group(2)), float(g.group(3))
            ghost_copy[(x, iy, iz)] = (target_of(row, col, dr, dc, b1), fac)
            continue
        # fluid cell
        rest = r
        nbs, kinds = [], []
        for m in NBR.finditer(r):
            ccol = int(m.group(1) or m.group(3))
            dr, dc, selfdr = int(m.group(5)), int(m.group(6)), int(m.group(7))
            if selfdr != -P:
                die(f'{a}: neighbour term does not reference the t block')
            nbs.append((ccol, target_of(row, col, dr, dc, b0)))
        rest = NBR.sub('', rest)
        adv = None
        for m in ADV.finditer(rest):
            if int(m.group(2)) == -P + 1 and int(m.group(3)) == 0 and rest[m.start() - 1:m.start()] != '-':
                adv = int(m.group(1))
        rest = ADV.sub('', rest)
        rest = re.sub(r'R\[-%d\]C\[0\]' % P, '', rest)
        rest = re.sub(r'R1C\d+', '', rest)
        if re.sub(r'[+\-*/() ]', '', rest):
            die(f'{a}: unparsed formula part {rest!r}')
        stencil[(x, iy, iz)] = (nbs, adv)
        for _, t in nbs:
            if t != 'M':
                refd.add(t)

    # ---- source cell (column left of tiles, formula with SUM)
    src = None
    for a, f in forms.items():
        c, r = split_addr(a)
        if c not in tile_of_col and 'SUM(' in f:
            src = (a, f)
    if not src:
        die('no source-cell formula with SUM found')
    sa, sf = src
    sc, sr = split_addr(sa)
    sr_rel = rel(sa, sf)
    faces = set()
    pos_cols = []
    pairs = []
    for m in SUMT.finditer(sr_rel):
        sign, r1, c1, r2, c2 = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
        xs = range(sr + r1 - b0 + 1, sr + r2 - b0 + 1 + 1)
        pairs.append((sign != '-', sc + c1, xs))
    for k in range(0, len(pairs), 2):
        (p1, pc, xs), (p2, nc, xs2) = pairs[k], pairs[k + 1]
        if not p1 or p2 or nc != pc + 1 or list(xs) != list(xs2):
            die('unexpected SUM pattern in source formula')
        iy, iz = tile_of_col[nc]
        if iz != 1:
            die('source face is not in the first column of a tile')
        for x in xs:
            faces.add((x, iy))
    kcol = int(re.search(r'R1C(\d+)\*\(SUM', sr_rel).group(1))
    vcol = int(re.search(r'\)/R1C(\d+)$', sr_rel).group(1)) if re.search(r'\)/R1C(\d+)$', sr_rel) else None
    if vcol is None:
        m = re.findall(r'R1C(\d+)', sr_rel)
        vcol = int(m[-1])
    print(f'source faces: {len(faces)}  (X {min(x for x,_ in faces)}..{max(x for x,_ in faces)}, '
          f'IY {min(y for _,y in faces)}..{max(y for _,y in faces)})')

    # ---- parameters
    coefcols = collections.Counter(c for nbs, _ in stencil.values() for c, _ in nbs)
    ks_col = [c for c, _ in coefcols.most_common() if c != kcol][0]
    adv_cols = {a for _, a in stencil.values() if a}
    if len(adv_cols) > 1:
        die('more than one advection parameter cell')
    vel_col = adv_cols.pop() if adv_cols else None
    # retardation column: from the first fluid formula
    some = next(iter(stencil))
    sx, siy, siz = some
    sform = rel(addr(b1 + sx - 1, runs[siy - 1][0] + siz - 1), forms[addr(b1 + sx - 1, runs[siy - 1][0] + siz - 1)])
    rcol = int(NBR.search(sform).group(2) or NBR.search(sform).group(4))

    def pcell(c):
        return n2c(c) + '1'

    def pval(c):
        return vals[pcell(c)]

    def dsp(c):
        m = PARAM_D.match(forms[pcell(c)])
        if not m:
            die(f'cannot read diffusion parameters from {pcell(c)} = {forms[pcell(c)]}')
        D, phi, l, tau = (vals[g] for g in m.groups())
        return D, tau, phi, l

    sand = dsp(ks_col)
    memb = dsp(kcol)
    m = PARAM_R.match(forms[pcell(rcol)])
    if not m:
        die('cannot read retardation formula')
    phi_r, rho, kd = (vals[g] for g in m.groups())
    V = pval(vcol)
    v = pval(vel_col) if vel_col else 0.0
    ks_calc = sand[0] * sand[2] / sand[3] / sand[1]
    km_calc = memb[0] * memb[2] / memb[3] / memb[1]
    r_calc = phi_r + rho * kd
    for name, calc, cell in (('Ks', ks_calc, ks_col), ('Km', km_calc, kcol), ('R', r_calc, rcol)):
        if abs(calc - pval(cell)) > 1e-12 * max(1, abs(calc)):
            die(f'{name} recomputed {calc} differs from sheet value {pval(cell)}')
    print(f'parameters: Ks={ks_calc:.6g} Km={km_calc:.6g} R={r_calc:.6g} V={V:g} v={v:g}')

    # ---- initial state
    def c0(x, iy, iz):
        return vals.get(addr(b0 + x - 1, runs[iy - 1][0] + iz - 1), 0.0)

    mvals = {vals.get(addr(b0 + x - 1, start_col[iy] - 1)) for (x, iy) in faces}
    if len(mvals) != 1 or None in mvals:
        die(f'source cells do not hold one common value: {mvals}')
    cm0 = mvals.pop()

    # ---- domain codes
    idomain = {}
    fixed = {}
    for pos in all_pos:
        x, iy, iz = pos
        if pos in stencil:
            idomain[pos] = 1
        elif pos in ghost_copy:
            idomain[pos] = 2
        else:
            a = addr(b1 + x - 1, runs[iy - 1][0] + iz - 1)
            val = vals.get(a, 0.0)
            if pos in refd:
                idomain[pos] = 2
                fixed[pos] = val
            else:
                if val != 0:
                    print(f'warning: solid cell {pos} holds {val}')
                idomain[pos] = 0

    # ---- default neighbours vs. sheet neighbours
    dirs = {'+X': (1, 0, 0), '-X': (-1, 0, 0), '+Y': (0, 1, 0), '-Y': (0, -1, 0), '+Z': (0, 0, 1), '-Z': (0, 0, -1)}

    def default_nb(pos):
        x, iy, iz = pos
        out = {}
        for d, (dx, dy, dz) in dirs.items():
            if d == '-Z' and iz == 1 and (x, iy) in faces:
                out[d] = 'M'
                continue
            t = (x + dx, iy + dy, iz + dz)
            if t in idomain and idomain[t] != 0:
                out[d] = t
        return out

    def direction(pos, t):
        x, iy, iz = pos
        if t == 'M':
            return '-Z'
        dx = t[0] - x
        if dx:
            return '+X' if dx > 0 else '-X'
        # same row: use column offset sign
        ca = runs[iy - 1][0] + iz - 1
        ct = runs[t[1] - 1][0] + t[2] - 1
        d = ct - ca
        if abs(d) == 1 and t[1] == iy:
            return '+Z' if d > 0 else '-Z'
        return '+Y' if d > 0 else '-Y'

    overrides = []
    advmask = {}
    for pos, (nbs, adv) in stencil.items():
        sheet = {}
        for ccol, t in nbs:
            d = direction(pos, t)
            want_km = (t == 'M')
            if (ccol == kcol) != want_km:
                die(f'{pos}: coefficient/neighbour kind mismatch toward {d}')
            sheet[d] = t
        default = default_nb(pos)
        for d in dirs:
            if d in default and d not in sheet:
                overrides.append((pos, d, 'OMIT', None))
            elif d in sheet and sheet[d] != default.get(d):
                overrides.append((pos, d, 'SET', sheet[d]))
        advmask[pos] = 1 if adv else 0
        if adv and adv != vel_col:
            die('advection coefficient differs between cells')

    # ---- ghost order (copy sources must be evaluated first)
    order, done, pending = [], set(), dict(ghost_copy)
    while pending:
        ready = [p for p, (t, _) in pending.items() if p not in done and (t not in pending)]
        if not ready:
            die('circular ghost-cell dependencies')
        for p in sorted(ready, key=lambda q: (q[1], q[0], q[2])):
            order.append(p)
            pending.pop(p)

    # ---- write
    os.makedirs(args.outdir, exist_ok=True)

    def w(name, text):
        with open(os.path.join(args.outdir, name), 'w') as fh:
            fh.write(text)

    title = args.title or f'{os.path.basename(args.xlsx)}'
    hdr = f'# memdif3d input written by xlsx2memdif.py from {os.path.basename(args.xlsx)}\n'

    w('memdif3d.nam', hdr + f'''BEGIN options
  TITLE {title}
END options

BEGIN packages
  TDIS  memdif3d.tdis
  DIS   memdif3d.dis
  IC    memdif3d.ic
  DSP   memdif3d.dsp
  MST   memdif3d.mst
  SRC   memdif3d.src
  ADV   memdif3d.adv
  BND   memdif3d.bnd
  OC    memdif3d.oc
END packages
''')
    w('memdif3d.tdis', hdr + f'''BEGIN options
  TIME_UNITS minutes
END options

BEGIN timing
  STEP_LENGTH {1.0}
  STEPS_PER_PERIOD {args.steps_per_day}
  NPERIODS {args.days}
END timing
''')

    def array(name, getter, fmt):
        lines = [f'  {name}', '    INTERNAL']
        for iy in range(1, NY + 1):
            lines.append(f'    # IY {iy}  (rows IX 1..{NX}, columns IZ 1..{NZ})')
            for x in range(1, NX + 1):
                lines.append('    ' + ' '.join(fmt(getter((x, iy, iz))) for iz in range(1, NZ + 1)))
        return '\n'.join(lines) + '\n'

    w('memdif3d.dis', hdr + f'''# IDOMAIN: 1 fluid cell, 0 solid (never used), 2 ghost cell (see BND)
# Array order: IZ fastest, then IX, then IY. IZ = 1 touches the membrane.
BEGIN dimensions
  NX {NX}
  NY {NY}
  NZ {NZ}
END dimensions

BEGIN griddata
{array('IDOMAIN', lambda p: idomain[p], str)}END griddata
''')
    w('memdif3d.ic', hdr + f'''BEGIN griddata
{array('STRT', lambda p: c0(*p), repr)}END griddata
''')
    w('memdif3d.dsp', hdr + f'''# Mass-transfer coefficient K = D * porosity / length / tortuosity
BEGIN sand
  DIFFUSION {sand[0]!r}
  TORTUOSITY {sand[1]!r}
  POROSITY {sand[2]!r}
  LENGTH {sand[3]!r}
END sand

BEGIN membrane
  DIFFUSION {memb[0]!r}
  TORTUOSITY {memb[1]!r}
  POROSITY {memb[2]!r}
  LENGTH {memb[3]!r}
END membrane
''')
    w('memdif3d.mst', hdr + f'''# Retardation R = POROSITY + BULK_DENSITY * KD
BEGIN options
  POROSITY {phi_r!r}
  BULK_DENSITY {rho!r}
  KD {kd!r}
END options
''')
    fl = '\n'.join(f'  {x} {iy}' for (x, iy) in sorted(faces, key=lambda q: (q[1], q[0])))
    w('memdif3d.src', hdr + f'''# One fully mixed source cell. Its faces touch IZ = 1 of the listed (IX, IY) columns.
BEGIN source
  VOLUME {V!r}
  START_CONC {cm0!r}
END source

BEGIN faces
{fl}
END faces
''')
    w('memdif3d.adv', hdr + f'''# Upwind term VELOCITY * (C(IX+1) - C) where ADVMASK = 1. VELOCITY is per time step.
BEGIN options
  VELOCITY {v!r}
END options

BEGIN griddata
{array('ADVMASK', lambda p: advmask.get(p, 0), str)}END griddata
''')

    gl = []
    for p in sorted(fixed, key=lambda q: (q[1], q[0], q[2])):     # constants first: COPY lines may read them
        gl.append(f'  {p[0]} {p[1]} {p[2]} FIXED {fixed[p]!r}')
    for p in order:
        t, fac = ghost_copy[p]
        gl.append(f'  {p[0]} {p[1]} {p[2]} COPY {t[0]} {t[1]} {t[2]} {fac!r}')
    ol = []
    for pos, d, kind, t in sorted(overrides, key=lambda q: (q[0][1], q[0][0], q[0][2], q[1])):
        if kind == 'OMIT':
            ol.append(f'  {pos[0]} {pos[1]} {pos[2]} {d} OMIT')
        elif t == 'M':
            ol.append(f'  {pos[0]} {pos[1]} {pos[2]} {d} SOURCE')
        else:
            ol.append(f'  {pos[0]} {pos[1]} {pos[2]} {d} SET {t[0]} {t[1]} {t[2]}')
    w('memdif3d.bnd', hdr + f'''# Ghost cells (IDOMAIN = 2), evaluated in file order after the fluid cells and the source.
#   COPY  = factor * new value of the cell (sx sy sz)      FIXED = constant
# Neighbour overrides replace the default neighbour of a fluid cell in one direction.
#   default: the 6 face neighbours that are not solid; IZ = 1 under a source face looks at the source.
BEGIN ghosts
{chr(10).join(gl)}
END ghosts

BEGIN neighbor_overrides
{chr(10).join(ol)}
END neighbor_overrides
''')
    fx = sorted(x for x, _ in faces)
    fy = sorted(y for _, y in faces)
    cx, cy = fx[len(fx) // 2], fy[len(fy) // 2]
    w('memdif3d.oc', hdr + f'''# {{period}} in a file name is replaced by the period (day) number.
BEGIN options
  DAILY_FIELD   FILEOUT field_{{period}}.csv
  PROBES        FILEOUT probes_{{period}}.csv
  RESTART       FILEOUT restart.dat
END options

# written every time step: the source cell, then cells at the middle of the source footprint
BEGIN probes
  SOURCE
  {cx} {cy} 1
  {cx} {cy} 6
END probes
''')
    nfix, ncopy = len(fixed), len(ghost_copy)
    print(f'cells: fluid={sum(1 for v in idomain.values() if v==1)} ghost={nfix+ncopy} '
          f'(copy {ncopy}, fixed {nfix}) solid={sum(1 for v in idomain.values() if v==0)}')
    print(f'neighbor overrides: {len(overrides)}  advection cells: {sum(advmask.values())}')
    print(f'wrote 9 files to {args.outdir}')


if __name__ == '__main__':
    main()
