import sys, re, json, random
sys.setrecursionlimit(10000)
sys.path.insert(0,'.')
import ref_step as R
V=json.load(open('cells.json')); F=V['cells']; vals={k:float(v) for k,v in V['vals'].items()}
n2c=R.n2c
random.seed(1)
# random block-0 state: all non-solid cells random in [0,1]; mixed column equal
CM=random.random(); C={}
state={}
for z in range(1,44):
    for y in range(29):
        for x in range(25):
            if R.solid(z,y,x): continue
            C[(z,y,x)]=random.random()
for y in range(7,22):
    for z in range(15,30):
        state[n2c(R.base(y)-1)+str(5+z)]=CM
for (z,y,x),u in C.items(): state[n2c(R.col(y,x))+str(5+z)]=u
# start values: block0 cells -> random state, else cached; formula cells in block1 evaluated
memo={}
refre=re.compile(r'(\$?)([A-Z]{1,3})(\$?)(\d+)')
rng=re.compile(r'SUM\((\$?[A-Z]{1,3}\$?\d+):(\$?[A-Z]{1,3}\$?\d+)\)')
def c2n(c):
    n=0
    for ch in c: n=n*26+ord(ch)-64
    return n
def g(a):
    m=re.match(r'([A-Z]+)(\d+)',a); r=int(m.group(2))
    if r<=48:
        if 6<=r<=48: return state.get(a,0.0)   # block 0: random state
        return vals.get(a,0.0)                  # params rows 1-4
    if a in memo: return memo[a]
    if a in F:
        memo[a]=ev(F[a],a)
    else: memo[a]=vals.get(a,0.0)
    return memo[a]
def s(a1,a2):
    a1=a1.replace('$',''); a2=a2.replace('$','')
    m1=re.match(r'([A-Z]+)(\d+)',a1); m2=re.match(r'([A-Z]+)(\d+)',a2)
    t=0.0
    for c in range(c2n(m1.group(1)),c2n(m2.group(1))+1):
        for r in range(int(m1.group(2)),int(m2.group(2))+1): t+=g(n2c(c)+str(r))
    return t
def ev(f,a):
    f2=rng.sub(lambda m:f's("{m.group(1)}","{m.group(2)}")',f)
    f2=re.sub(r'(?<![A-Za-z"])(\$?)([A-Z]{1,3})(\$?)(\d+)(?![\d"])',lambda m:f'g("{m.group(2)}{m.group(4)}")',f2)
    return eval(f2)
N,CMn=R.step(C,CM)
worst=0;bad=0
for z in range(1,44):
    for y in range(29):
        for x in range(25):
            a=n2c(R.col(y,x))+str(49+z)
            if R.solid(z,y,x): continue
            ref=g(a); mine=N[(z,y,x)]
            d=abs(ref-mine); worst=max(worst,d)
            if d>1e-12: bad+=1
print('random-state test: fluid cells',len(C),'max abs diff',worst,'mismatches',bad)
print('source cell: Excel',g('GA71'),'mine',CMn)
# mixed copies
print('mixed copy check',max(abs(g(n2c(R.base(y)-1)+str(49+z))-CMn) for y in range(7,22) for z in range(15,30)))
import collections
cls=collections.Counter(); ex={}
for z in range(1,44):
    for y in range(29):
        for x in range(25):
            if R.solid(z,y,x): continue
            a=n2c(R.col(y,x))+str(49+z)
            if abs(g(a)-N[(z,y,x)])>1e-12:
                k=('y0/28' if y in(0,28) else '')+('z1/43' if z in(1,43) else '')+('x24' if x==24 else '')+('foot' if R.foot(z,y) else '')+('x<3' if x<3 else '')
                cls[k]+=1; ex.setdefault(k,(a,(z,y,x),g(a),N[(z,y,x)],F.get(a)))
print(cls)
for k,v in ex.items(): print(k,v)
print('---- constants where a formula is expected (x=24 ghost, z in 1..43):')
const_x24=collections.defaultdict(list)
for y in range(1,28):
    for z in range(1,44):
        a=n2c(R.col(y,24))+str(49+z)
        if a not in F: const_x24[y].append(z)
for y,zs in const_x24.items(): print(' slice y=%d: %d cells, z=%s..%s'%(y,len(zs),zs[0],zs[-1]))
print('---- interior (z 2..42, x<=23, 1<=y<=27) mismatches by slice:')
by=collections.defaultdict(list)
for z in range(2,43):
    for y in range(1,28):
        for x in range(0,24):
            if R.solid(z,y,x): continue
            a=n2c(R.col(y,x))+str(49+z)
            if abs(g(a)-N[(z,y,x)])>1e-12: by[y].append((z,x))
for y,l in by.items(): print(' y=%d n=%d x-set=%s zrange=%s-%s'%(y,len(l),sorted({x for _,x in l})[:6],min(z for z,_ in l),max(z for z,_ in l)))
# which cells' formulas reference stride mismatch
print('---- y-neighbour column offsets used by cells (interior formulas), by slice:')
for y in (5,6,7,8,20,21,22,26,27):
    a=n2c(R.col(y,10))+'60'; f=F[a]; 
    offs=sorted({c2n(m.group(2))-c2n(n2c(R.col(y,10))) for m in refre.finditer(f) if m.group(2) not in ('GM','GV','FZ','GG','GQ') and abs(c2n(m.group(2))-c2n(n2c(R.col(y,10))))>1})
    print(' y=%d col offsets %s'%(y,offs), '(true stride -, +:', R.base(y)-R.base(y-1), R.base(y+1)-R.base(y),')')
