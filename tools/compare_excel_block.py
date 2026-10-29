#!/usr/bin/env python3
"""Compare a memdif3d field file with one block of values stored in a spreadsheet (e.g. the last
time block of 3d_nonzeroboundry.xlsx, read as a stream, so huge files are fine).

    python3 compare_excel_block.py BOOK.xlsx FIELD.csv --first-row 50694 --nam rm.nam

--first-row is the first sheet row of the block (43 rows). Needs numpy. The column layout is the one
of Reduced_Matrix.xlsx (tiles at columns 1, 27, ..., see docs/MODEL_SPEC.md section 3).
Prints the largest absolute difference over all cells, the boundary cells and the source cell.
"""
import argparse
import os
import sys
import zipfile
from xml.etree import ElementTree as ET

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animate_field as AF  # noqa: E402  (read_field)
import memdif_proto as P    # noqa: E402

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def n2c(n):
    s = ''
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


LAST_TILE = 750                    # first column of the last tile (Y = 28); 751 in Reduced_Matrix_fixed.xlsx


def base(y):                       # first column of slice y (0-based), Reduced_Matrix layout
    return 1 + 26 * y if y <= 6 else (157 + 27 * (y - 6) if y <= 27 else LAST_TILE)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('xlsx')
    ap.add_argument('field')
    ap.add_argument('--first-row', type=int, required=True)
    ap.add_argument('--nam', required=True)
    ap.add_argument('--fixed-layout', action='store_true', help='the workbook is Reduced_Matrix_fixed.xlsx (last tile one column further right)')
    a = ap.parse_args()
    global LAST_TILE
    if a.fixed_layout:
        LAST_TILE = 751
    m = P.Model(a.nam)
    nx, ny, nz = m.nx, m.ny, m.nz
    lo, hi = a.first_row, a.first_row + nx - 1
    vals = {}
    with zipfile.ZipFile(a.xlsx).open('xl/worksheets/sheet1.xml') as f:
        for _, el in ET.iterparse(f, events=('end',)):
            if el.tag == NS + 'row':
                rn = int(el.get('r'))
                if lo <= rn <= hi:
                    for c in el:
                        v = c.find(NS + 'v')
                        if v is not None and c.get('t') in (None, 'n'):
                            vals[c.get('r')] = float(v.text)
                el.clear()
    big = np.zeros((ny, nx, nz))
    for y in range(ny):
        for x in range(nx):
            for z in range(nz):
                big[y, x, z] = vals.get(n2c(base(y) + z) + str(lo + x), 0.0)
    arr, info = AF.read_field(a.field)
    bnd = np.zeros(arr.shape, bool)
    for (x, iy, iz), c in m.idom.items():
        bnd[iy - 1, x - 1, iz - 1] = (c == 2)
    cms = [vals.get(n2c(base(iy - 1) - 1) + str(lo + x - 1)) for (x, iy) in m.faces]
    print(f"step {info['step']}  ({info['minutes']:.0f} min)")
    print(f'all cells        max abs diff {np.abs(arr - big).max():.2e}')
    print(f'boundary cells      max abs diff {np.abs(arr - big)[bnd].max():.2e}')
    print(f"source cell      memdif3d {info['cm']:.15f}   sheet {np.mean(cms):.15f}")


if __name__ == '__main__':
    main()
