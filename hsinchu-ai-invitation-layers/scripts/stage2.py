"""Decompose the poster into layers at 4x (4096x6144 = 300dpi @ 34.7x52.0cm)."""
import numpy as np, cv2, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from layers_cfg import *
W = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
S = 4
t0 = time.time()
def log(*a): print(f'[{time.time()-t0:5.0f}s]', *a, flush=True)

I1 = cv2.imread(f'{W}/poster_src.png')[:, :, ::-1].astype(np.float32)
I4 = cv2.imread(f'{W}/poster_x4.png')[:, :, ::-1].astype(np.float32)
H, Wd = I1.shape[:2]; H4, W4 = H*S, Wd*S
assert I4.shape[:2] == (H4, W4)
r1, g1, b1 = I1[..., 0], I1[..., 1], I1[..., 2]
lum1 = 0.299*r1 + 0.587*g1 + 0.114*b1
cream = np.median(I1[20:60, 20:300].reshape(-1, 3), 0)

# ---------- geometry helpers (1x pixel-index coords -> 4x) ----------
yy4, xx4 = np.mgrid[0:H4, 0:W4].astype(np.float32)
yy1, xx1 = np.mgrid[0:H, 0:Wd].astype(np.float32)
def to4(v): return (v + 0.5)*S - 0.5
def circle_alpha(cx, cy, rad, s=1, xx=None, yy=None):
    d = np.hypot(xx - (cx if s == 1 else to4(cx)), yy - (cy if s == 1 else to4(cy)))
    return np.clip(rad*s - d + 0.5, 0, 1), d
def smoothstep(e0, e1, x):
    t = np.clip((x - e0)/(e1 - e0), 0, 1); return t*t*(3 - 2*t)
def up_mask(m1, blur=0):
    m = cv2.resize(m1.astype(np.float32), (W4, H4), interpolation=cv2.INTER_LINEAR)
    if blur: m = cv2.GaussianBlur(m, (0, 0), blur)
    return m

def pushpull(img, valid):
    pyr = [(img*valid[..., None], valid)]
    while min(pyr[-1][1].shape) > 4:
        im, w = pyr[-1]
        pyr.append((cv2.pyrDown(im), cv2.pyrDown(w)))
    im, w = pyr[-1]
    res = im/np.maximum(w, 1e-6)[..., None]
    for im, w in reversed(pyr[:-1]):
        upr = cv2.pyrUp(res, dstsize=(w.shape[1], w.shape[0]))
        k = np.clip(w*4, 0, 1)[..., None]
        res = (im/np.maximum(w, 1e-6)[..., None])*k + upr*(1 - k)
    return res
# ---------- 1. core masks for text / lines at 1x ----------
gx, gy, gr = GLOBE
in_globe1 = np.hypot(xx1 - gx, yy1 - gy) < gr
def boxmask(boxes):
    m = np.zeros((H, Wd), bool)
    for x0, y0, x1, y1 in boxes: m[y0:y1, x0:x1] = True
    return m
dist_cream1 = np.linalg.norm(I1 - cream, axis=2)
core, region = {}, {}
for name, (kind, boxes) in ELEMENTS.items():
    bm = boxmask(boxes)
    if kind == 'navy':
        c = (b1 > r1) & np.where(in_globe1, lum1 < 80, lum1 < 125)
    elif kind == 'blue':
        c = (dist_cream1 > 90) & (b1 > r1 + 20)
    else:
        c = ((r1 - b1) > 30) & (lum1 < 235) & (r1 > g1)
    c &= bm
    if kind == 'navy':   # hysteresis: grow into weaker dark pixels near strokes (catches faint serif tips over the globe)
        weak = ((b1 > r1) & (lum1 < 135) & bm).astype(np.uint8)
        k3 = np.ones((3, 3), np.uint8); g = c.astype(np.uint8)
        for _ in range(4): g = cv2.dilate(g, k3) & weak
        c = c | (g > 0)
    core[name] = c
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    reg = cv2.dilate(c.astype(np.uint8), k) > 0
    if name in ('rules', 'divider'):     # thin lines on plain cream: take the whole strip
        reg = bm.copy()
    region[name] = reg & bm
icon_mask1 = np.zeros((H, Wd), bool)
for cx, cy, rad in list(BADGES.values()) + list(GOLD_ICONS.values()):
    icon_mask1 |= np.hypot(xx1 - cx, yy1 - cy) < rad + 2.5
text_mask1 = np.zeros((H, Wd), bool)
for v in region.values(): text_mask1 |= v
inpaint_mask1 = text_mask1 | icon_mask1
log('masks ready', int(text_mask1.sum()), int(icon_mask1.sum()))

