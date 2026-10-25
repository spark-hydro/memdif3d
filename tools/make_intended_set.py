#!/usr/bin/env python3
"""Make the "intended" version of the Reduced_Matrix input set: the two spreadsheet irregularities removed.

    python3 make_intended_set.py data/reduced_matrix data/reduced_matrix_intended

The spreadsheet's irregularities are exactly the exceptions of its input set:
1. Slice 27 (ILAY 28) reads its next-slice neighbour one position too far along Z (a copied formula kept a
   +27 column offset where the last slice is only 26 columns away). These are the 861 neighbor_overrides.
2. In slices 20 and 26 (ILAY 21 and 27) the far boundary (ICOL = NCOL) holds the typed number 0 instead of
   0.82 times its neighbour, and the corner cells next to them read those zeros. These are the boundary_cells.
The intended set keeps the five side rules and drops both lists, so every boundary cell follows its rule.
The sheet-exact set stays as it is (it reproduces Excel to 2e-16). The tool refuses a set that does not have
exactly 861 overrides, so it cannot be used on other models by mistake.
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
    new, mode, nexc, nover = [], None, 0, 0
    for ln in open(path).read().split('\n'):
        s = ln.strip()
        if s.startswith('BEGIN '):
            mode = s.split()[1]
        elif s.startswith('END '):
            mode = None
        elif s and not s.startswith('#') and mode == 'boundary_cells':
            nexc += 1
            continue
        elif s and not s.startswith('#') and mode == 'neighbor_overrides':
            nover += 1
            continue
        new.append(ln)
    if nover != 861 or nexc == 0:
        sys.exit(f'expected 861 overrides and some boundary_cells, found {nover} and {nexc}: not the Reduced_Matrix set')
    text = '\n'.join(new)
    text = text.replace('# memdif3d boundary:', '# Intended pattern (the two spreadsheet irregularities removed, see tools/make_intended_set.py).\n# memdif3d boundary:', 1)
    open(path, 'w').write(text)
    for f in os.listdir(out):
        if f.endswith('.nam'):
            p = os.path.join(out, f)
            t = open(p).read()
            t = re.sub(r'TITLE .*', 'TITLE Reduced_Matrix case, irregularities removed', t)
            open(p, 'w').write(t)
    print(f'{nexc} boundary_cells and {nover} overrides removed -> {os.path.join(out, [f for f in os.listdir(out) if f.endswith(".nam")][0])}')


if __name__ == '__main__':
    main()
