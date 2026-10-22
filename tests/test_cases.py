#!/usr/bin/env python3
"""Tests on synthetic geometry that differs from the Reduced_Matrix case.

  python3 test_cases.py <memdif3d executable>

open    off-centre 5x3 source, other grid size, mixed ghost rules, sorption, advection, neighbour
        overrides, 2 min step: Fortran field and probes must match the Python prototype (1e-12).
closed  sealed box without ghost cells: V*CM + R*sum(c) must stay constant, and the long-time
        concentration must be uniform and equal to the analytic value V*CM0 / (V + R*Nfluid).
unstable  a diffusion coefficient far too large must be refused (and run with --force).
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import make_test_case as G  # noqa: E402
import memdif_proto as P  # noqa: E402

exe = os.path.abspath(sys.argv[1])


def fail(msg):
    sys.exit('FAIL: ' + msg)


def make(case, d, diffusion=None):
    files, info = G.build(case, diffusion)
    for n, t in files.items():
        G.write(os.path.join(d, n), t)
    return os.path.join(d, 't.nam'), info


def run(nam, cwd, *extra, check=True):
    r = subprocess.run([exe, nam, *extra], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        fail(f'memdif3d failed ({r.returncode}):\n{r.stdout}\n{r.stderr}')
    return r


def field(path):
    cm, vals = None, []
    for line in open(path):
        if line.startswith('#'):
            m = re.search(r'CM\s+(\S+)', line)
            if m:
                cm = float(m.group(1))
            continue
        if line.strip():
            vals.extend(float(t) for t in line.split(','))
    return cm, vals


def probes(path):
    rows = [l.strip().split(',') for l in open(path)]
    return [[float(t) for t in r] for r in rows[1:]]


with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as r1:
    # ---------------- open case against the prototype
    nam, info = make('open', d1)
    run(nam, r1)
    m = P.Model(nam)
    C, CM = dict(m.c0), m.cm0
    nper, spp = 3, 15
    ser = []
    cells = [(8, 5, 1), (8, 5, 5)]
    for _ in range(nper * spp):
        C, CM = m.step(C, CM)
        ser.append([CM] + [C[p] for p in cells])
    cmf, vals = field(os.path.join(r1, f'field_{nper:03d}.csv'))
    order = [(x, iy, iz) for iy in range(1, m.ny + 1) for x in range(1, m.nx + 1) for iz in range(1, m.nz + 1)]
    worst = max(abs(a - C[p]) for a, p in zip(vals, order))
    print(f'open: {m.nx}x{m.ny}x{m.nz}, fluid {len(m.fluid)}, field vs prototype {worst:.2e}, CM diff {abs(cmf - CM):.2e}')
    if len(vals) != len(order) or worst > 1e-12 or abs(cmf - CM) > 1e-12:
        fail('open case differs from the prototype')
    pr = probes(os.path.join(r1, f'probes_{nper:03d}.csv'))
    off = (nper - 1) * spp
    pw = max(abs(row[2 + j] - ser[off + i][j]) for i, row in enumerate(pr) for j in range(3))
    print(f'open: probes vs prototype {pw:.2e}')
    if len(pr) != spp or pw > 1e-12:
        fail('open case probes differ from the prototype')

with tempfile.TemporaryDirectory() as d2, tempfile.TemporaryDirectory() as r2:
    # ---------------- closed box: conservation and the analytic end state
    nam, info = make('closed', d2)
    run(nam, r2)
    m = P.Model(nam)
    fluid = [k for k, p in enumerate((x, iy, iz) for iy in range(1, m.ny + 1) for x in range(1, m.nx + 1)
                                    for iz in range(1, m.nz + 1)) if m.idom[p] == 1]
    R = info['retardation']
    mass0 = info['vol'] * info['cm0']
    drift = 0.0
    for period in range(1, 21):
        cm, vals = field(os.path.join(r2, f'field_{period:03d}.csv'))
        mass = info['vol'] * cm + R * sum(vals[k] for k in fluid)
        drift = max(drift, abs(mass - mass0) / mass0)
    ceq = info['vol'] * info['cm0'] / (info['vol'] + R * info['nfluid'])
    spread = max(abs(vals[k] - ceq) for k in fluid)
    print(f'closed: max relative mass drift {drift:.2e}; end state {ceq:.6f}, largest deviation {max(spread, abs(cm - ceq)):.2e}')
    if drift > 1e-12:
        fail('mass is not conserved in the sealed box')
    if max(spread, abs(cm - ceq)) > 1e-6:
        fail('closed box did not reach the analytic uniform concentration')

with tempfile.TemporaryDirectory() as d3, tempfile.TemporaryDirectory() as r3:
    # ---------------- stability guard
    nam, _ = make('open', d3, diffusion=5.0)
    r = run(nam, r3, check=False)
    if r.returncode == 0 or 'unstable' not in r.stdout:
        fail('an unstable setup must be refused:\n' + r.stdout)
    r = run(nam, r3, '--force', '--nperiods', '1', '--steps-per-period', '2', check=False)
    if r.returncode != 0 or 'running anyway' not in r.stdout:
        fail('--force must run with a warning:\n' + r.stdout)
    print('unstable: refused, and --force runs with a warning')
print('PASS')
