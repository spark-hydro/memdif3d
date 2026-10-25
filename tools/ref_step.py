import json, re
import os
if os.path.exists('cells.json'):          # written by expand_formulas.py; only needed for the Excel comparison
    V=json.load(open('cells.json')); vals={k:float(v) for k,v in V['vals'].items()}
else:                                      # parameters of Reduced_Matrix.xlsx
    vals={'GM1':0.015,'GG1':0.125*0.02/0.3,'GV1':0.3,'FZ1':0.0,'GQ1':5625.0}
def n2c(n):
    s=''
    while n: n,r=divmod(n-1,26); s=chr(65+r)+s
    return s
NZ,NY,NX=43,29,25
def base(y): return 1+26*y if y<=6 else (157+27*(y-6) if y<=27 else 750)
def col(y,x): return base(y)+x
def foot(z,y): return 15<=z<=29 and 7<=y<=21
Ks=vals['GM1']; Km=vals['GG1']; R=vals['GV1']; v=vals['FZ1']; Vs=vals['GQ1']
ks,km=Ks/R,Km/R
def get(block_row0,z,y,x): return vals.get(n2c(col(y,x))+str(block_row0+z),0.0)
def solid(z,y,x): return x<=2 and not foot(z,y)
def step(C,CM,quirks=True):
    N={}
    def c(z,y,x): return C.get((z,y,x),0.0)
    # interior fluid cells
    for y in range(1,NY-1):
        for z in range(2,NZ):
            for x in range(0,24):
                if solid(z,y,x): continue
                u=c(z,y,x); s=u
                for dz,dy,dx in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                    zz,yy,xx=z+dz,y+dy,x+dx
                    if quirks and y==NY-2 and dy==1: xx=x+1   # Excel quirk 1: slice 27 reads slice 28 shifted by +1 in x
                    if dx==-1 and x==0:
                        if foot(z,y): s+=km*(CM-u)
                        continue
                    if not(0<=xx<NX) or solid(zz,yy,xx): continue
                    s+=ks*(c(zz,yy,xx)-u)
                if not(x<=2 and foot(z,y)): s+=v*c(z+1,y,x)-v*u
                N[(z,y,x)]=s
    # source
    tot=0.0
    for y in range(7,22):
        for z in range(15,30): tot+=CM-c(z,y,0)
    CMn=CM-Km*tot/Vs
    # boundary cells (new values, in dependency order)
    for y in range(1,NY-1):
        for x in range(3,24):
            N[(1,y,x)]=0.82*N[(2,y,x)]; N[(NZ,y,x)]=0.82*N[(NZ-1,y,x)]
    for y in range(1,NY-1):
        for z in range(1,NZ+1):
            if quirks and y==26 and z in (1,NZ): N[(z,y,24)]=0.0   # corner reads the constant-0 neighbour
            elif quirks and y in (20,26) and 2<=z<=NZ-1:   # Excel quirk 2: far boundary is constant 0 here
                N[(z,y,24)]=0.0
            else: N[(z,y,24)]=0.82*N[(z,y,23)]
    for z in range(1,NZ+1):
        for x in range(NX):
            N[(z,0,x)]=0.82*N.get((z,1,x),0.0); N[(z,NY-1,x)]=0.82*N.get((z,NY-2,x),0.0)
    return N,CMn
NZ_=NZ
if __name__=='__main__':
    C={}; 
    for z in range(1,NZ+1):
        for y in range(NY):
            for x in range(NX):
                a=get(5,z,y,x)
                if a: C[(z,y,x)]=a
    CM=1.0
    N,CMn=step(C,CM)
    worst=0; n=0; bad=[]
    for z in range(1,NZ+1):
        for y in range(NY):
            for x in range(NX):
                ref=get(49,z,y,x); mine=N.get((z,y,x),0.0)
                if solid(z,y,x): mine=0.0
                d=abs(ref-mine); n+=1
                if d>worst: worst=d
                if d>1e-12: bad.append(((z,y,x),ref,mine))
    print('cells compared',n,'max abs diff',worst,'mismatches',len(bad)); print(bad[:6])
    print('source: excel GA71 =',vals['GA71'] if 'GA71' in vals else None,' mine',CMn)
