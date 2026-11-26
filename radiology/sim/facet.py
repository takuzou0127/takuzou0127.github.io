import numpy as np
from overlap import proj
def thick(o,c0=250,c1=360):
    T,C=o[0]>0.8,o[1]>0.8; H=T.shape[0]; vals=[]
    for c in range(c0,c1):
        if T[:,c].any() and C[:,c].any():
            tb=H-1-np.argmax(T[::-1,c]); ct=np.argmax(C[:,c]); vals.append((tb-ct)*0.25)
    v=np.array(vals); return np.median(v), np.percentile(v,10), np.percentile(v,90)
if __name__=='__main__':
    for inv in range(0,45,5):
        m,a,b=thick(proj(14,inv,30,px=0.25)); print(f'inv{inv:2d} 重なり中央値 {m:+.1f}mm (10-90%: {a:+.1f}〜{b:+.1f})',flush=True)
    for cc in [-6,-3,3,6]:
        m,a,b=thick(proj(14,20,30,cc=cc,px=0.25)); print(f'inv20 cc{cc:+d} {m:+.1f}mm ({a:+.1f}〜{b:+.1f})',flush=True)
    for t in [20,40]:
        m,a,b=thick(proj(14,20,t,px=0.25)); print(f'inv20 tilt{t} {m:+.1f}mm ({a:+.1f}〜{b:+.1f})',flush=True)
