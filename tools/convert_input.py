#!/usr/bin/env python3
"""Convert a memdif3d input set from the list formats (faces as lines, boundary cells as a 'ghosts' list)
to the compact formats (faces as a map, boundary as side rules plus exceptions).

    python3 convert_input.py OLD_DIR NEW_DIR [--rules "IROW=1:COPY 0.82,IROW=NROW:COPY 0.82,ICOL=NCOL:COPY 0.82,ILAY=1:COPY 0.82,ILAY=NLAY:COPY 0.82"]

SRC: `BEGIN faces` lines "ilay irow [TYPE]" become a map of NLAY lines with NROW values
(0 none, 1 membrane, 2 hole, 3 closed).
BND: the side rules are expanded and compared with the old `ghosts` list; every boundary cell whose old
entry differs from the rules goes to `boundary_cells`, in the old order, after the rules. The overrides
are copied. If the exceptions would not reproduce the old list the tool stops.
The default rules are the Reduced_Matrix ones; pass --rules for another model. See docs/INPUT_SPEC.md.
"""
import argparse
import os
import re
import shutil
import sys

DEFAULT_RULES = 'IROW=1:COPY 0.82,IROW=NROW:COPY 0.82,ICOL=NCOL:COPY 0.82,ILAY=1:COPY 0.82,ILAY=NLAY:COPY 0.82'


def blocks(text):
    out, cur = {}, None
    for ln in text.split('\n'):
        s = ln.split('#')[0].strip()
        if not s:
            continue
        w = s.split()
        if w[0].upper() == 'BEGIN':
            cur = out.setdefault(w[1].lower(), [])
        elif w[0].upper() == 'END':
            cur = None
        elif cur is not None:
            cur.append(w)
    return out


def read_dis(path):
    b = blocks(open(path).read())
    dims = {w[0].upper(): int(w[1]) for w in b['dimensions']}
    vals = [t for w in b['griddata'] for t in w if t.upper() not in ('IDOMAIN', 'INTERNAL')]
    nl, nr, nc = dims['NLAY'], dims['NROW'], dims['NCOL']
    if len(vals) != nl * nr * nc:
        sys.exit('IDOMAIN has the wrong number of values')
    idom = {}
    k = 0
    for il in range(1, nl + 1):
        for ir in range(1, nr + 1):
            for ic in range(1, nc + 1):
                idom[(il, ir, ic)] = int(vals[k])
                k += 1
    return nl, nr, nc, idom


def expand(rules, nl, nr, nc, idom):
    """-> list of (cell, kind, source cell or None, value); cells are (ilay, irow, icol)"""
    size = {'ILAY': nl, 'IROW': nr, 'ICOL': nc}
    axis = {'ILAY': 0, 'IROW': 1, 'ICOL': 2}
    named = {'NLAY': nl, 'NROW': nr, 'NCOL': nc}
    out = []
    for side, rule in rules:
        name, k = side.upper().split('=')
        kside = named.get(k.upper()) or int(k)
        step = 1 if kside == 1 else -1
        w = rule.split()
        for il in range(1, nl + 1):
            for ir in range(1, nr + 1):
                for ic in range(1, nc + 1):
                    p = (il, ir, ic)
                    if idom[p] != 2 or p[axis[name]] != kside:
                        continue
                    if w[0].upper() == 'FIXED':
                        out.append((p, 'FIXED', None, float(w[1])))
                    else:
                        q = list(p)
                        q[axis[name]] += step
                        out.append((p, 'COPY', tuple(q), float(w[1]) if w[0].upper() == 'COPY' else 1.0))
    return out


