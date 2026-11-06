#!/usr/bin/env python3
"""A model of Sephiroth's up special trail / loop protocol (fighters/edge/edge.c edge_tr_*, weapons/trail.c from
tools/edge_trail_msc.py): the fighter's points and loop queries through his shared 4 - 6, the trail articles' crossing
tests and answers, run on a held Octaslash circle (2.2 a frame, 8 degrees a frame) with the articles updated after and
before him. Prints each fill's middle and radius and the circle's.

  python3 tools/edge_trail_sim.py
"""
import math
SEG=4.0; PER=15; PTS=16
def pack(x,y):
    ix=int((x+512)*2+0.5); iy=int((y+512)*2+0.5); return float(ix*2048+iy)
def unpack(v):
    c=int(v); ix=c//2048; return ix*0.5-512, (c-ix*2048)*0.5-512
def cross(a,b,c,d):
    ax,ay=a;bx,by=b;cx,cy=c;dx,dy=d
    d1=(bx-ax)*(cy-ay)-(by-ay)*(cx-ax); d2=(bx-ax)*(dy-ay)-(by-ay)*(dx-ax)
    d3=(dx-cx)*(ay-cy)-(dy-cy)*(ax-cx); d4=(dx-cx)*(by-cy)-(dy-cy)*(bx-cx)
    return ((d1>0 and d2<0) or (d1<0 and d2>0)) and ((d3>0 and d4<0) or (d3<0 and d4>0))
sh={4:0.0,5:0.0,6:0.0}; V={0:0.0,1:0.0,2:0.0,3:0.0,4:0.0,5:0.0}
arts=[]; fills=[]
class Art:
    def __init__(s):
        s.base=int(sh[6]); s.pts=[unpack(sh[5])]; s.seen=s.base; s.sp=s.pts[0]; s.stale=False; s.ans=0
    def tick(s):
        if s.stale: return
        v=sh[6]
        if v<0: s.stale=True; return
        if v-int(v)>0.25:
            code=int(v)
            if code==s.ans: return
            s.ans=code; st=code//512; cnt=code-st*512
            for k,(x,y) in enumerate(s.pts):
                if st<=s.base+k<st+cnt and (k>0 or s.base==1000): sh[5]+=x; sh[4]+=y
            return
        num=int(v)
        if num<=s.seen: return
        p=unpack(sh[5])
        if num==s.seen+1:
            k=0
            while k<len(s.pts)-1 and s.base+k+1<=num-2:
                if cross(s.sp,p,s.pts[k],s.pts[k+1]):
                    m=s.base+k; r=sh[4]
                    if r>-1000 or m>-r: sh[4]=-float(m)
                k+=1
        if num==s.base+len(s.pts) and len(s.pts)<PTS: s.pts.append(p)
        s.seen=num; s.sp=p
def point(p,n):
    sh[5]=p; sh[6]=float(n)
    if (n-1000)%PER==0: arts.append(Art())
def begin(x,y):
    sh[4]=0.0; V[0]=0; V[5]=0; V[1]=0; point(pack(x,y),1000)
def fill():
    n=V[2]; r=max(4,min(40,(n+1)*SEG/6.2832))
    c=(sh[5]/n, sh[4]/n); fills.append((c,r))
    sh[4]=0.0; sh[5]=V[3]; sh[6]=V[4]; V[5]=10; V[1]=V[4]
def step(x,y,last=False):
    if V[0]>0:
        V[0]-=1
        if V[0]<=0:
            fill()
            if last: sh[6]=-1
        return
    if sh[6]<1000: return
    if V[5]>0: V[5]-=1
    c=sh[4]; sh[4]=0.0; num=int(sh[6])
    if c<=-1000 and -c>=V[1] and V[5]<=0 and not last:
        m=int(-c); cnt=num-1-m
        if 3<=cnt<512:
            V[3]=sh[5]; V[4]=float(num); V[2]=cnt; sh[5]=0.0; sh[4]=0.0; sh[6]=(m+1)*512+cnt+0.5; V[0]=1; return
    lx,ly=unpack(sh[5]); d=(x-lx)**2+(y-ly)**2
    if d>=SEG*SEG or (last and d>=1): point(pack(x,y),num+1)
    if last: sh[6]=-1
for order in ('fighter_first','articles_first'):
    sh.update({4:0.0,5:0.0,6:0.0}); arts.clear(); fills.clear()
    x,y=0.0,50.0; ang=0.0; begin(x,y)
    for f in range(1,140):
        ang+=math.radians(8); x+=2.2*math.cos(ang); y+=2.2*math.sin(ang)
        if order=='articles_first':
            for a in arts: a.tick()
            step(x,y,f==139)
        else:
            step(x,y,f==139)
            for a in arts: a.tick()
    print(order, 'articles', len(arts), 'fills', [((round(c[0],1),round(c[1],1)),round(r,1)) for c,r in fills])
print('true circle centre', (0.0, 50.0+2.2/math.radians(8)), 'radius', round(2.2/math.radians(8),1))
