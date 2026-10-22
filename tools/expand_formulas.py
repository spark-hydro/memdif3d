import zipfile, re, json, collections
from xml.etree import ElementTree as ET
ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
z=zipfile.ZipFile('/home/spark/Documents/Andrew/Reduced_Matrix.xlsx')
root=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
def c2n(c):
    n=0
    for ch in c: n=n*26+ord(ch)-64
    return n
def n2c(n):
    s=''
    while n: n,r=divmod(n-1,26); s=chr(65+r)+s
    return s
def split(a):
    m=re.match(r'([A-Z]+)(\d+)$',a); return c2n(m.group(1)),int(m.group(2))
ref=re.compile(r'(\$?)([A-Z]{1,3})(\$?)(\d+)')
def shift(f,dr,dc):
    def rep(m):
        ca,col,ra,row=m.groups()
        c=c2n(col); r=int(row)
        if not ca: c+=dc
        if not ra: r+=dr
        return f"{ca}{n2c(c)}{ra}{r}"
    return ref.sub(rep,f)
masters={}; cells={}; vals={}
for row in root.find(ns+'sheetData'):
    for c in row:
        a=c.get('r'); f=c.find(ns+'f'); v=c.find(ns+'v')
        if v is not None: vals[a]=v.text
        if f is None: continue
        if f.get('t')=='shared':
            si=f.get('si')
            if f.text: masters[si]=(a,f.text); cells[a]=f.text
            else:
                ma,mt=masters[si]; mc,mr=split(ma); cc,cr=split(a)
                cells[a]=shift(mt,cr-mr,cc-mc)
        else: cells[a]=f.text
# relative form
def rel(a,f):
    cc,cr=split(a)
    def rep(m):
        ca,col,ra,row=m.groups(); c=c2n(col); r=int(row)
        cs=f"C{c}" if ca else f"C[{c-cc}]"
        rs=f"R{r}" if ra else f"R[{r-cr}]"
        return rs+cs
    return ref.sub(rep,f)
json.dump({'cells':cells,'vals':vals},open('cells.json','w'))
pats=collections.OrderedDict()
cellpat={}
for a,f in cells.items():
    p=rel(a,f); 
    if p not in pats: pats[p]=len(pats)
    cellpat[a]=pats[p]
print(len(cells),'formulas',len(pats),'patterns')
cnt=collections.Counter(cellpat.values())
for p,i in pats.items(): print(i,cnt[i],p[:230])
json.dump({'pats':list(pats),'cellpat':cellpat},open('pats.json','w'))
