#!/usr/bin/env python3
"""Interactive viewer of a memdif3d model and its results: one self-contained HTML file.

    python3 make_viewer.py RUN_DIR --nam path/to/rm.nam --out viewer.html
    python3 make_viewer.py RUN_DIR --nam rm.nam --pattern 'day_*.txt' --every 60 --from 0 --to 360
    python3 make_viewer.py --nam rm.nam --out domain.html            # only the domain and the start state

Open the HTML in any browser (no server, no internet). Left: the 3D domain (the box of sand cells, the source,
the membrane faces: grey = membrane, red = hole, black = closed) that you can rotate, with the plane you chose
drawn inside it. Right: the concentration on that plane, animated over time. Choose the kind of plane and its
number in the page, without running anything again:
  Layer   one ILAY, rows x columns           (top view, MODFLOW xy)
  Row     one IROW, layers x columns         (row section, MODFLOW xz)
  Column  one ICOL, rows x layers            (column plane, MODFLOW yz; ICOL = 1 touches the membrane)
The source concentration is drawn as column 0 next to the membrane. Linear or logarithmic colours, the top of the
colour scale and the play speed can be changed in the page.
Lower left: the probes. The files probes_*.csv of RUN_DIR (the cells and the source written every minute) are drawn
as concentration against time, a line for every probe with a dot at every frame of the animation, and a vertical
line at the time shown; a drop-down chooses one probe or all of them. The probe cells are marked in the 3D domain and on the plane picture (when the plane contains them), in the colour of
their line.
--probes PATTERN changes the file pattern (default 'probes*.csv'), --no-probes leaves them out.

Frames are the files of RUN_DIR that --pattern matches: field_*.csv (one per day, default), snap_*.csv, or the
minutes output day_*.txt / day_*.csv (--every N keeps every N-th minute; --from / --to give a time window in
minutes; keep probes_NNN.csv next to the day files). The start state is the first frame when the window begins at 0.

The page holds the concentration of every cell of every frame as a compressed 16-bit number (relative precision
about 1e-4), so its size grows with the number of frames: about 15 to 50 KB per frame for the Reduced_Matrix case.

Needs: numpy, plotly (only for the plotting library file that goes into the page)
"""
import argparse
import base64
import glob
import json
import os
import sys
import zlib

try:
    import numpy as np
    from plotly.offline import get_plotlyjs
except ImportError as e:                       # pragma: no cover
    sys.exit(f'make_viewer.py needs numpy and plotly ({e}). Install: pip install numpy plotly')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from animate_field import load_frames          # noqa: E402
import memdif_proto as P                       # noqa: E402

KIND = {'MEMBRANE': 1, 'HOLE': 2, 'CLOSED': 3}


def pack(raw):
    """bytes -> base64 text of the zlib-compressed bytes (the page inflates it with DecompressionStream)"""
    return base64.b64encode(zlib.compress(bytes(raw), 6)).decode('ascii')


