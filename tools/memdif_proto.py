#!/usr/bin/env python3
"""Prototype reader and one-step solver for memdif3d text input (stdlib only).

Reads only the package files, so it checks that they carry the whole model. The Fortran program
should reproduce this logic. Run as a script to compare one step on a random field with
ref_step.py (which was validated against the spreadsheet formulas):

    python3 memdif_proto.py ../data/reduced_matrix/memdif3d.nam
"""
import os
import random
import sys


def read_blocks(path):
    blocks, cur = {}, None
    for line in open(path):
        line = line.split('#')[0].strip()
        if not line:
            continue
        w = line.split()
        if w[0].upper() == 'BEGIN':
            cur = blocks.setdefault(w[1].lower(), [])
        elif w[0].upper() == 'END':
            cur = None
        elif cur is not None:
            cur.append(w)
    return blocks


def scalar(block, key, conv=float):
    for w in block:
        if w[0].upper() == key:
            return conv(w[1])
    raise KeyError(key)


def array(block, name, conv):
    vals, on = [], False
    for w in block:
        if w[0].upper() == name:
            on = True
            continue
        if on:
            if w[0].upper() == 'INTERNAL':
                continue
            vals.extend(conv(t) for t in w)
    return vals


def cell(w):
    """cell id of the files (ilay irow icol) -> tuple (x, y, z) = (row, col, lay)"""
    lay, row, col = (int(t) for t in w)
    return (row, col, lay)


