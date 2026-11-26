import sys; sys.argv=['x']
from drr import drr
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import numpy as np
def enh(im):
    a=np.asarray(im).astype(float)
    b=np.asarray(im.filter(ImageFilter.GaussianBlur(6))).astype(float)
    c=np.clip(a+1.2*(a-b),0,255)
    lo,hi=np.percentile(c[c>20],[2,99.5]) if (c>20).any() else (0,255)
    c=np.clip((c-lo)/(hi-lo),0,1)*255
    return Image.fromarray(c.astype(np.uint8))
if __name__=="__main__":
    ims=[]
    for inv in [0,10,20,30,40]:
        im=enh(drr(inv=inv,Y=(-50,70),Z=(-45,55)))
        im.save(f'inv{inv}.png'); ims.append((inv,im))
    W,H=ims[0][1].size
    sheet=Image.new('L',(W*len(ims),H+30),255); d=ImageDraw.Draw(sheet)
    for k,(inv,im) in enumerate(ims):
        sheet.paste(im,(k*W,30)); d.text((k*W+10,8),f'inv {inv}',fill=0)
    sheet.save('sheet_inv.png')
