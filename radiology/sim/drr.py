import numpy as np, trimesh, glob, sys, os
from scipy import ndimage
from PIL import Image

r = np.radians
P = 0.4  # voxel pitch mm
LO = np.array([40.0, -130.0, -6.0]); HI = np.array([142.0, 0.0, 110.0])
shape = np.ceil((HI - LO) / P).astype(int)

def build():
    vol = np.zeros(shape, np.float32)
    for f in sorted(glob.glob('stl/*.stl')):
        m = trimesh.load(f)
        if m.bounds[1, 2] > 150:  # tibia/fibula: clip
            m = m.slice_plane([0, 0, 108], [0, 0, -1], cap=True)
        if m.bounds[0, 1] < -135 and m.bounds[1, 1] < -100:  # metatarsals fully in front: keep only bases inside box anyway
            pass
        vg = m.voxelized(pitch=P).fill()
        mask = vg.matrix
        org = vg.transform[:3, 3]
        idx0 = np.round((org - LO) / P).astype(int)
        # cortex: distance inside
        dist = ndimage.distance_transform_edt(mask) * P
        dens = np.where(dist <= 1.0, 2.6, 1.0).astype(np.float32) * mask
        sl_src = []; sl_dst = []
        for a in range(3):
            s0 = idx0[a]; s1 = s0 + mask.shape[a]
            d0 = max(s0, 0); d1 = min(s1, shape[a])
            if d1 <= d0: break
            sl_dst.append(slice(d0, d1)); sl_src.append(slice(d0 - s0, d1 - s0))
        else:
            vol[tuple(sl_dst)] = np.maximum(vol[tuple(sl_dst)], dens[tuple(sl_src)])
    np.save('vol.npy', vol)
    return vol

vol = np.load('vol.npy') if os.path.exists('vol.npy') else build()

a = r(21.2)
F = np.array([[np.cos(a), np.sin(a), 0], [np.sin(a), -np.cos(a), 0], [0, 0, 1.0]])  # rows: lateral, toe, up
C0 = np.array([80.7, -48.1, 42.2])  # posterior facet center

def Rx(t): t = r(t); c, s = np.cos(t), np.sin(t); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def Ry(t): t = r(t); c, s = np.cos(t), np.sin(t); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])

def drr(df=14, inv=20, tilt=30, cc=0.0, px=0.25, Y=(-55, 65), Z=(-50, 50), out=None):
    """cc: extra tube tilt toward dorsum(+)/sole(-) (= 頭側+/足側-) in degrees"""
    R = Rx(df) @ Ry(inv)
    d = np.array([np.cos(r(tilt)), np.sin(r(tilt)), 0.0])
    d = Rx(0) @ d
    # extra tilt about the toe axis' perpendicular: rotate d toward +z
    c, s = np.cos(r(cc)), np.sin(r(cc))
    d = np.array([d[0] * c, d[1] * c, s]) if cc else d
    d = d / np.linalg.norm(d)
    ys = np.arange(Y[0], Y[1], px); zs = np.arange(Z[1], Z[0], -px)
    img = np.zeros((len(zs), len(ys)), np.float32)
    ts = np.arange(0, 140, P)
    XD = 45.0
    RT = R.T; FT = F.T
    for i, z in enumerate(zs):
        Pd = np.stack([np.full_like(ys, XD), ys, np.full_like(ys, z)], 1)  # room coords on detector
        pts = Pd[:, None, :] - ts[None, :, None] * d[None, None, :]
        q = pts.reshape(-1, 3) @ RT.T  # foot frame: f = R^T q
        w = q @ FT.T + C0  # world
        idx = ((w - LO) / P).T
        v = ndimage.map_coordinates(vol, idx, order=1, mode='constant', cval=0)
        img[i] = v.reshape(len(ys), len(ts)).sum(1) * P
    I = 1 - np.exp(-img * 0.045)
    I = (I / max(I.max(), 1e-6))
    im = Image.fromarray((np.clip(I, 0, 1) ** 0.9 * 255).astype(np.uint8))
    if out: im.save(out)
    return im

if __name__ == '__main__':
    args = dict(a.split('=') for a in sys.argv[2:])
    drr(**{k: float(v) for k, v in args.items()}, out=sys.argv[1])
    print('saved', sys.argv[1])
