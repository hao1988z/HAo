import numpy as np, cv2, sys, os, time
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from psdutil import new_psd, add_group, add_layer
W = os.path.dirname(os.path.abspath(__file__)); L = f'{W}/layers'
OUT = sys.argv[1]
t0 = time.time()
def log(*a): print(f'[{time.time()-t0:5.0f}s]', *a, flush=True)

# (group, npy, name, slug, visible) bottom -> top
SPEC = [
    ('背景',     '_plate',        '背景_底圖',                 'background',      True),
    ('地球',     'globe',         '地球',                      'globe',           True),
    ('地球',     'badge_chip',    '地球_晶片圖示',             'badge-chip',      True),
    ('地球',     'badge_server',  '地球_伺服器圖示',           'badge-server',    True),
    ('地球',     'badge_cloud',   '地球_雲端圖示',             'badge-cloud',     True),
    ('地球',     'badge_people',  '地球_人群圖示',             'badge-people',    True),
    ('資訊框',   'infobox',       '資訊框_底框',               'infobox',         True),
    ('資訊框',   'infobox_full',  '資訊框_底框_完整版(備用)',  'infobox-full',    False),
    ('資訊框',   'front_waves',   '前景_資訊框前波浪',         'front-waves',     True),
    ('資訊框',   'divider',       '資訊框_分隔線',             'divider',         True),
    ('資訊框',   'icon_calendar', '資訊框_日曆圖示',           'icon-calendar',   True),
    ('資訊框',   'icon_location', '資訊框_地點圖示',           'icon-location',   True),
    ('資訊框',   'date',          '資訊框_日期文字',           'text-date',       True),
    ('資訊框',   'place',         '資訊框_地點文字',           'text-place',      True),
    ('資訊框',   'regards',       '資訊框_敬邀蒞臨指導',       'text-regards',    True),
    ('標題區',   'rules',         '裝飾_金色線條',             'gold-rules',      True),
    ('標題區',   'desc',          '文字_說明',                 'text-desc',       True),
    ('標題區',   'tagline',       '文字_副標題',               'text-tagline',    True),
    ('標題區',   'invitation',    '文字_INVITATION邀請函',     'text-invitation', True),
    ('標題區',   'press',         '文字_記者會',               'text-press',      True),
    ('標題區',   'title',         '文字_主標題',               'text-title',      True),
    ('標題區',   'county',        '文字_新竹縣政府',           'text-county',     True),
]
GROUP_SLUG = {'背景': 'background', '地球': 'globe', '資訊框': 'info-box', '標題區': 'headline'}
TEXT = {'date', 'place', 'regards', 'desc', 'tagline', 'invitation', 'press', 'title', 'county'}
DPI = (300, 300)
os.makedirs(f'{OUT}/PNG分層', exist_ok=True)

def load(n):
    x = np.load(f'{L}/{n}.npy')
    if x.shape[2] == 3: x = np.dstack([x, np.full(x.shape[:2], 255, np.uint8)])
    return x
def over(dst, x):
    a = x[..., 3:].astype(np.float32)/255
    return dst*(1 - a) + x[..., :3].astype(np.float32)*a

# ---- composites ----
comp = load('_plate')[..., :3].astype(np.float32); clean = comp.copy()
for _, n, *_r, vis in SPEC[1:]:
    if not vis: continue
    x = load(n); comp = over(comp, x)
    if n not in TEXT: clean = over(clean, x)
comp = np.clip(comp + 0.5, 0, 255).astype(np.uint8); clean = np.clip(clean + 0.5, 0, 255).astype(np.uint8)
H, Wd = comp.shape[:2]
Image.fromarray(clean).save(f'{OUT}/背景_去字完整版_300dpi.png', dpi=DPI, compress_level=6)
Image.fromarray(comp).resize((Wd//4, H//4), Image.LANCZOS).save(f'{OUT}/預覽_合成.jpg', quality=90)
log('composites saved')

# ---- PNGs (full canvas, so they stack in register) + PSD (cropped layers with offsets) ----
psd = new_psd(Image.fromarray(comp))
groups = {}
for i, (grp, n, name, slug, vis) in enumerate(SPEC):
    x = load(n)
    fname = f'{i:02d}_{name}_{slug}.png'.replace('(備用)', '_備用')
    if n == '_plate':
        im = Image.fromarray(x[..., :3]); im.save(f'{OUT}/PNG分層/{fname}', dpi=DPI, compress_level=6)
        crop, top, left = im, 0, 0
    else:
        im = Image.fromarray(x, 'RGBA'); im.save(f'{OUT}/PNG分層/{fname}', dpi=DPI, compress_level=6)
        ys, xs = np.where(x[..., 3] > 0)
        top, left = max(0, ys.min() - 2), max(0, xs.min() - 2)
        bottom, right = min(H, ys.max() + 3), min(Wd, xs.max() + 3)
        crop = Image.fromarray(x[top:bottom, left:right], 'RGBA')
    if grp not in groups: groups[grp] = add_group(psd, grp, GROUP_SLUG[grp])
    add_layer(groups[grp], crop, name, slug, top=int(top), left=int(left), visible=vis)
    log(fname, crop.size, (left, top))
psd_path = f'{OUT}/新竹縣政府AI記者會邀請函_分層_300dpi.psd'
psd.save(psd_path)
log('psd saved', os.path.getsize(psd_path)//1024//1024, 'MB')