# ---------- 2. text-free background at 1x (Telea), merged into 4x ----------
B1 = cv2.inpaint(np.clip(I1, 0, 255).astype(np.uint8)[:, :, ::-1], inpaint_mask1.astype(np.uint8)*255, 6, cv2.INPAINT_TELEA)[:, :, ::-1].astype(np.float32)
# on the plain cream paper, Telea smears compression ringing into ghosts: use a smooth membrane fill instead
k9 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
big1 = cv2.dilate(inpaint_mask1.astype(np.uint8), k9) > 0
Bpp1 = cv2.GaussianBlur(pushpull(I1, (~big1).astype(np.float32)).astype(np.float32), (0, 0), 2.0)
plain1 = (np.linalg.norm(Bpp1 - cream, axis=2) < 14) & ~icon_mask1
wpl = cv2.GaussianBlur((big1 & plain1).astype(np.float32), (0, 0), 1.5)[..., None]
B1 = B1*(1 - wpl) + Bpp1*wpl
inpaint_mask1 = inpaint_mask1 | (big1 & plain1)
B1up = cv2.resize(B1, (W4, H4), interpolation=cv2.INTER_CUBIC)
M4 = up_mask(cv2.dilate(inpaint_mask1.astype(np.uint8), np.ones((3, 3), np.uint8)), blur=2.0)
M4 = np.clip(M4*1.5, 0, 1)[..., None]
B4 = I4*(1 - M4) + B1up*M4
# gently clean WebP block noise on the flat cream paper (normalized blur restricted to cream pixels)
cz = (np.linalg.norm(cv2.GaussianBlur(B4, (0, 0), 3) - cream, axis=2) < 9).astype(np.float32)
cz = cv2.erode(cz, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
num = cv2.GaussianBlur(B4*cz[..., None], (0, 0), 6); den = cv2.GaussianBlur(cz, (0, 0), 6)
sm = num/np.maximum(den, 1e-4)[..., None]
wcz = cv2.GaussianBlur(cz, (0, 0), 4)[..., None]
B4 = B4*(1 - wcz) + sm*wcz
del num, sm
log('background inpainted')

# ---------- 3. text / line layers: unblend I4 against B4 ----------
def save_layer(name, rgb, al):
    np.save(f'{OUT}/{name}.npy', np.dstack([np.clip(rgb, 0, 255), np.clip(al*255 + 0.5, 0, 255)]).astype(np.uint8))
class _Saver(dict):
    def __setitem__(self, k, v): save_layer(k, *v)
layers = _Saver()
def unblend(name):
    reg4 = up_mask(region[name]) > 0.01
    ys, xs = np.where(reg4)
    y0, y1, x0, x1 = ys.min(), ys.max()+1, xs.min(), xs.max()+1
    Ii, Bi, Ri = I4[y0:y1, x0:x1], B4[y0:y1, x0:x1], reg4[y0:y1, x0:x1]
    # robust ink colour: strongest-contrast core pixels at 1x
    c1 = core[name]
    d = np.linalg.norm(I1[c1] - B1[c1], axis=1)
    F = np.median(I1[c1][d >= np.percentile(d, 70)], axis=0)
    FB = F - Bi
    a = (( Ii - Bi)*FB).sum(2) / np.maximum((FB*FB).sum(2), 1e-3)
    a = np.clip(a, 0, 1)*Ri
    a[a < 0.04] = 0
    a = np.clip((a - 0.04)/0.96, 0, 1)
    # colour: recover true ink colour where fairly opaque, fall back to F at soft edges
    est = Bi + (Ii - Bi)/np.maximum(a, 1e-3)[..., None]
    w = smoothstep(0.35, 0.8, a)[..., None]
    col = np.clip(F*(1 - w) + est*w, 0, 255)
    rgb = np.zeros((H4, W4, 3), np.float32); al = np.zeros((H4, W4), np.float32)
    rgb[y0:y1, x0:x1] = col; al[y0:y1, x0:x1] = a
    log(name, 'ink', F.round(), 'bbox', (x0, y0, x1, y1))
    return rgb, al
for name in ELEMENTS: layers[name] = unblend(name)

# ---------- 4. circular icons ----------
def disc_layer(cx, cy, rad, edge_from):
    pad = int(rad*S + 12)
    X0, Y0 = int(to4(cx) - pad), int(to4(cy) - pad)
    X1, Y1 = min(W4, int(to4(cx) + pad)), min(H4, int(to4(cy) + pad))
    xx, yy = xx4[Y0:Y1, X0:X1], yy4[Y0:Y1, X0:X1]
    a, d = circle_alpha(cx, cy, rad, S, xx, yy)
    patch = I4[Y0:Y1, X0:X1].copy()
    ring = (d > (rad - edge_from)*S) & (d < rad*S - 4)
    rim = np.median(patch[ring], 0)
    band = d >= rad*S - 3
    patch[band] = rim                    # avoid background bleeding into the AA edge
    rgb = np.zeros((H4, W4, 3), np.float32); al = np.zeros((H4, W4), np.float32)
    rgb[Y0:Y1, X0:X1] = patch; al[Y0:Y1, X0:X1] = a
    return rgb, al
for n, (cx, cy, rad) in GOLD_ICONS.items(): layers['icon_' + n] = disc_layer(cx, cy, rad, 3)
for n, (cx, cy, rad) in BADGES.items():     layers['badge_' + n] = disc_layer(cx, cy, rad, 2.5)
log('icons done')

# ---------- 5. globe ----------
ga, _ = circle_alpha(gx, gy, gr + 1.5, S, xx4, yy4)
ga = cv2.GaussianBlur(ga, (0, 0), 2.0)
pts = np.array(GLOBE_CUT, np.float32)
cut_y = np.interp(np.arange(Wd), pts[:, 0], pts[:, 1])
cut_y4 = to4(np.interp((np.arange(W4) + 0.5)/S - 0.5, np.arange(Wd), cut_y))
f4 = GLOBE_CUT_FEATHER*S
ga *= 1 - smoothstep(cut_y4[None, :] - f4, cut_y4[None, :] + f4, yy4)
layers['globe'] = (B4, ga)
log('globe done')

# ---------- 6. info box base (clean rounded rectangle) + waves in front of it ----------
bx0, by0, bx1, by1, br = INFO_BOX
def rrect_sd(x0, y0, x1, y1, rad, xx, yy):
    # signed distance to a rounded rectangle, in 1x units
    cxm, cym = (x0 + x1)/2, (y0 + y1)/2
    hx, hy = (x1 - x0)/2 - rad, (y1 - y0)/2 - rad
    qx, qy = np.abs(xx - cxm) - hx, np.abs(yy - cym) - hy
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - rad
hw = INFO_BOX_STROKE/2
sd4 = rrect_sd(bx0, by0, bx1, by1, br, (xx4 + 0.5)/S - 0.5, (yy4 + 0.5)/S - 0.5)
sd1 = rrect_sd(bx0, by0, bx1, by1, br, xx1, yy1)
fill_a = np.clip((hw - sd4)*S + 0.5, 0, 1)
stroke_a = np.clip((hw - np.abs(sd4))*S + 0.5, 0, 1)
border_col = np.median(B4[(np.abs(sd4) < 0.35) & (yy4 < to4(1370))], 0)
box_fill = np.median(B1[1300:1330, 300:900].reshape(-1, 3), 0)
# smooth paper colour for the box interior
creamy1 = np.linalg.norm(B1 - box_fill, axis=2) < 10
valid1 = (sd1 < -2.5) & creamy1 & (yy1 < 1380)
fill1 = cv2.GaussianBlur(pushpull(B1, valid1.astype(np.float32)).astype(np.float32), (0, 0), 3)
fill4 = cv2.resize(fill1, (W4, H4), interpolation=cv2.INTER_CUBIC)
def box_layer(fade):
    st = stroke_a*(1 - smoothstep(to4(INFO_BOX_FADE[0]), to4(INFO_BOX_FADE[1]), yy4)) if fade else stroke_a
    rgb = fill4*(1 - st[..., None]) + border_col*st[..., None]
    return rgb, np.maximum(fill_a, st)
layers['infobox'] = box_layer(True)
layers['infobox_full'] = box_layer(False)
# waves / thin gold lines that pass in front of the box bottom
dist_fill = np.linalg.norm(B4 - fill4, axis=2)
fw_region = np.clip((hw + 1.5 - sd4)*S, 0, 1)*smoothstep(to4(FRONT_WAVE_TOP), to4(FRONT_WAVE_TOP + 8), yy4)
wave_a = smoothstep(4, 24, dist_fill)*fw_region
layers['front_waves'] = (B4, wave_a)
boxa = fill_a
log('info box done, fill', box_fill.round(), 'border', border_col.round())

# ---------- 7. background plate: fill what the globe / box cover ----------
cov4 = np.maximum(ga, boxa*(1 - wave_a))
cover1 = cv2.resize(cov4, (Wd, H), interpolation=cv2.INTER_AREA)
hole1 = cover1 > 0.02
fill1 = pushpull(B1, (~hole1).astype(np.float32))
fill4 = cv2.resize(fill1.astype(np.float32), (W4, H4), interpolation=cv2.INTER_CUBIC)
wfill = smoothstep(0.9, 0.999, cov4)[..., None]
plate = B4*(1 - wfill) + fill4*wfill
log('plate filled')

# ---------- 8. save ----------
np.save(f'{OUT}/_plate.npy', plate.astype(np.uint8))
np.save(f'{OUT}/_clean_bg.npy', np.clip(B4, 0, 255).astype(np.uint8))
log('saved')