def convert_dir(old, new, rules_text=DEFAULT_RULES):
    if os.path.abspath(old) != os.path.abspath(new):
        shutil.copytree(old, new, dirs_exist_ok=True)
    files = {os.path.splitext(f)[1]: os.path.join(new, f) for f in os.listdir(new)}
    nl, nr, nc, idom = read_dis(files['.dis'])
    rules = [tuple(r.split(':', 1)) for r in rules_text.split(',')]

    # ---- SRC: faces list -> map
    src = open(files['.src']).read()
    head, rest = src.split('BEGIN faces')
    body, tail = rest.split('END faces')
    if 'FACES' in body.upper().split():
        print('SRC already has a faces map')
    else:
        code = {'MEMBRANE': 1, 'HOLE': 2, 'CLOSED': 3}
        fmap = [[0] * nr for _ in range(nl)]
        for ln in body.strip().split('\n'):
            s = ln.split('#')[0].split()
            if s:
                fmap[int(s[0]) - 1][int(s[1]) - 1] = code[s[2].upper()] if len(s) > 2 else 1
        lines = ['BEGIN faces', '  FACES', '    INTERNAL']
        for il in range(nl):
            lines.append(f'    # ILAY {il + 1}  (values along IROW 1..{nr})')
            lines.append('    ' + ' '.join(str(v) for v in fmap[il]))
        head = head.replace('Its faces touch ICOL = 1 of the listed (ILAY, IROW) cells.',
                            'Its faces touch ICOL = 1 under the cells of the FACES map: 0 none, 1 membrane, 2 hole, 3 closed.')
        open(files['.src'], 'w').write(head + '\n'.join(lines) + '\nEND faces' + tail)

    # ---- BND: ghosts list -> rules + exceptions
    bnd = open(files['.bnd']).read()
    b = blocks(bnd)
    if 'ghosts' not in b:
        print('BND has no ghosts list; left as it is')
        return
    old = []
    for w in b['ghosts']:
        p = tuple(int(t) for t in w[:3])
        if w[3].upper() == 'FIXED':
            old.append((p, 'FIXED', None, float(w[4])))
        else:
            old.append((p, 'COPY', tuple(int(t) for t in w[4:7]), float(w[7])))
    exp = expand(rules, nl, nr, nc, idom)
    final = {}
    for e in exp:
        final[e[0]] = e
    oldmap = {}
    for e in old:
        oldmap[e[0]] = e
    bcells = [p for p, c in idom.items() if c == 2]
    if set(oldmap) != set(bcells):
        sys.exit('the old ghosts list does not cover exactly the IDOMAIN = 2 cells')
    exc = [e for e in old if final.get(e[0]) != e]
    # an exception is applied after all rules: no rule cell may read an exception cell
    excells = {e[0] for e in exc}
    for e in final.values():                      # only the last entry of a cell counts; earlier ones are overwritten
        if e[0] not in excells and e[2] in excells:
            sys.exit('a rule cell reads an exception cell; the order would change: ' + str(e))
    # re-evaluate order inside the exceptions: sources must be set earlier (kept from the old list order)
    ov = [' '.join(w) for w in b.get('neighbor_overrides', [])]
    out = ['# memdif3d boundary: five side rules, per-cell exceptions, neighbour overrides.',
           '# Boundary cells are the IDOMAIN = 2 cells. The rules are evaluated in this order, a cell on two sides takes',
           '# the later rule and COPY reads the new value of the cell one step inward; then the exceptions, in file order.',
           '#   COPY factor | FIXED value | NOFLOW (= COPY 1.0).   Cell ids: ilay irow icol.',
           'BEGIN boundary']
    out += [f'  {s} {r.replace(":", " ")}' for s, r in rules]
    out += ['END boundary', '', 'BEGIN boundary_cells']
    for p, kind, q, v in exc:
        out.append(f'  {p[0]} {p[1]} {p[2]} FIXED {v!r}' if kind == 'FIXED' else
                   f'  {p[0]} {p[1]} {p[2]} COPY {q[0]} {q[1]} {q[2]} {v!r}')
    out += ['END boundary_cells', '', '# Neighbour overrides replace the default neighbour of a fluid cell in one direction.',
            '#   default: the 6 face neighbours that are not solid; ICOL = 1 under a source face looks at the source.',
            'BEGIN neighbor_overrides']
    out += ['  ' + o for o in ov]
    out += ['END neighbor_overrides', '']
    first = bnd.split('\n')[0]
    open(files['.bnd'], 'w').write((first + '\n' if first.startswith('#') else '') + '\n'.join(out))
    print(f'boundary: {len(exp)} rule entries expand to {len(final)} cells; {len(exc)} exceptions; {len(ov)} overrides')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('old')
    ap.add_argument('new')
    ap.add_argument('--rules', default=DEFAULT_RULES)
    a = ap.parse_args()
    convert_dir(a.old, a.new, a.rules)
    print(f'wrote {a.new}')


if __name__ == '__main__':
    main()
