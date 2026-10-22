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
print('PASS')
