import numpy as np, trimesh
from drr import LO,P,shape
lab=np.zeros(shape,np.uint8)
for k,f in [(1,'stl/FMA24483.stl'),(2,'stl/FMA24498.stl')]:
    m=trimesh.load(f); vg=m.voxelized(pitch=P).fill(); mask=vg.matrix
    i0=np.round((vg.transform[:3,3]-LO)/P).astype(int)
    sl=tuple(slice(i0[a],i0[a]+mask.shape[a]) for a in range(3))
    sub=lab[sl]; sub[mask[:sub.shape[0],:sub.shape[1],:sub.shape[2]]]=k
np.save('lab.npy',lab); print('ok')
