# Tiled EDSR x4 super-resolution with overlap blending
import cv2, numpy as np, sys, time
model, src, dst = sys.argv[1:4]
sr = cv2.dnn_superres.DnnSuperResImpl_create()
sr.readModel(model); sr.setModel('edsr', 4)
img = cv2.imread(src)
H, W = img.shape[:2]; S = 4
T, P = 160, 16  # tile size, padding
out = np.zeros((H*S, W*S, 3), np.float32)
t0 = time.time(); n = 0
ys = list(range(0, H, T)); xs = list(range(0, W, T))
for y in ys:
    for x in xs:
        y0, x0 = max(0, y-P), max(0, x-P)
        y1, x1 = min(H, y+T+P), min(W, x+T+P)
        up = sr.upsample(img[y0:y1, x0:x1]).astype(np.float32)
        ty1, tx1 = min(H, y+T), min(W, x+T)
        out[y*S:ty1*S, x*S:tx1*S] = up[(y-y0)*S:(y-y0+ty1-y)*S, (x-x0)*S:(x-x0+tx1-x)*S]
        n += 1
    print(f'row {y} done, {n}/{len(ys)*len(xs)} tiles, {time.time()-t0:.0f}s', flush=True)
cv2.imwrite(dst, np.clip(out, 0, 255).astype(np.uint8))
print('done', time.time()-t0)
