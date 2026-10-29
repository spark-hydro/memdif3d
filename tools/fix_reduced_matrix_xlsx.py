#!/usr/bin/env python3
"""Write a corrected copy of Reduced_Matrix.xlsx (stdlib only; the original is not changed).

    python3 fix_reduced_matrix_xlsx.py Reduced_Matrix.xlsx Reduced_Matrix_fixed.xlsx

The sheet has two mistakes (confirmed as mistakes by the author of the sheet), see docs/MODEL_SPEC.md section 6:

1. The last tile (the boundary slice Y = 28, columns ABV:ACT) is only 26 columns after the tile before it, while
   every other tile is 27 columns after the previous one. The formulas of the second-to-last tile (Y = 27) were
   copied with the usual +27 offset and so read their neighbour in that tile one column too far to the right.
   Fix: the last tile moves one column to the right (columns ABW:ACU), in both blocks. Formula text is not
   changed anywhere, so the 861 formulas of Y = 27 now point to the right cells.
2. The far column (Z = 24) of the tiles Y = 20 (UM) and Y = 26 (AAS) holds the typed number 0 in rows 51:91 where
   all other tiles have a formula such as =TK59*0.82; in tile Y = 26 the two corner cells AAS50 and AAS92 read that
   zero column instead of their left neighbour. Fix: UM51:UM91 and AAS51:AAS91 get =<left neighbour>*0.82, and
   AAS50, AAS92 get =AAR50*0.82, =AAR92*0.82 like the other tiles.

Shared formulas are written out as ordinary formulas first (needed for the move); the calculation chain is dropped
and the workbook is set to recalculate fully when it is opened. The macro needs its ranges widened by one column:
see excel/DailyRun_fixed.bas. Only the small Reduced_Matrix.xlsx is handled here.
"""
import re
import sys
import zipfile

REF = re.compile(r'(\$?)([A-Z]{1,3})(\$?)(\d+)')
CELL = re.compile(r'<c r="([A-Z]+)(\d+)"((?:\s[^>]*?)?)(/>|>.*?</c>)', re.S)
FORM = re.compile(r'<f([^>]*?)(?:/>|>(.*?)</f>)', re.S)
LAST_TILE_FIRST_COL = 750          # ABV, first column of the boundary tile Y = 28


def c2n(c):
    n = 0
    for ch in c:
        n = n * 26 + ord(ch) - 64
    return n


def n2c(n):
    s = ''
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def shift(f, dr, dc):
    def rep(m):
        ca, col, ra, row = m.groups()
        c, r = c2n(col), int(row)
        if not ca:
            c += dc
        if not ra:
            r += dr
        return f'{ca}{n2c(c)}{ra}{r}'
    return REF.sub(rep, f)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1:]
    zin = zipfile.ZipFile(src)
    sheet = zin.read('xl/worksheets/sheet1.xml').decode('utf-8')

    # pass 1: masters of shared formulas
    masters = {}
    for m in CELL.finditer(sheet):
        f = FORM.search(m.group(4))
        if f and 'shared' in f.group(1) and f.group(2) is not None:
            si = re.search(r'si="(\d+)"', f.group(1)).group(1)
            masters[si] = (c2n(m.group(1)), int(m.group(2)), f.group(2))

    stats = dict(expanded=0, zeros=0, corners=0, moved=0)

    def fix(m):
        col, row, attrs, rest = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        n = c2n(col)
        # 1. shared formulas -> ordinary formulas
        f = FORM.search(rest)
        if f and 'shared' in f.group(1):
            si = re.search(r'si="(\d+)"', f.group(1)).group(1)
            mc, mr, text = masters[si]
            new = shift(text, row - mr, n - mc)
            rest = rest[:f.start()] + f'<f>{new}</f>' + rest[f.end():]
            stats['expanded'] += 1
        # 2. the typed zeros and the two corner cells of tile Y = 26
        if col in ('UM', 'AAS') and 51 <= row <= 91:
            assert '<f' not in rest and '<v>0</v>' in rest, (col, row, rest)
            rest = rest.replace('<v>0</v>', f'<f>{n2c(n - 1)}{row}*0.82</f><v>0</v>', 1)
            stats['zeros'] += 1
        if col == 'AAS' and row in (50, 92):
            new = f'AAR{row}*0.82'
            f = FORM.search(rest)
            rest = rest[:f.start()] + f'<f>{new}</f>' + rest[f.end():]
            stats['corners'] += 1
        # 3. the last tile moves one column to the right
        if n >= LAST_TILE_FIRST_COL:
            col = n2c(n + 1)
            stats['moved'] += 1
        return f'<c r="{col}{row}"{attrs}{rest}'

    sheet2 = CELL.sub(fix, sheet)
    sheet2 = sheet2.replace('spans="1:774"', 'spans="1:775"').replace('<dimension ref="A1:ACT92"/>', '<dimension ref="A1:ACU92"/>')
    assert 'ref="A1:ACU92"' in sheet2 and 'shared' not in sheet2, 'shared formulas left over'
    assert stats['zeros'] == 82 and stats['corners'] == 2, stats

    # the calculation chain lists the old cell addresses: drop it, and recalculate fully when the file is opened
    wb = zin.read('xl/workbook.xml').decode('utf-8').replace('<calcPr calcId="191029"/>', '<calcPr calcId="191029" fullCalcOnLoad="1"/>')
    ct = re.sub(r'<Override PartName="/xl/calcChain.xml"[^>]*/>', '', zin.read('[Content_Types].xml').decode('utf-8'))
    rels = re.sub(r'<Relationship [^>]*calcChain[^>]*/>', '', zin.read('xl/_rels/workbook.xml.rels').decode('utf-8'))
    assert 'fullCalcOnLoad' in wb and 'calcChain' not in ct and 'calcChain' not in rels

    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == 'xl/calcChain.xml':
                continue
            data = zin.read(item.filename)
            if item.filename == 'xl/worksheets/sheet1.xml':
                data = sheet2.encode('utf-8')
            elif item.filename == 'xl/workbook.xml':
                data = wb.encode('utf-8')
            elif item.filename == '[Content_Types].xml':
                data = ct.encode('utf-8')
            elif item.filename == 'xl/_rels/workbook.xml.rels':
                data = rels.encode('utf-8')
            zout.writestr(item, data)
    print(f"{dst}: {stats['expanded']} shared formulas written out, {stats['zeros']} zero cells given formulas, "
          f"{stats['corners']} corner cells corrected, {stats['moved']} cells of the last tile moved one column to the right")


if __name__ == '__main__':
    main()