class Model:
    def __init__(self, namefile):
        d = os.path.dirname(namefile)
        pk = {w[0].upper(): os.path.join(d, w[1]) for w in read_blocks(namefile)['packages']}
        dis = read_blocks(pk['DIS'])
        # nlay, nrow, ncol in the files; here x = row, y = col, z = lay (cells are tuples (x, y, z))
        nlay, self.nx, self.ny = (scalar(dis['dimensions'], k, int) for k in ('NLAY', 'NROW', 'NCOL'))
        self.nz = nlay
        flat = array(dis['griddata'], 'IDOMAIN', int)
        ic = array(read_blocks(pk['IC'])['griddata'], 'STRT', float)
        am = array(read_blocks(pk['ADV'])['griddata'], 'ADVMASK', int)
        self.idom, self.c0, self.advmask = {}, {}, {}
        k = 0
        for iz in range(1, self.nz + 1):                     # file order: col fastest, then row, then layer
            for x in range(1, self.nx + 1):
                for iy in range(1, self.ny + 1):
                    p = (x, iy, iz)
                    self.idom[p], self.c0[p], self.advmask[p] = flat[k], ic[k], am[k]
                    k += 1
        dsp = read_blocks(pk['DSP'])
        coef = {}
        for nm in ('sand', 'membrane'):
            b = dsp[nm]
            D, t, ph, l = (scalar(b, key) for key in ('DIFFUSION', 'TORTUOSITY', 'POROSITY', 'LENGTH'))
            coef[nm] = D * ph / l / t
        mst = read_blocks(pk['MST'])['options']
        R = scalar(mst, 'POROSITY') + scalar(mst, 'BULK_DENSITY') * scalar(mst, 'KD')
        self.Km, self.Ks = coef['membrane'], coef['sand']
        self.ks, self.km = coef['sand'] / R, coef['membrane'] / R
        src = read_blocks(pk['SRC'])
        self.V = scalar(src['source'], 'VOLUME')
        self.cm0 = scalar(src['source'], 'START_CONC')
        self.kind = {(int(w[0]), int(w[1])): (w[2].upper() if len(w) > 2 else 'MEMBRANE') for w in src['faces']}
        self.faces = [f for f, k in self.kind.items() if k != 'CLOSED']
        self.v = scalar(read_blocks(pk['ADV'])['options'], 'VELOCITY')
        bnd = read_blocks(pk['BND'])
        self.ghosts = []
        for w in bnd['ghosts']:
            p = cell(w[:3])
            if w[3].upper() == 'COPY':
                self.ghosts.append((p, 'COPY', cell(w[4:7]), float(w[7])))
            else:
                self.ghosts.append((p, 'FIXED', None, float(w[4])))
        self.over = {}
        for w in bnd['neighbor_overrides']:
            p, d = cell(w[:3]), self.DIRS_FILE[w[3].upper()]
            if w[4].upper() == 'OMIT':
                self.over[(p, d)] = None
            elif w[4].upper() == 'SOURCE':
                self.over[(p, d)] = 'M'
            else:
                self.over[(p, d)] = cell(w[5:8])
        self.fset = {f for f, k in self.kind.items() if k == 'MEMBRANE'}
        self.hset = {f for f, k in self.kind.items() if k == 'HOLE'}
        self.fluid = [p for p, c in self.idom.items() if c == 1]

    DIRS_FILE = {'+ROW': '+X', '-ROW': '-X', '+COL': '+Y', '-COL': '-Y', '+LAY': '+Z', '-LAY': '-Z'}
    DIRS = {'+X': (1, 0, 0), '-X': (-1, 0, 0), '+Y': (0, 1, 0), '-Y': (0, -1, 0), '+Z': (0, 0, 1), '-Z': (0, 0, -1)}

    def neighbours(self, p):
        x, iy, iz = p
        out = {}
        for d, (dx, dy, dz) in self.DIRS.items():
            if (p, d) in self.over:
                if self.over[(p, d)] is not None:
                    out[d] = self.over[(p, d)]
                continue
            if d == '-Z' and iz == 1 and (x, iy) in self.kind:
                if (x, iy) in self.fset:
                    out[d] = 'M'
                elif (x, iy) in self.hset:
                    out[d] = 'H'
                continue
            t = (x + dx, iy + dy, iz + dz)
            if self.idom.get(t, 0) != 0:
                out[d] = t
        return out

    def step(self, C, CM):
        N = dict(C)
        for p in self.fluid:
            u = C[p]
            s = u
            for t in self.neighbours(p).values():
                s += self.km * (CM - u) if t == 'M' else self.ks * ((CM if t == 'H' else C[t]) - u)
            if self.advmask[p]:
                s += self.v * (C[(p[0] + 1, p[1], p[2])] - u)
            N[p] = s
        CMn = CM - self.Km / self.V * sum(CM - C[(x, iy, 1)] for (x, iy) in self.faces if (x, iy) in self.fset)
        if self.hset:
            CMn -= self.Ks / self.V * sum(CM - C[(x, iy, 1)] for (x, iy) in self.hset)
        for p, kind, t, val in self.ghosts:
            N[p] = val * N[t] if kind == 'COPY' else val
        return N, CMn


def selftest(namefile):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ref_step as R
    m = Model(namefile)
    random.seed(7)
    C, Cref = {}, {}
    for p, code in m.idom.items():
        if code == 0:
            C[p] = 0.0
        else:
            C[p] = random.random()
            Cref[(p[0], p[1] - 1, p[2] - 1)] = C[p]       # ref_step uses Y 0..28, Z 0..24
    CM = random.random()
    N, CMn = m.step(C, CM)
    Nr, CMr = R.step(Cref, CM)
    worst = 0.0
    for p, code in m.idom.items():
        worst = max(worst, abs(N[p] - (Nr.get((p[0], p[1] - 1, p[2] - 1), 0.0) if code else 0.0)))
    worst = max(worst, abs(CMn - CMr))
    print(f'cells {len(m.idom)}  fluid {len(m.fluid)}  max abs diff vs ref_step: {worst:.3e}')
    # Excel's own first step from the initial state
    N, CMn = m.step(m.c0, m.cm0)
    nz = sum(1 for v in N.values() if v != 0.0)
    print(f'first step from START: CM = {CMn!r}, nonzero cells = {nz}')
    return worst


if __name__ == '__main__':
    sys.exit(0 if selftest(sys.argv[1]) < 1e-12 else 1)
