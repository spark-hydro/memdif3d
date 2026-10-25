#!/usr/bin/env python3
"""Make the "intended" version of the Reduced_Matrix input set: the two spreadsheet irregularities removed.

    python3 make_intended_set.py data/reduced_matrix data/reduced_matrix_intended

1. Slice 27 (ILAY 28) reads its next-slice neighbour one position too far along Z (a copied formula kept a
   +27 column offset where the last slice is only 26 columns away). Removed: the 861 neighbor_overrides.
2. In slices 20 and 26 (ILAY 21 and 27) the far boundary (ICOL = NCOL) holds the typed number 0 instead of
   0.82 times its neighbour. Changed: the 82 FIXED lines become COPY of the cell next to them, factor 0.82.
The sheet-exact set stays as it is (it reproduces Excel to 2e-16). The tool refuses a set that does not have
exactly these 861 overrides and 82 FIXED lines, so it cannot be used on other models by mistake.
"""
import os
import re
import shutil
import sys


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, out = sys.argv[1:]
    shutil.copytree(src, out, dirs_exist_ok=True)
    name = [f for f in os.listdir(out) if f.endswith('.bnd')]
    if len(name) != 1:
        sys.exit('expected one .bnd file in ' + out)
    path = os.path.join(out, name[0])
    dis = open([os.path.join(out, f) for f in os.listdir(out) if f.endswith('.dis')][0]).read()
    ncol = int(re.search(r'^\s*NCOL\s+(\d+)', dis, re.M).group(1))
    lines = open(path).read().split('\n')
    new, mode, nfix, nover = [], None, 0, 0
    for ln in lines:
        s = ln.strip()
        if s.startswith('BEGIN '):
            mode = s.split()[1]
        elif s.startswith('END '):
            mode = None
        elif s and not s.startswith('#') and mode == 'ghosts' and ' FIXED ' in ' ' + s + ' ':
            w = s.split()
            lay, row, col = w[:3]
            if int(col) != ncol or float(w[4]) != 0.0:
                sys.exit('FIXED line is not a zero on the far boundary: ' + s)
            ln = f'  {lay} {row} {col} COPY {lay} {row} {int(col) - 1} 0.82'
            nfix += 1
        elif s and not s.startswith('#') and mode == 'neighbor_overrides':
            nover += 1
            continue
        new.append(ln)
    if (nfix, nover) != (82, 861):
        sys.exit(f'expected 82 FIXED lines and 861 overrides, found {nfix} and {nover}: not the Reduced_Matrix set')
    text = '\n'.join(new)
    text = text.replace('# Ghost cells', '# Intended pattern (the two spreadsheet irregularities removed, see tools/make_intended_set.py).\n# Ghost cells', 1)
    open(path, 'w').write(text)
    for f in os.listdir(out):
        if f.endswith('.nam'):
            p = os.path.join(out, f)
            t = open(p).read()
            t = re.sub(r'TITLE .*', 'TITLE Reduced_Matrix case, irregularities removed', t)
            open(p, 'w').write(t)
    print(f'{nfix} FIXED lines -> COPY 0.82, {nover} overrides removed -> {os.path.join(out, [f for f in os.listdir(out) if f.endswith(".nam")][0])}')


if __name__ == '__main__':
    main()
