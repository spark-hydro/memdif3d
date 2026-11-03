#!/usr/bin/env python3
"""Smoke test of tools/animate_field.py: face only, side only and both must give GIFs (needs numpy,
matplotlib, Pillow; prints SKIP when they are missing).

  python3 test_animate.py <memdif3d executable> <namefile>
"""
import os
import subprocess
import sys
import tempfile

try:
    import numpy, matplotlib, PIL.Image  # noqa: F401,E401
except ImportError:
    print('SKIP: numpy, matplotlib or Pillow not installed')
    sys.exit(0)

exe, nam = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
script = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'animate_field.py')
from PIL import Image  # noqa: E402

with tempfile.TemporaryDirectory() as d:
    r = subprocess.run([exe, nam, '--nperiods', '3', '--steps-per-period', '10'], cwd=d, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit('FAIL: memdif3d run failed\n' + r.stdout + r.stderr)
    for name, extra, width_ratio in (('both', [], 1), ('face', ['--side', 'off'], 1), ('side', ['--face', 'off', '--log'], 1)):
        out = os.path.join(d, f'{name}.gif')
        r = subprocess.run([sys.executable, script, d, '--nam', nam, '--out', out, '--dpi', '40', *extra],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(out):
            sys.exit(f'FAIL: animate_field.py ({name}) failed\n' + r.stdout + r.stderr)
        n = Image.open(out).n_frames
        print(f'{name}: {n} frames')
        if n != 4:                                 # initial state + 3 periods
            sys.exit(f'FAIL: expected 4 frames, got {n}')
    r = subprocess.run([sys.executable, script, d, '--face', 'off', '--side', 'off', '--out', os.path.join(d, 'x.gif')],
                       capture_output=True, text=True)
    if r.returncode == 0:
        sys.exit('FAIL: both views off must be refused')

# ---- day files (MINUTES output) as animation frames
import glob  # noqa: E402
import re    # noqa: E402
import shutil  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import animate_field as AF  # noqa: E402

with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as md:
    for f in glob.glob(os.path.join(os.path.dirname(nam), '*')):
        shutil.copy(f, md)
    oc = [f for f in os.listdir(md) if f.endswith('.oc')][0]
    txt = open(os.path.join(md, oc)).read()
    txt = re.sub(r'(?i)begin options', 'BEGIN options\n  SNAPSHOT FILEOUT snap_{step}.csv EVERY 10', txt, count=1)
    open(os.path.join(md, oc), 'w').write(txt + '\nBEGIN MINUTES\n  DIGITS 16\nEND MINUTES\n')
    mnam = os.path.join(md, os.path.basename(nam))
    r = subprocess.run([exe, mnam, '--nperiods', '3', '--steps-per-period', '10', '--fresh'], cwd=d, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit('FAIL: memdif3d run (MINUTES) failed\n' + r.stdout + r.stderr)
    days = sorted(glob.glob(os.path.join(d, 'day_*.txt')))
    got = AF.load_frames(days, every=10)
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.csv')))
    ref = [AF.read_field(f) for f in snaps]
    steps = [g[1]['step'] for g in got]
    if steps != [0, 10, 20, 30]:
        sys.exit(f'FAIL: day-file frames at steps {steps}, expected [0, 10, 20, 30]')
    for g, (arr, info) in zip(got[1:], ref):
        if g[1]['step'] != info['step'] or not numpy.array_equal(g[0], arr) or abs(g[1]['cm'] - info['cm']) > 1e-15:
            sys.exit(f"FAIL: day-file frame at step {info['step']} differs from the snapshot file")
    print('day files: frames equal the snapshot files')
    out = os.path.join(d, 'days.gif')
    r = subprocess.run([sys.executable, script, d, '--nam', mnam, '--pattern', 'day_*.txt', '--every', '10', '--out', out, '--dpi', '40'],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out):
        sys.exit('FAIL: animate_field.py with day files failed\n' + r.stdout + r.stderr)
    n = Image.open(out).n_frames
    print(f'day files: {n} frames')
    if n != 4:
        sys.exit(f'FAIL: expected 4 frames from the day files, got {n}')
    # 3D page: a block, a plane, and the refusal of two planes (needs plotly)
    try:
        import plotly  # noqa: F401
    except ImportError:
        print('3D page: SKIP, plotly not installed')
    else:
        s3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'animate_3d.py')
        base = [sys.executable, s3, d, '--nam', mnam, '--pattern', 'day_*.txt', '--every', '10', '--out', os.path.join(d, 'x.html')]
        for extra, grid in (([], None), (['--ilay', '15-29'], '14'), (['--icol', '3'], 'x1x'), (['--irow', '22'], 'x1x')):
            r = subprocess.run(base + extra, capture_output=True, text=True)
            if r.returncode != 0 or '4 frames' not in r.stdout:
                sys.exit(f'FAIL: animate_3d.py {extra} failed\n' + r.stdout + r.stderr)
        r = subprocess.run(base + ['--ilay', '15', '--icol', '3'], capture_output=True, text=True)
        if r.returncode == 0:
            sys.exit('FAIL: two planes at once must be refused')
        print('3D page: block, planes and refusal ok')
    out = os.path.join(d, 'views.gif')
    r = subprocess.run([sys.executable, script, d, '--nam', mnam, '--pattern', 'day_*.txt', '--every', '10', '--ilay', '15',
                        '--icol', '3', '--out', out, '--dpi', '40'], capture_output=True, text=True)
    if r.returncode != 0 or 'face on, side on' not in r.stdout:
        sys.exit('FAIL: --ilay/--icol view options failed\n' + r.stdout + r.stderr)
    r = subprocess.run([sys.executable, script, d, '--nam', mnam, '--pattern', 'day_*.txt', '--ilay', '15', '--irow', '22',
                        '--out', os.path.join(d, 'y.gif')], capture_output=True, text=True)
    if r.returncode == 0:
        sys.exit('FAIL: --ilay with --irow must be refused')
    print('MODFLOW view options ok')
    out = os.path.join(d, 'window.gif')
    r = subprocess.run([sys.executable, script, d, '--nam', mnam, '--pattern', 'day_*.txt', '--every', '10', '--from', '10', '--to', '20',
                        '--out', out, '--dpi', '40'], capture_output=True, text=True)
    if r.returncode != 0 or Image.open(out).n_frames != 2:
        sys.exit('FAIL: --from 10 --to 20 must give the 2 frames of steps 10 and 20\n' + r.stdout + r.stderr)
    r = subprocess.run([sys.executable, script, d, '--nam', mnam, '--pattern', 'day_*.txt', '--from', '5000', '--out', os.path.join(d, 'e.gif')],
                       capture_output=True, text=True)
    if r.returncode == 0:
        sys.exit('FAIL: an empty time window must be refused')
    print('time window ok')
print('PASS')