def read_probes(run_dir, pattern, tfrom, tto):
    """probe files of a run -> (names, time[n], value[n, nprobe]) or None; later files continue earlier ones"""
    names, rows = None, {}
    for f in sorted(glob.glob(os.path.join(run_dir, pattern))):
        with open(f) as fh:
            head = fh.readline().strip().split(',')
            if len(head) < 3 or head[:2] != ['step', 'time']:
                continue
            if names is None:
                names = head[2:]
            elif head[2:] != names:
                sys.exit(f'{f}: the probe columns differ from those of the first probe file')
            for line in fh:
                t = line.strip().split(',')
                if len(t) == len(head):
                    rows[int(t[0])] = [float(x) for x in t[1:]]
    if not names or not rows:
        return None
    arr = np.array([rows[k] for k in sorted(rows)])
    time, val = arr[:, 0], arr[:, 1:]
    keep = np.ones(len(time), bool)
    if tfrom is not None:
        keep &= time >= tfrom
    if tto is not None:
        keep &= time <= tto
    if not keep.any():
        return None
    return names, time[keep], val[keep]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run_dir', nargs='?', default=None, help='folder with the result files (omit for the domain only)')
    ap.add_argument('--nam', required=True, help='name file of the model')
    ap.add_argument('--out', default='viewer.html')
    ap.add_argument('--pattern', default='field_*.csv')
    ap.add_argument('--every', type=int, default=1, help='use every n-th file (day files: every n-th step)')
    ap.add_argument('--from', dest='tfrom', type=float, default=None, help='first minute shown (1 day = 1440)')
    ap.add_argument('--to', dest='tto', type=float, default=None, help='last minute shown')
    ap.add_argument('--no-initial', action='store_true', help='do not add the start state as the first frame')
    ap.add_argument('--probes', default='probes*.csv', help='probe files in RUN_DIR (default probes*.csv)')
    ap.add_argument('--no-probes', action='store_true', help='leave the probe panel out')
    a = ap.parse_args()

    m = P.Model(a.nam)
    ny, nx, nz = m.ny, m.nx, m.nz                                   # ILAY, IROW, ICOL
    idom = np.zeros((ny, nx, nz), np.uint8)
    c0 = np.zeros((ny, nx, nz))
    for (x, iy, iz), code in m.idom.items():
        idom[iy - 1, x - 1, iz - 1] = code
        c0[iy - 1, x - 1, iz - 1] = m.c0[(x, iy, iz)]
    fluid = idom == 1

    frames = []
    files = sorted(glob.glob(os.path.join(a.run_dir, a.pattern))) if a.run_dir else []
    if files:
        frames = load_frames(files, a.every, m.cm0, a.tfrom, a.tto)
        if frames[0][0].shape != (ny, nx, nz):
            sys.exit('name file and result files have different grid sizes (the files must hold all layers)')
    elif a.run_dir:
        print(f'note: no files {a.pattern} in {a.run_dir}: the page shows the domain and the start state only')
    if not a.no_initial and not a.tfrom and (not frames or frames[0][1]['step'] != 0):
        frames.insert(0, (c0, dict(period=0, step=0, minutes=0.0, cm=m.cm0)))
    nf = len(frames)

    probes = None
    if a.run_dir and not a.no_probes:
        pr = read_probes(a.run_dir, a.probes, a.tfrom, a.tto)
        if pr:
            names, ptime, pval = pr
            locs = []
            for n in names:
                parts = n.split('_')
                locs.append([int(x) for x in parts] if len(parts) == 3 and all(x.isdigit() for x in parts) else None)
            if not a.no_initial and not a.tfrom:                     # the start state belongs to the probes too
                row0 = [m.cm0 if l is None else float(c0[l[0] - 1, l[1] - 1, l[2] - 1]) for l in locs]
                ptime, pval = np.insert(ptime, 0, 0.0), np.vstack([row0, pval])
            stride = max(1, len(ptime) // 100000)                    # at most about 100,000 points per probe
            if stride > 1:
                print(f'note: the probe series is thinned to every {stride}th point')
                ptime, pval = ptime[::stride], pval[::stride]
            probes = dict(names=names, loc=locs, n=int(len(ptime)),
                          t=pack(ptime.astype('<f4').tobytes()), v=pack(np.ascontiguousarray(pval).astype('<f4').tobytes()))

    # concentrations as 16-bit numbers on a logarithmic scale: q = 0 means "below the floor" (zero)
    vmax = max(float(f[0][fluid].max()) for f in frames)
    if not vmax > 0:
        vmax = 1.0
    floor = vmax * 1e-7
    lo, hi = float(np.log10(floor)), float(np.log10(vmax))
    q = np.zeros((nf, ny, nx, nz), '<u2')
    for i, (arr, _) in enumerate(frames):
        v = np.where(fluid, arr, 0.0)
        pos = v > floor
        q[i][pos] = 1 + np.clip(np.round((np.log10(v[pos]) - lo) / (hi - lo) * 65534), 0, 65534)

    zs = np.where(fluid.any(axis=(0, 1)))[0]
    xs = np.where(fluid.any(axis=(0, 2)))[0]
    ys = np.where(fluid.any(axis=(1, 2)))[0]
    foot = sorted(m.faces)                                           # (IROW, ILAY) of open faces
    meta = dict(
        nlay=ny, nrow=nx, ncol=nz, nf=nf,
        minutes=[float(f[1]['minutes']) for f in frames], cm=[float(f[1]['cm']) for f in frames],
        lo=lo, hi=hi, vmax=vmax,
        bbox=dict(ilay=[int(ys[0]) + 1, int(ys[-1]) + 1], irow=[int(xs[0]) + 1, int(xs[-1]) + 1], icol=[int(zs[0]) + 1, int(zs[-1]) + 1]),
        faces=[[ir, il, KIND[k]] for (ir, il), k in sorted(m.kind.items())],
        foot=[[ir, il] for ir, il in foot],
        counts=dict(fluid=int(fluid.sum()), boundary=int((idom == 2).sum()), solid=int((idom == 0).sum())),
        title=os.path.basename(a.nam),
        probes=probes, idom=pack(idom.tobytes()), frames=pack(q.tobytes()))
    html = (TEMPLATE.replace('__TITLE__', 'memdif3d viewer: ' + os.path.basename(a.nam))
            .replace('__META__', json.dumps(meta, separators=(',', ':')))
            .replace('__PLOTLY__', get_plotlyjs()))
    with open(a.out, 'w', encoding='utf-8') as fh:
        fh.write(html)
    t = meta['minutes']
    pn = f', {len(probes["names"])} probes' if probes else ''
    print(f'{nf} frame{"s" if nf != 1 else ""} (minute {t[0]:g} to {t[-1]:g}){pn}, grid {ny} x {nx} x {nz} -> {a.out} '
          f'({os.path.getsize(a.out) / 1e6:.1f} MB)')
    if os.path.getsize(a.out) > 100e6:
        print('warning: the page is very large; use --every, --from and --to to keep fewer frames')


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f6f5f1;--fg:#1f2937;--mut:#5b6470;--card:#fdfcf9;--line:#d9d6cc;--acc:#0f766e}
@media (prefers-color-scheme:dark){:root{--bg:#14213d;--fg:#f3f1ea;--mut:#b9c2d0;--card:#1d2e55;--line:#33466f;--acc:#5eead4}}
body{margin:0;background:var(--bg);color:var(--fg);font-family:system-ui,Segoe UI,Arial,sans-serif;font-size:15px}
header{padding:10px 16px 0}h1{font-size:18px;margin:0 0 2px;font-weight:600}.sub{color:var(--mut);font-size:13px}
.bar{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;padding:10px 16px;background:var(--card);border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin-top:8px}
.bar label{display:flex;align-items:center;gap:6px;white-space:nowrap}
select,input,button{font:inherit;color:var(--fg);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:3px 6px}
button{cursor:pointer;padding:3px 12px}input[type=range]{padding:0;accent-color:var(--acc)}input[type=number]{width:5.5em}
.val{min-width:7em;color:var(--mut)}
.panels{display:grid;grid-template-columns:1fr 1fr;grid-template-areas:"s p" "q p";gap:8px;padding:8px 8px 16px}
.panels.noprobe{grid-template-areas:"s p"}
.panel{background:var(--card);border:1px solid var(--line);border-radius:10px;min-height:360px}
#scene{grid-area:s}#plane2d{grid-area:p}#probes{grid-area:q}
@media (max-width:1000px){.panels{grid-template-columns:1fr;grid-template-areas:"s" "p" "q"}.panels.noprobe{grid-template-areas:"s" "p"}}
#msg{padding:30px;text-align:center;color:var(--mut)}
</style></head><body>
<header><h1 id="title"></h1><div class="sub" id="sub"></div></header>
<div class="bar">
 <label>Plane <select id="ptype"><option value="layer">Layer (top view, xy)</option><option value="row">Row (section, xz)</option><option value="column">Column (plane, yz)</option></select></label>
 <label><span id="plab">ILAY</span> <input type="range" id="pidx" min="1" max="1" value="1"><input type="number" id="pnum" min="1" max="1" value="1"></label>
 <label>Time <input type="range" id="tsl" min="0" max="0" value="0" style="width:200px"><span class="val" id="tlab"></span></label>
 <button id="play">Play</button>
 <label>Speed <select id="speed"><option value="900">slow</option><option value="400" selected>normal</option><option value="150">fast</option></select></label>
 <label>Scale <select id="scale"><option value="log">logarithmic</option><option value="lin">linear</option></select></label>
 <label>Top of scale <input type="number" id="vmax" step="any"></label>
 <label><input type="checkbox" id="showbnd">boundary and solid cells</label>
 <label id="probelab" style="display:none">Probes <select id="probesel"></select></label>
</div>
<div id="msg">Loading the data ...</div>
<div class="panels" style="display:none" id="panels"><div class="panel" id="scene"></div><div class="panel" id="plane2d"></div><div class="panel" id="probes"></div></div>
<script>__PLOTLY__</script>
<script type="application/json" id="meta">__META__</script>
<script>
(async function(){
const META = JSON.parse(document.getElementById('meta').textContent);
const NL=META.nlay, NR=META.nrow, NC=META.ncol, NF=META.nf, NCELL=NL*NR*NC, LO=META.lo, HI=META.hi, BB=META.bbox;
const $ = id => document.getElementById(id);
async function inflate(b64){
  const bin=atob(b64), u8=new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++) u8[i]=bin.charCodeAt(i);
  const ds=new DecompressionStream('deflate');
  const buf=await new Response(new Blob([u8]).stream().pipeThrough(ds)).arrayBuffer();
  return new Uint8Array(buf);
}
let IDOM, Q, PRT=null, PRV=null;
try{
  IDOM = await inflate(META.idom);
  const raw = await inflate(META.frames);
  Q = new Uint16Array(raw.buffer, raw.byteOffset, raw.byteLength/2);
  if(META.probes){
    const a=await inflate(META.probes.t), b=await inflate(META.probes.v);
    PRT=new Float32Array(a.buffer,a.byteOffset,a.byteLength/4); PRV=new Float32Array(b.buffer,b.byteOffset,b.byteLength/4);
  }
}catch(e){
  $('msg').textContent='This page needs a current browser (Chrome, Edge, Firefox or Safari 16.4 or newer): '+e;
  return;
}
$('msg').style.display='none'; $('panels').style.display='grid';
const PR=META.probes, HP=PR?968:600;
const PAL=['#0f766e','#b45309','#7c3aed','#d4537e','#378add','#639922','#e24b4a','#5f5e5a'];
if(!PR){$('probes').style.display='none';$('panels').classList.add('noprobe');}
const LUT=new Float64Array(65536);
for(let q=1;q<65536;q++) LUT[q]=Math.pow(10, LO+(q-1)/65534*(HI-LO));
const FOOT=new Set(META.foot.map(p=>p[0]+','+p[1]));
const idx=(il,ir,ic)=>((il-1)*NR+(ir-1))*NC+(ic-1);
const med=a=>a.length?a.slice().sort((x,y)=>x-y)[a.length>>1]:1;
const sel={layer:med(META.foot.map(p=>p[1]))||BB.ilay[0], row:med(META.foot.map(p=>p[0]))||BB.irow[0], column:1};
const LIM={layer:NL,row:NR,column:NC}, LAB={layer:'ILAY',row:'IROW',column:'ICOL'};
let fr=0, timer=null;
const fg=getComputedStyle(document.body).color;
const day=t=>t>=1440?(' ('+(t/1440).toFixed(2)+' d)'):'';

$('title').textContent=META.title+': '+NL+' layers x '+NR+' rows x '+NC+' columns';
$('sub').textContent=META.counts.fluid+' sand cells, '+META.counts.boundary+' boundary cells, '+META.counts.solid+' solid cells, '+META.foot.length+' open source faces, '+NF+' frame'+(NF>1?'s':'');
$('vmax').value=Number(META.vmax.toPrecision(3));
$('tsl').max=NF-1;
if(NF<2){$('tsl').disabled=true;$('play').disabled=true;$('speed').disabled=true;}

// ---- 3D domain ----
const x0=BB.icol[0]-.5,x1=BB.icol[1]+.5,y0=BB.irow[0]-.5,y1=BB.irow[1]+.5,z0=BB.ilay[0]-.5,z1=BB.ilay[1]+.5;
const E=[[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],[x0,y0,z0],null,[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1],[x0,y0,z1],null,
 [x0,y0,z0],[x0,y0,z1],null,[x1,y0,z0],[x1,y0,z1],null,[x1,y1,z0],[x1,y1,z1],null,[x0,y1,z0],[x0,y1,z1]];
const g=(i)=>E.map(p=>p?p[i]:null);
const tr=[{type:'scatter3d',mode:'lines',x:g(0),y:g(1),z:g(2),line:{color:fg,width:3},name:'sand box',hoverinfo:'skip',showlegend:false}];
if(META.foot.length){
  const fx=META.foot.map(p=>p[0]), fy=META.foot.map(p=>p[1]);
  const a0=Math.min(...fx)-.5,a1=Math.max(...fx)+.5,b0=Math.min(...fy)-.5,b1=Math.max(...fy)+.5,zt=-1.5;
  tr.push({type:'mesh3d',x:[zt,zt,zt,zt,.5,.5,.5,.5],y:[a0,a1,a1,a0,a0,a1,a1,a0],z:[b0,b0,b1,b1,b0,b0,b1,b1],
    i:[0,0,4,4,0,0,1,1,2,2,3,3],j:[1,2,5,6,1,5,2,6,3,7,0,4],k:[2,3,6,7,5,4,6,5,7,6,4,7],color:'#b45309',opacity:.85,flatshading:true,name:'source',hoverinfo:'name',showlegend:true});
}
const KN={1:['membrane','#8a8f98'],2:['hole','#e24b4a'],3:['closed','#111111']};
for(const k of [1,2,3]){
  const p=META.faces.filter(f=>f[2]===k);
  if(p.length) tr.push({type:'scatter3d',mode:'markers',x:p.map(_=>.55),y:p.map(f=>f[0]),z:p.map(f=>f[1]),marker:{size:3,color:KN[k][1],symbol:'square'},name:KN[k][0],hoverinfo:'name'});
}
const bx=[],by=[],bz=[],bc=[];
for(let il=1;il<=NL;il++)for(let ir=1;ir<=NR;ir++)for(let ic=1;ic<=NC;ic++){const c=IDOM[idx(il,ir,ic)]; if(c!==1){bx.push(ic);by.push(ir);bz.push(il);bc.push(c===0?'#555555':'#7aa7d9');}}
if(PR){
  const pl=PR.loc.map((l,k)=>l?{l,k,n:PR.names[k]}:null).filter(x=>x);
  if(pl.length) tr.push({type:'scatter3d',mode:pl.length<=12?'markers+text':'markers',x:pl.map(o=>o.l[2]),y:pl.map(o=>o.l[1]),z:pl.map(o=>o.l[0]),text:pl.map(o=>o.n),
    textposition:'top center',textfont:{size:11,color:fg},marker:{size:7,color:pl.map(o=>PAL[o.k%PAL.length]),symbol:'diamond',line:{color:fg,width:1}},
    name:'probe cells',hovertemplate:'probe %{text}<br>ILAY %{z}, IROW %{y}, ICOL %{x}<extra></extra>'});
}
const iB=tr.length; tr.push({type:'scatter3d',mode:'markers',x:bx,y:by,z:bz,marker:{size:2,color:bc,opacity:.35},name:'boundary / solid cells',hoverinfo:'skip',visible:false});
const iP=tr.length; tr.push({type:'mesh3d',x:[0,0,0,0],y:[0,0,0,0],z:[0,0,0,0],i:[0,0],j:[1,2],k:[2,3],color:'#0f766e',opacity:.45,name:'chosen plane',hoverinfo:'skip',showlegend:true});
Plotly.newPlot('scene',tr,{paper_bgcolor:'rgba(0,0,0,0)',font:{color:fg},margin:{l:0,r:0,t:30,b:0},height:600,legend:{x:0,y:1},
  title:{text:'domain: x = ICOL (distance from the membrane), y = IROW, z = ILAY',font:{size:13}},
  scene:{xaxis:{title:'ICOL',range:[-1.5,x1+.5]},yaxis:{title:'IROW'},zaxis:{title:'ILAY'},aspectmode:'data',camera:{eye:{x:1.7,y:-1.7,z:1.0}}}},{responsive:true});
function movePlane(){
  const t=$('ptype').value,k=sel[t]; let X,Y,Z;
  if(t==='layer'){X=[x0,x1,x1,x0];Y=[y0,y0,y1,y1];Z=[k,k,k,k];}
  else if(t==='row'){X=[x0,x1,x1,x0];Y=[k,k,k,k];Z=[z0,z0,z1,z1];}
  else{X=[k,k,k,k];Y=[y0,y1,y1,y0];Z=[z0,z0,z1,z1];}
  Plotly.restyle('scene',{x:[X],y:[Y],z:[Z]},[iP]);
}

// ---- 2D plane ----
function plane(t,k,f){
  const base=f*NCELL,z=[];let xs=[],ys=[],xl,yl;
  const val=i=>IDOM[i]===1?LUT[Q[base+i]]:null;
  if(t==='layer'){
    xs=[0];for(let c=1;c<=NC;c++)xs.push(c);for(let r=1;r<=NR;r++)ys.push(r);xl='ICOL (0 = source cell)';yl='IROW';
    for(let r=1;r<=NR;r++){const row=[FOOT.has(r+','+k)?META.cm[f]:null];for(let c=1;c<=NC;c++)row.push(val(idx(k,r,c)));z.push(row);}
  }else if(t==='row'){
    xs=[0];for(let c=1;c<=NC;c++)xs.push(c);for(let l=1;l<=NL;l++)ys.push(l);xl='ICOL (0 = source cell)';yl='ILAY';
    for(let l=1;l<=NL;l++){const row=[FOOT.has(k+','+l)?META.cm[f]:null];for(let c=1;c<=NC;c++)row.push(val(idx(l,k,c)));z.push(row);}
  }else{
    for(let r=1;r<=NR;r++)xs.push(r);for(let l=1;l<=NL;l++)ys.push(l);xl='IROW';yl='ILAY';
    for(let l=1;l<=NL;l++){const row=[];for(let r=1;r<=NR;r++)row.push(val(idx(l,r,k)));z.push(row);}
  }
  return {xs,ys,z,xl,yl};
}
const NAME={layer:'Top view (MODFLOW xy): ILAY = ',row:'Row section (MODFLOW xz): IROW = ',column:'Column plane (MODFLOW yz): ICOL = '};
function probeMarks(t,k){          // the probe cells that lie on the plane shown
  if(!PR) return [];
  const x=[],y=[],c=[],n=[];
  PR.loc.forEach((l,j)=>{ if(!l) return; const [il,ir,ic]=l;
    if(t==='layer'&&il===k){x.push(ic);y.push(ir);} else if(t==='row'&&ir===k){x.push(ic);y.push(il);} else if(t==='column'&&ic===k){x.push(ir);y.push(il);} else return;
    c.push(PAL[j%PAL.length]);n.push(PR.names[j]); });
  if(!x.length) return [];
  return [{type:'scatter',mode:'markers+text',x:x,y:y,text:n,textposition:'top center',textfont:{size:11,color:'#ffffff'},
    marker:{size:11,color:c,symbol:'diamond',line:{color:'#ffffff',width:2}},showlegend:false,hovertemplate:'probe %{text}<extra></extra>'}];
}
function draw(){
  const t=$('ptype').value,k=sel[t],p=plane(t,k,fr),log=$('scale').value==='log';
  let vmax=parseFloat($('vmax').value); if(!(vmax>0)) vmax=META.vmax;
  const vmin=vmax*1e-4, f=v=>v===null?null:(log?Math.log10(Math.max(v,vmin)):v);
  const zz=p.z.map(r=>r.map(f));
  const cb=log?{tickvals:[-4,-3,-2,-1,0].map(d=>Math.log10(vmax)+d),ticktext:[-4,-3,-2,-1,0].map(d=>(vmax*Math.pow(10,d)).toPrecision(2)),title:{text:'concentration'}}:{title:{text:'concentration'}};
  const trace={type:'heatmap',x:p.xs,y:p.ys,z:zz,customdata:p.z,colorscale:'Viridis',zmin:log?Math.log10(vmin):0,zmax:log?Math.log10(vmax):vmax,
    zsmooth:false,hoverongaps:false,colorbar:cb,hovertemplate:p.xl.split(' ')[0]+' %{x}, '+p.yl+' %{y}<br>C = %{customdata:.4g}<extra></extra>'};
  Plotly.react('plane2d',[trace,...probeMarks(t,k)],{paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'#c8c8c8',font:{color:fg},height:HP,margin:{l:55,r:10,t:40,b:50},
    title:{text:NAME[t]+k+' &nbsp; minute '+META.minutes[fr]+day(META.minutes[fr])+', source = '+META.cm[fr].toPrecision(4),font:{size:13}},
    xaxis:{title:p.xl,constrain:'domain',range:t==='column'?[.5,NR+.5]:[-.5,NC+.5]},
    yaxis:{title:p.yl,scaleanchor:'x',constrain:'domain',range:t==='layer'?[.5,NR+.5]:[.5,NL+.5]}},{responsive:true});
  $('tlab').textContent='minute '+META.minutes[fr]+day(META.minutes[fr]);
  markTime();
}
function syncPlane(){
  const t=$('ptype').value; $('plab').textContent=LAB[t];
  for(const id of ['pidx','pnum']){$(id).max=LIM[t];$(id).value=sel[t];}
  movePlane(); draw();
}
$('ptype').onchange=syncPlane;
$('pidx').oninput=()=>{sel[$('ptype').value]=+$('pidx').value;$('pnum').value=$('pidx').value;movePlane();draw();};
$('pnum').onchange=()=>{let v=Math.max(1,Math.min(LIM[$('ptype').value],Math.round(+$('pnum').value||1)));sel[$('ptype').value]=v;$('pnum').value=v;$('pidx').value=v;movePlane();draw();};
$('tsl').oninput=()=>{fr=+$('tsl').value;draw();};
$('scale').onchange=()=>{draw();probeScale();}; $('vmax').onchange=draw;
$('showbnd').onchange=()=>Plotly.restyle('scene',{visible:$('showbnd').checked},[iB]);
function step(){fr=(fr+1)%NF;$('tsl').value=fr;draw();}
function stop(){if(timer){clearInterval(timer);timer=null;} $('play').textContent='Play';}
$('play').onclick=()=>{if(timer){stop();return;} $('play').textContent='Pause';timer=setInterval(step,+$('speed').value);};
$('speed').onchange=()=>{if(timer){clearInterval(timer);timer=setInterval(step,+$('speed').value);}};
window.__viewer={sel,get fr(){return fr;},setFrame:i=>{fr=i;$('tsl').value=i;draw();},NF};

// ---- probes: concentration against time ----
function markTime(){ if(PR) Plotly.relayout('probes',{'shapes[0].x0':META.minutes[fr],'shapes[0].x1':META.minutes[fr]}); }
function probeScale(){ if(PR) Plotly.relayout('probes',{'yaxis.type':$('scale').value==='log'?'log':'linear'}); }
if(PR){
  const NP=PR.names.length, N=PR.n, ptr=[];
  const fi=META.minutes.map(t=>{let a=0,b=N-1;while(b-a>1){const m=(a+b)>>1;if(PRT[m]<=t)a=m;else b=m;}return Math.abs(PRT[a]-t)<=Math.abs(PRT[b]-t)?a:b;});
  for(let k=0;k<NP;k++){
    const y=new Float32Array(N); for(let j=0;j<N;j++) y[j]=PRV[j*NP+k];
    const c=PAL[k%PAL.length], nm=PR.names[k], ht=nm+': %{y:.4g} at minute %{x}<extra></extra>';
    ptr.push({type:'scattergl',mode:'lines',x:PRT,y:y,name:nm,legendgroup:nm,line:{color:c,width:1.6},hovertemplate:ht});
    ptr.push({type:'scatter',mode:'markers',x:fi.map(j=>PRT[j]),y:fi.map(j=>y[j]),name:nm,legendgroup:nm,showlegend:false,marker:{color:c,size:7},hovertemplate:ht});
  }
  Plotly.newPlot('probes',ptr,{paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{color:fg},height:360,margin:{l:60,r:10,t:36,b:46},
    title:{text:'probes: concentration in time (dots = frames of the animation)',font:{size:13}},
    xaxis:{title:'time (min)',zeroline:false},yaxis:{title:'concentration',type:$('scale').value==='log'?'log':'linear',exponentformat:'power'},
    legend:{orientation:'h',y:-0.25},hovermode:'closest',
    shapes:[{type:'line',xref:'x',yref:'paper',x0:META.minutes[0],x1:META.minutes[0],y0:0,y1:1,line:{color:fg,width:1,dash:'dot'}}]},{responsive:true});
  $('probelab').style.display='flex';
  const sel=$('probesel'); sel.add(new Option('all probes (' + NP + ')','all'));
  PR.names.forEach((n,k)=>sel.add(new Option(n,String(k))));
  sel.onchange=()=>{const v=sel.value; Plotly.restyle('probes',{visible:ptr.map((_,i)=>v==='all'||String(i>>1)===v)});};
}
syncPlane();
})();
</script></body></html>
'''


if __name__ == '__main__':
    main()
