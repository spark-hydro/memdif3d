#!/usr/bin/env python3
"""Test of tools/make_viewer.py (the interactive HTML viewer): the data in the page must equal the result files.

  python3 test_viewer.py <memdif3d executable> <namefile>

Runs 3 periods of 10 steps with snapshots every 10 steps and the minutes output, then builds the viewer from
the field files, from the day files with a time window, and for the domain only. The concentrations stored in
the page (16-bit numbers on a log scale) are decoded and compared with the files (relative error 3e-4).
Prints SKIP when numpy or plotly are missing.
"""
import base64
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zlib

try:
    import numpy as np
    import plotly  # noqa: F401
except ImportError:
    print('SKIP: numpy or plotly not installed')
    sys.exit(0)

exe, nam = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
tools = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools')
sys.path.insert(0, tools)
import animate_field as AF  # noqa: E402


def fail(msg):
    sys.exit('FAIL: ' + msg)


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        fail(' '.join(cmd[:3]) + ' failed\n' + r.stdout + r.stderr)
    return r.stdout


def read_page(path):
    """-> (meta dict, idomain array, concentrations [frame, cell]) decoded from the page like the browser does"""
    txt = open(path, encoding='utf-8').read()
    meta = json.loads(re.search(r'<script type="application/json" id="meta">(.*?)</script>', txt, re.S).group(1))
    n = meta['nlay'] * meta['nrow'] * meta['ncol']
    idom = np.frombuffer(zlib.decompress(base64.b64decode(meta['idom'])), np.uint8)
    q = np.frombuffer(zlib.decompress(base64.b64decode(meta['frames'])), '<u2').reshape(meta['nf'], n)
    v = np.where(q == 0, 0.0, 10.0 ** (meta['lo'] + (q.astype(float) - 1) / 65534 * (meta['hi'] - meta['lo'])))
    return meta, idom, v, txt


def check(page_frames, files, label, first=0):
    """page_frames = (meta, idom, v); compare frames first.. with the (array, info) pairs read from the files"""
    meta, idom, v = page_frames
    fluid = idom == 1
    if meta['nf'] - first != len(files):
        fail(f'{label}: {meta["nf"] - first} frames in the page, expected {len(files)}')
    floor = meta['vmax'] * 1e-7
    worst = 0.0
    for k, (arr, info) in enumerate(files):
        i = first + k
        ref, got = arr.ravel()[fluid], v[i][fluid]
        big = ref > floor * 10
        err = np.abs(got[big] - ref[big]) / ref[big]
        worst = max(worst, float(err.max()))
        if err.max() > 3e-4:
            fail(f'{label}: frame {i} relative error {err.max():.1e}')
        if np.any(got[~big] > floor * 10):
            fail(f'{label}: frame {i} has values where the file has none')
        if abs(meta['cm'][i] - info['cm']) > 1e-12 or abs(meta['minutes'][i] - info['minutes']) > 1e-9:
            fail(f'{label}: frame {i} time or source value differs')
    print(f'{label}: {len(files)} frames equal the files (largest relative error {worst:.1e})')


with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as md:
    for f in glob.glob(os.path.join(os.path.dirname(nam), '*')):
        shutil.copy(f, md)
    oc = [f for f in os.listdir(md) if f.endswith('.oc')][0]
    txt = open(os.path.join(md, oc)).read()
    txt = re.sub(r'(?i)begin options', 'BEGIN options\n  SNAPSHOT FILEOUT snap_{step}.csv EVERY 10', txt, count=1)
    open(os.path.join(md, oc), 'w').write(txt + '\nBEGIN MINUTES\n  DIGITS 16\nEND MINUTES\n')
    mnam = os.path.join(md, os.path.basename(nam))
    run([exe, mnam, '--nperiods', '3', '--steps-per-period', '10', '--fresh'], d)
    script = os.path.join(tools, 'make_viewer.py')
    out = os.path.join(d, 'v.html')

    # field files: the start state comes first, then one frame per day
    run([sys.executable, script, d, '--nam', mnam, '--out', out], d)
    meta, idom, v, _ = read_page(out)
    if meta['minutes'][0] != 0 or meta['nf'] != 4:
        fail('the start state must be the first of 4 frames')
    fields = [AF.read_field(f) for f in sorted(glob.glob(os.path.join(d, 'field_*.csv')))]
    check((meta, idom, v), fields, 'field files', first=1)

    # probes: the series of the probe files (start state first), dots at the frames
    pr = meta['probes']
    if pr is None or pr['names'] != ['SOURCE', '15_22_1', '15_22_6'] or pr['loc'][0] is not None or pr['loc'][1] != [15, 22, 1]:
        fail('the probes of the page are not those of the probe files')
    pt = np.frombuffer(zlib.decompress(base64.b64decode(pr['t'])), '<f4')
    pv = np.frombuffer(zlib.decompress(base64.b64decode(pr['v'])), '<f4').reshape(pr['n'], 3)
    rows = []
    for f in sorted(glob.glob(os.path.join(d, 'probes_*.csv'))):
        rows += [[float(x) for x in line.split(',')] for line in open(f).read().strip().splitlines()[1:]]
    rows = np.array(rows)
    if pr['n'] != len(rows) + 1 or pt[0] != 0 or abs(pv[0, 0] - meta['cm'][0]) > 1e-6:
        fail('the probe series must be the start state plus every minute of the files')
    if np.abs(pt[1:] - rows[:, 1]).max() > 1e-3 or np.abs(pv[1:] - rows[:, 2:]).max() > 1e-6:
        fail('the probe values of the page differ from the probe files')
    print(f'probes: {pr["n"]} points x 3 probes equal the probe files')
    # a page without probes
    run([sys.executable, script, d, '--nam', mnam, '--no-probes', '--out', out], d)
    if read_page(out)[0]['probes'] is not None:
        fail('--no-probes must leave the probes out')

    # day files with a time window (steps 10, 20, 30 equal the snapshot files)
    run([sys.executable, script, d, '--nam', mnam, '--pattern', 'day_*.txt', '--every', '10', '--from', '10', '--to', '30', '--out', out], d)
    meta, idom, v, _ = read_page(out)
    snaps = [AF.read_field(f) for f in sorted(glob.glob(os.path.join(d, 'snap_*.csv')))]
    check((meta, idom, v), snaps, 'day files, window 10 to 30')

    # the domain only
    run([sys.executable, script, '--nam', mnam, '--out', out], d)
    meta, idom, v, html = read_page(out)
    if meta['nf'] != 1 or meta['minutes'] != [0.0]:
        fail('a domain-only page must hold the start state only')
    for needle in ('id="ptype"', 'id="tsl"', 'Plotly.newPlot', 'DecompressionStream'):
        if needle not in html:
            fail(f'the page lacks {needle}')
    print('domain only: 1 frame, controls present')
print('PASS')
