import numpy as np, cv2, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from order import ORDER
W = os.path.dirname(os.path.abspath(__file__)); L = f'{W}/layers'
comp = np.load(f'{L}/_plate.npy').astype(np.float32)
for n, _ in [o for o in ORDER if o[0] != 'infobox_full']:
    x = np.load(f'{L}/{n}.npy').astype(np.float32); a = x[..., 3:]/255
    comp = comp*(1 - a) + x[..., :3]*a
I4 = cv2.imread(f'{W}/poster_x4.png')[:, :, ::-1].astype(np.float32)
d = np.abs(comp - I4).max(2)
mse = ((comp - I4)**2).mean(); print('PSNR', 10*np.log10(255**2/mse), 'max', d.max(), 'p99.9', np.percentile(d, 99.9), '>20px', (d > 20).sum())
cv2.imwrite(f'{W}/v_comp.png', cv2.resize(comp, (1024, 1536), interpolation=cv2.INTER_AREA)[:, :, ::-1].astype(np.uint8))
dm = cv2.resize(d, (1024, 1536), interpolation=cv2.INTER_AREA)
cv2.imwrite(f'{W}/v_diff.png', np.clip(dm*8, 0, 255).astype(np.uint8))
for k in ['_plate', '_clean_bg']:
    cv2.imwrite(f'{W}/v{k}.png', cv2.resize(np.load(f'{L}/{k}.npy'), (1024, 1536), interpolation=cv2.INTER_AREA)[:, :, ::-1])
