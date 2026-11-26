import numpy as np, sys
from scipy import ndimage
import drr
from drr import Rx,Ry,F,C0,LO,P,r
lab=np.load('lab.npy')
T=(lab==1).astype(np.float32); Cc=(lab==2).astype(np.float32)
def proj(df,inv,tilt,cc=0,px=0.4,Y=(-50,70),Z=(-45,55)):
    R=Rx(df)@Ry(inv)
    d=np.array([np.cos(r(tilt)),np.sin(r(tilt)),0.0]); c,s=np.cos(r(cc)),np.sin(r(cc)); d=np.array([d[0]*c,d[1]*c,s]); d/=np.linalg.norm(d)
    ys=np.arange(Y[0],Y[1],px); zs=np.arange(Z[1],Z[0],-px); ts=np.arange(0,140,P)
    out=np.zeros((2,len(zs),len(ys)),np.float32)
    for i,z in enumerate(zs):
        Pd=np.stack([np.full_like(ys,45.0),ys,np.full_like(ys,z)],1)
        q=(Pd[:,None,:]-ts[None,:,None]*d).reshape(-1,3)@R
        w=q@F+C0; idx=((w-LO)/P).T
        for k,V in enumerate([T,Cc]):
            out[k,i]=ndimage.map_coordinates(V,idx,order=1).reshape(len(ys),len(ts)).sum(1)*P
    return out
if __name__=='__main__':
    for tilt in [30]:
        for inv in range(0,45,5):
            o=proj(14,inv,tilt)
            ov=((o[0]>1.0)&(o[1]>1.0)).sum()*0.16
            print(f'tilt{tilt} inv{inv:2d} overlap {ov:7.0f} mm2', flush=True)
