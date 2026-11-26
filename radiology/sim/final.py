import numpy as np
from PIL import Image
from scipy import ndimage
from overlap import proj
from series import enh
from drr import drr
box=(120,40,460,330)
for inv in [0]:
    im=enh(drr(inv=inv,Y=(-50,70),Z=(-45,55))).convert('RGB')
    im.crop(box).resize(((box[2]-box[0])*2,(box[3]-box[1])*2),Image.LANCZOS).save(f'f_raw{inv}.png')
    o=proj(14,inv,30,px=0.25); a=np.asarray(im).copy()
    for M,col in [(o[0]>0.8,(255,70,70)),(o[1]>0.8,(70,150,255))]:
        e=M&~ndimage.binary_erosion(M,iterations=2); a[e]=col
    Image.fromarray(a).crop(box).resize(((box[2]-box[0])*2,(box[3]-box[1])*2),Image.LANCZOS).save(f'f_ol{inv}.png')
print('ok')
