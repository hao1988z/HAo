"""Fit smooth cubic Bezier outlines to closed pixel contours.

Pipeline (per closed contour):
  1. resample the contour at a fixed arc-length step;
  2. low-pass it (circular Gaussian) to remove pixel/tracing jitter;
  3. find true design corners (large turning angle over a short window);
  4. fit each corner-to-corner run with the fewest cubic segments whose
     maximum deviation stays under `tol` (Schneider's algorithm), keeping
     tangents continuous at every non-corner joint.
"""
import numpy as np


def resample_closed(pts, step):
    pts = np.asarray(pts, float)
    seg = np.diff(np.vstack([pts, pts[:1]]), axis=0)
    ln = np.hypot(seg[:, 0], seg[:, 1])
    s = np.r_[0, np.cumsum(ln)]
    total = s[-1]
    n = max(8, int(round(total / step)))
    t = np.linspace(0, total, n, endpoint=False)
    closed = np.vstack([pts, pts[:1]])
    x = np.interp(t, s, closed[:, 0])
    y = np.interp(t, s, closed[:, 1])
    return np.c_[x, y]


def smooth_closed(pts, sigma):
    if sigma <= 0:
        return pts
    n = len(pts)
    k = int(3 * sigma)
    w = np.exp(-0.5 * (np.arange(-k, k + 1) / sigma) ** 2)
    w /= w.sum()
    out = np.zeros_like(pts)
    for i, wi in zip(range(-k, k + 1), w):
        out += wi * np.roll(pts, -i, axis=0)
    return out


def corners(pts, win, angle_deg):
    n = len(pts)
    a = pts - np.roll(pts, win, axis=0)
    b = np.roll(pts, -win, axis=0) - pts
    ang = np.degrees(np.abs(np.arctan2(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0],
                                       (a * b).sum(1))))
    idx = []
    for i in range(n):
        if ang[i] >= angle_deg and ang[i] == max(ang[(i + j) % n] for j in range(-win, win + 1)):
            idx.append(i)
    return idx


# ---- Schneider curve fitting ------------------------------------------------
def _bez(ctrl, t):
    t = t[:, None]
    return ((1 - t) ** 3 * ctrl[0] + 3 * (1 - t) ** 2 * t * ctrl[1]
            + 3 * (1 - t) * t ** 2 * ctrl[2] + t ** 3 * ctrl[3])


def _bez_d(ctrl, t):
    t = t[:, None]
    return (3 * (1 - t) ** 2 * (ctrl[1] - ctrl[0]) + 6 * (1 - t) * t * (ctrl[2] - ctrl[1])
            + 3 * t ** 2 * (ctrl[3] - ctrl[2]))


def _bez_dd(ctrl, t):
    t = t[:, None]
    return 6 * (1 - t) * (ctrl[2] - 2 * ctrl[1] + ctrl[0]) + 6 * t * (ctrl[3] - 2 * ctrl[2] + ctrl[1])


def _chord_params(p):
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    return d / d[-1] if d[-1] > 0 else np.linspace(0, 1, len(p))


def _generate(p, u, t1, t2):
    p0, p3 = p[0], p[-1]
    A1 = t1[None, :] * (3 * (1 - u) ** 2 * u)[:, None]
    A2 = t2[None, :] * (3 * (1 - u) * u ** 2)[:, None]
    C = np.array([[np.sum(A1 * A1), np.sum(A1 * A2)], [np.sum(A1 * A2), np.sum(A2 * A2)]])
    base = _bez(np.array([p0, p0, p3, p3]), u)
    X = np.array([np.sum(A1 * (p - base)), np.sum(A2 * (p - base))])
    det = C[0, 0] * C[1, 1] - C[0, 1] * C[1, 0]
    seg = np.hypot(*(p3 - p0))
    if abs(det) > 1e-12:
        a1 = (X[0] * C[1, 1] - X[1] * C[0, 1]) / det
        a2 = (C[0, 0] * X[1] - C[1, 0] * X[0]) / det
    else:
        a1 = a2 = seg / 3
    eps = 1e-6 * seg
    if a1 < eps or a2 < eps:
        a1 = a2 = seg / 3
    return np.array([p0, p0 + t1 * a1, p3 + t2 * a2, p3])


def _reparam(ctrl, p, u):
    d = _bez(ctrl, u) - p
    d1 = _bez_d(ctrl, u)
    d2 = _bez_dd(ctrl, u)
    num = (d * d1).sum(1)
    den = (d1 * d1).sum(1) + (d * d2).sum(1)
    with np.errstate(divide='ignore', invalid='ignore'):
        nu = np.where(np.abs(den) > 1e-12, u - num / den, u)
    return np.clip(nu, 0, 1)


def _max_err(ctrl, p, u):
    e = np.hypot(*(_bez(ctrl, u) - p).T)
    i = int(np.argmax(e))
    return e[i], i


def _unit(v):
    n = np.hypot(*v)
    return v / n if n > 1e-12 else v


def fit_run(p, t1, t2, tol, out):
    if len(p) == 2:
        d = np.hypot(*(p[1] - p[0])) / 3
        out.append(np.array([p[0], p[0] + t1 * d, p[1] + t2 * d, p[1]]))
        return
    u = _chord_params(p)
    ctrl = _generate(p, u, t1, t2)
    err, split = _max_err(ctrl, p, u)
    if err < tol:
        out.append(ctrl)
        return
    if err < tol * 4:
        for _ in range(20):
            u = _reparam(ctrl, p, u)
            ctrl = _generate(p, u, t1, t2)
            err, split = _max_err(ctrl, p, u)
            if err < tol:
                out.append(ctrl)
                return
    split = min(max(split, 1), len(p) - 2)
    tc = _unit(p[split - 1] - p[split + 1])
    fit_run(p[:split + 1], t1, tc, tol, out)
    fit_run(p[split:], -tc, t2, tol, out)


def fit_closed(contour, step=2.0, sigma=2.0, tol=1.2, corner_win=4, corner_deg=55):
    """Return a list of cubic segments (4x2 arrays) for a closed contour."""
    pts = resample_closed(contour, step)
    pts = smooth_closed(pts, sigma / step)
    n = len(pts)
    cs = corners(pts, corner_win, corner_deg)
    if not cs:
        # no corners: start anywhere, joint tangent is the local direction
        cs = [0]
        smooth_start = True
    else:
        smooth_start = False
    segs = []
    for k, c0 in enumerate(cs):
        c1 = cs[(k + 1) % len(cs)]
        run = np.vstack([pts[c0:], pts[:c1 + 1]]) if c1 <= c0 else pts[c0:c1 + 1]
        if len(cs) == 1:
            run = np.vstack([pts[c0:], pts[:c0 + 1]])
        if len(run) < 2:
            continue
        if smooth_start:
            tin = _unit(pts[1] - pts[-1])
            t1, t2 = tin, -tin
        else:
            t1 = _unit(run[min(2, len(run) - 1)] - run[0])
            t2 = _unit(run[max(-3, -len(run))] - run[-1])
        fit_run(run, t1, t2, tol, segs)
    return segs


def to_path(segs, fmt=lambda v: f"{v:.1f}".rstrip('0').rstrip('.')):
    if not segs:
        return ''
    d = [f"M{fmt(segs[0][0][0])} {fmt(segs[0][0][1])}"]
    for s in segs:
        d.append("C" + " ".join(f"{fmt(x)} {fmt(y)}" for x, y in s[1:]))
    d.append("Z")
    return "".join(d)
