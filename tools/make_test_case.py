#!/usr/bin/env python3
"""Write small synthetic memdif3d input sets for testing (stdlib only).

    python3 make_test_case.py open   <outdir>   off-centre rectangular source, different ghost rules,
                                                sorption, advection, a neighbour override, 2 min step
    python3 make_test_case.py closed <outdir>   sealed box without ghost cells: mass is conserved and the
                                                concentration must end up uniform (analytic answer)
    options: --diffusion D   sand diffusion (default 0.2 open / 0.3 closed); a large value breaks stability

Both cases use a different grid and source footprint than the Reduced_Matrix case, so they exercise
the reader and solver on geometry that is not hard-coded anywhere.
"""
import argparse
import os


def write(path, text):
    with open(path, 'w') as fh:
        fh.write(text)


def build(case, diffusion):
    if case == 'open':
        nx, ny, nz = 17, 13, 11
        faces_x, faces_y = range(6, 11), range(4, 7)       # 5 x 3 faces, off centre
        sand = dict(D=diffusion or 0.2, t=2.0, ph=0.35, l=1.0)
        memb = dict(D=0.15, t=1.1, ph=0.05, l=0.5)
        por, rho, kd = 0.35, 1.6, 0.4
        vol, cm0, vel = 50.0, 2.0, 0.03
        step_len, spp, nper = 2.0, 15, 3
    else:
        nx, ny, nz = 8, 6, 6
        faces_x, faces_y = range(3, 6), range(2, 5)        # 3 x 3 faces
        sand = dict(D=diffusion or 0.3, t=1.5, ph=0.4, l=1.0)
        memb = dict(D=0.2, t=1.0, ph=0.1, l=0.3)
        por, rho, kd = 0.4, 1.5, 0.2
        vol, cm0, vel = 40.0, 1.0, 0.0
        step_len, spp, nper = 1.0, 200, 20
    faces = {(x, y) for x in faces_x for y in faces_y}

    def ring(x, y, z):
        return x in (1, nx) or y in (1, ny) or z == nz

    code, ghosts = {}, {}
    for y in range(1, ny + 1):
        for x in range(1, nx + 1):
            for z in range(1, nz + 1):
                p = (x, y, z)
                plate = (case == 'open' and z <= 3 and (x, y) not in faces) or \
                        (case == 'closed' and z == 1 and (x, y) not in faces)
                if case == 'closed':
                    code[p] = 0 if (ring(x, y, z) or plate) else 1
                elif plate:
                    code[p] = 0
                elif ring(x, y, z):
                    code[p] = 2
                    if x == 1:
                        ghosts[p] = ('COPY', (2, y, z), 0.82)
                    elif x == nx:
                        ghosts[p] = ('COPY', (nx - 1, y, z), 0.5)
                    elif y == 1:
                        ghosts[p] = ('COPY', (x, 2, z), 0.9)
                    elif y == ny:
                        ghosts[p] = ('FIXED', None, 0.0)
                    else:
                        ghosts[p] = ('COPY', (x, y, nz - 1), 0.82)
                else:
                    code[p] = 1

    # ghost evaluation order: constants first, then copies after the ghosts they read
    order = [p for p, g in ghosts.items() if g[0] == 'FIXED']
    pending = {p: g for p, g in ghosts.items() if g[0] == 'COPY'}
    while pending:
        ready = [p for p, g in pending.items() if g[1] not in pending]
        assert ready, 'circular ghost dependencies'
        for p in sorted(ready, key=lambda q: (q[2], q[1], q[0])):
            order.append(p)
            del pending[p]

    def arr(name, f, fmt):
        lines = [f'  {name}', '    INTERNAL']
        for y in range(1, ny + 1):
            lines.append(f'    # IY {y}')
            for x in range(1, nx + 1):
                lines.append('    ' + ' '.join(fmt(f((x, y, z))) for z in range(1, nz + 1)))
        return '\n'.join(lines) + '\n'

    def ic(p):
        if code[p] == 0:
            return 0.0
        if case == 'closed':
            return 0.0
        return 0.05 * ((p[0] * 7 + p[1] * 3 + p[2]) % 5) if code[p] == 1 else 0.01

    nfluid = sum(1 for c in code.values() if c == 1)
    adv = {p: 1 if (code[p] == 1 and not (p[2] <= 3 and (p[0], p[1]) in faces)) else 0 for p in code}
    files = {}
    files['t.nam'] = ('BEGIN options\n  TITLE synthetic ' + case + ' case\nEND options\nBEGIN packages\n'
                      '  TDIS t.tdis\n  DIS t.dis\n  IC t.ic\n  DSP t.dsp\n  MST t.mst\n  SRC t.src\n'
                      '  ADV t.adv\n  BND t.bnd\n  OC t.oc\nEND packages\n')
    files['t.tdis'] = (f'BEGIN options\n  TIME_UNITS minutes\nEND options\nBEGIN timing\n  STEP_LENGTH {step_len}\n'
                       f'  STEPS_PER_PERIOD {spp}\n  NPERIODS {nper}\nEND timing\n')
    files['t.dis'] = (f'BEGIN dimensions\n  NX {nx}\n  NY {ny}\n  NZ {nz}\nEND dimensions\n'
                      f'BEGIN griddata\n{arr("IDOMAIN", lambda p: code[p], str)}END griddata\n')
    files['t.ic'] = f'BEGIN griddata\n{arr("STRT", ic, repr)}END griddata\n'
    files['t.dsp'] = (''.join(f'BEGIN {n}\n  DIFFUSION {d["D"]!r}\n  TORTUOSITY {d["t"]!r}\n  POROSITY {d["ph"]!r}\n'
                              f'  LENGTH {d["l"]!r}\nEND {n}\n' for n, d in (('sand', sand), ('membrane', memb))))
    files['t.mst'] = f'BEGIN options\n  POROSITY {por!r}\n  BULK_DENSITY {rho!r}\n  KD {kd!r}\nEND options\n'
    files['t.src'] = (f'BEGIN source\n  VOLUME {vol!r}\n  START_CONC {cm0!r}\nEND source\nBEGIN faces\n' +
                      ''.join(f'  {x} {y}\n' for x, y in sorted(faces, key=lambda q: (q[1], q[0]))) + 'END faces\n')
    files['t.adv'] = (f'BEGIN options\n  VELOCITY {vel!r}\nEND options\nBEGIN griddata\n'
                      f'{arr("ADVMASK", lambda p: adv[p], str)}END griddata\n')
    gl = []
    for p in order:
        kind, src, val = ghosts[p]
        gl.append(f'  {p[0]} {p[1]} {p[2]} FIXED {val!r}' if kind == 'FIXED'
                  else f'  {p[0]} {p[1]} {p[2]} COPY {src[0]} {src[1]} {src[2]} {val!r}')
    ov = []
    if case == 'open':                     # two exceptions: skip a cell in +Y, and cut a link in -X
        ov = ['  4 8 6 +Y SET 4 10 6', '  9 5 8 -X OMIT']
    files['t.bnd'] = ('BEGIN ghosts\n' + '\n'.join(gl) + ('\n' if gl else '') + 'END ghosts\n'
                      'BEGIN neighbor_overrides\n' + '\n'.join(ov) + ('\n' if ov else '') + 'END neighbor_overrides\n')
    probes = '8 5 1\n  8 5 5' if case == 'open' else '4 3 1\n  4 3 4'
    files['t.oc'] = ('BEGIN options\n  DAILY_FIELD FILEOUT field_{period}.csv\n  PROBES FILEOUT probes_{period}.csv\n'
                     '  RESTART FILEOUT restart.dat\nEND options\nBEGIN probes\n  SOURCE\n  ' + probes + '\nEND probes\n')
    info = dict(nfluid=nfluid, vol=vol, cm0=cm0, retardation=por + rho * kd, nx=nx, ny=ny, nz=nz)
    return files, info


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('case', choices=['open', 'closed'])
    ap.add_argument('outdir')
    ap.add_argument('--diffusion', type=float, default=None)
    a = ap.parse_args()
    files, info = build(a.case, a.diffusion)
    os.makedirs(a.outdir, exist_ok=True)
    for name, text in files.items():
        write(os.path.join(a.outdir, name), text)
    print(info)
