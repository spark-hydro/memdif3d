#!/usr/bin/env python3
"""Regression test for the memdif3d executable.

  python3 test_run.py <memdif3d executable> <namefile>

1. 2 periods x 20 steps: the daily field and the probe file must match the Python prototype
   (tools/memdif_proto.py, which reads the same text input) to 1e-12.
2. Restart: 1 period, then a second run asking for 2 periods must continue from the restart file
   and give a field file identical to the uninterrupted run.
3. A run that is already finished does nothing; --fresh starts again.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import memdif_proto as P  # noqa: E402

exe, nam = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
NP, SPP = 2, 20


def run(cwd, *extra):
    r = subprocess.run([exe, nam, *extra], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'memdif3d failed ({r.returncode}):\n{r.stdout}\n{r.stderr}')
    return r.stdout


def read_field(path):
    vals = []
    for line in open(path):
        if line.startswith('#') or not line.strip():
            continue
        vals.extend(float(t) for t in line.split(','))
    return vals


def read_probes(path):
    rows = [line.strip().split(',') for line in open(path)]
    return rows[0], [[float(t) for t in r] for r in rows[1:]]


def fail(msg):
    sys.exit('FAIL: ' + msg)


with tempfile.TemporaryDirectory() as ta, tempfile.TemporaryDirectory() as tb:
    # ---- 1. against the prototype
    run(ta, '--nperiods', str(NP), '--steps-per-period', str(SPP))
    m = P.Model(nam)
    C, CM = dict(m.c0), m.cm0
    src_series, cell_series = [], []
    ijk = [(22, 15, 1), (22, 15, 6)]
    for _ in range(NP * SPP):
        C, CM = m.step(C, CM)
        src_series.append(CM)
        cell_series.append([C[p] for p in ijk])
    fort = read_field(os.path.join(ta, f'field_{NP:03d}.csv'))
    order = [(x, iy, iz) for iz in range(1, m.nz + 1) for x in range(1, m.nx + 1) for iy in range(1, m.ny + 1)]
    if len(fort) != len(order):
        fail(f'field has {len(fort)} values, expected {len(order)}')
    worst = max(abs(f - C[p]) for f, p in zip(fort, order))
    print(f'field vs prototype after {NP * SPP} steps: max abs diff {worst:.2e}')
    if worst > 1e-12:
        fail('field differs from the prototype')
    head, rows = read_probes(os.path.join(ta, 'probes_001.csv'))
    if len(rows) != SPP or head[2] != 'SOURCE':
        fail('probe file has the wrong shape')
    pw = max(max(abs(r[2] - src_series[i]), abs(r[3] - cell_series[i][0]), abs(r[4] - cell_series[i][1]))
             for i, r in enumerate(rows))
    print(f'probes vs prototype (period 1): max abs diff {pw:.2e}')
    if pw > 1e-12:
        fail('probes differ from the prototype')

    # ---- 2. restart
    out = run(tb, '--nperiods', '1', '--steps-per-period', str(SPP))
    out = run(tb, '--nperiods', str(NP), '--steps-per-period', str(SPP))
    if 'restart: continuing after period 1' not in out:
        fail('second run did not continue from the restart file:\n' + out)
    same = open(os.path.join(ta, f'field_{NP:03d}.csv')).read() == open(os.path.join(tb, f'field_{NP:03d}.csv')).read()
    print('resumed run identical to continuous run:', same)
    if not same:
        fail('restarted run differs from the uninterrupted run')

    # ---- 3. finished run, --fresh
    out = run(tb, '--nperiods', str(NP), '--steps-per-period', str(SPP))
    if 'nothing to do' not in out:
        fail('a finished run should do nothing')
    out = run(tb, '--nperiods', str(NP), '--steps-per-period', str(SPP), '--fresh')
    if 'restart: continuing' in out:
        fail('--fresh must ignore the restart files')
    if open(os.path.join(ta, f'field_{NP:03d}.csv')).read() != open(os.path.join(tb, f'field_{NP:03d}.csv')).read():
        fail('fresh rerun differs from the first run')
print('PASS')
