#!/usr/bin/env python3
"""Test of the minutes output (MINUTES block of the OC file).

  python3 test_minutes.py <memdif3d executable> <namefile>

The model is copied to a temporary folder and a MINUTES block is added. Then:
1. DIGITS 16: every minute block equals the snapshot file of the same step (--snapshot-every 1), start state included.
2. DIGITS 6: values agree with the 16-digit ones to 5e-6 relative.
3. FROM/TO/LAYERS: only the steps in the window and only the chosen layers are written, split over the periods.
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

exe, nam = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
SPP = 5


def fail(msg):
    sys.exit('FAIL: ' + msg)


def run(cwd, nam_path, *extra):
    r = subprocess.run([exe, nam_path, '--steps-per-period', str(SPP), '--fresh', *extra],
                       cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'memdif3d failed ({r.returncode}):\n{r.stdout}\n{r.stderr}')


def model_copy(dest, block):
    src = os.path.dirname(nam)
    for f in glob.glob(os.path.join(src, '*')):
        if os.path.isfile(f):
            shutil.copy(f, dest)
    oc = [f for f in os.listdir(dest) if f.endswith('.oc')][0]
    with open(os.path.join(dest, oc), 'a') as fh:
        fh.write('\nBEGIN MINUTES\n' + block + 'END MINUTES\n')
    return os.path.join(dest, os.path.basename(nam))


def read_minutes(path):
    """{(step, ilay): list of values}, and the header lines in order"""
    out, heads, cur = {}, [], None
    for line in open(path):
        if line.startswith('#'):
            m = re.match(r'# STEP (\d+) TIME (\S+) ILAY (\d+) NROW (\d+) NCOL (\d+)', line)
            if not m:
                fail('bad header: ' + line)
            cur = (int(m.group(1)), int(m.group(3)))
            heads.append((cur, float(m.group(2)), int(m.group(4)), int(m.group(5))))
            out[cur] = []
        elif line.strip():
            out[cur].extend(float(t) for t in line.split())
    return out, heads


def read_field(path):
    out, cur = {}, None
    for line in open(path):
        if line.startswith('# ILAY'):
            cur = int(line.split()[2])
            out[cur] = []
        elif line.startswith('#') or not line.strip():
            continue
        else:
            out[cur].extend(float(t) for t in line.split(','))
    return out


with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2, tempfile.TemporaryDirectory() as t3:
    # ---- 1 and 2
    n1 = model_copy(t1, '  DIGITS 16\n')
    run(t1, n1, '--nperiods', '2', '--snapshot-every', '1')
    mins = {}
    for p in (1, 2):
        d, _ = read_minutes(os.path.join(t1, f'minutes_{p:03d}.txt'))
        mins.update(d)
    steps = sorted({s for s, _ in mins})
    if steps != list(range(0, 2 * SPP + 1)):
        fail(f'steps in the minutes files: {steps}')
    for s in steps[1:]:
        snap = read_field(os.path.join(t1, f'snap_{s:07d}.csv'))
        for il, vals in snap.items():
            if mins[(s, il)] != vals:
                fail(f'step {s} layer {il} differs from the snapshot')
    print(f'minutes (16 digits) equal the snapshot files for {len(steps) - 1} steps')

    n2 = model_copy(t2, '  DIGITS 6\n')
    run(t2, n2, '--nperiods', '2')
    worst = 0.0
    for p in (1, 2):
        d, _ = read_minutes(os.path.join(t2, f'minutes_{p:03d}.txt'))
        for k, vals in d.items():
            ref = mins[k]
            for a, b in zip(vals, ref):
                worst = max(worst, abs(a - b) / max(abs(b), 1e-300) if b != 0 else abs(a))
    print(f'minutes (6 digits) relative difference {worst:.1e}')
    if worst > 5e-6:
        fail('6-digit values are too far from the full precision values')

    # ---- 3
    n3 = model_copy(t3, '  FROM 3\n  TO 7\n  LAYERS 14-15\n')
    run(t3, n3, '--nperiods', '2')
    d1, h1 = read_minutes(os.path.join(t3, 'minutes_001.txt'))
    d2, h2 = read_minutes(os.path.join(t3, 'minutes_002.txt'))
    got = [h[0] for h in h1 + h2]
    want = [(s, il) for s in range(3, 8) for il in (14, 15)]
    if got != want:
        fail(f'window/layers wrong: {got}')
    if any(h[2] != 43 or h[3] != 25 for h in h1 + h2):
        fail('NROW/NCOL in the header are wrong')
    print('window and layer selection ok')
print('PASS')
