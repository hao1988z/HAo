#!/usr/bin/env python3
"""Geometric reconstruction of art/globe/reference.webp as a hand-built SVG.

All geometry comes from art/globe/globe-data.json (measured from the
reference) and is emitted as exact primitives instead of traced pixels:

* Globe: one circle (fitted to the alpha edge, r = 547.5).
* Graticule: a true 15-degree lat/long grid on the sphere. Every parallel and
  meridian is the orthographic projection of a circle, so each one is a single
  SVG elliptical arc (A command) over its visible part.
* Network links: circular arcs (A) or single quadratic Beziers (Q) between
  node centres; dashed routes are quadratics with a dash pattern.
* Continents: smooth cubic outlines fitted with few anchors (tools/bezierfit.py).
  The dotted continents are a regular dot lattice with a gentle spherical
  falloff, clipped by those outlines and drawn as dotted strokes
  (dash 0, round caps): each run of dots is one two-anchor segment.
* Light effects: radial/linear gradients and Gaussian blur filters only.

Usage:  python3 tools/build_globe_svg.py > art/globe/globe.svg
"""
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "art/globe/globe-data.json").read_text())
W, H = DATA["canvas"]
CX, CY, RG = DATA["globe"]["cx"], DATA["globe"]["cy"], DATA["globe"]["r"]


def n(v, nd=2):
    s = f"{v:.{nd}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def pt(p):
    return f"{n(p[0])} {n(p[1])}"


# --- cubic outlines ---------------------------------------------------------
def cubic_path(segs):
    p1 = lambda q: f"{n(q[0], 1)} {n(q[1], 1)}"
    d = [f"M{p1(segs[0][0])}"]
    for s in segs:
        d.append(f"C{p1(s[1])} {p1(s[2])} {p1(s[3])}")
    return "".join(d) + "Z"


def sample_cubics(segs, k=8):
    t = np.linspace(0, 1, k, endpoint=False)[:, None]
    out = []
    for s in segs:
        p = np.asarray(s, float)
        out.append((1 - t) ** 3 * p[0] + 3 * (1 - t) ** 2 * t * p[1]
                   + 3 * (1 - t) * t ** 2 * p[2] + t ** 3 * p[3])
    return np.vstack(out)


def inside(poly, pts):
    """Even-odd point-in-polygon test (vectorised ray casting)."""
    x, y = pts[:, 0], pts[:, 1]
    res = np.zeros(len(pts), bool)
    xj, yj = poly[-1]
    for xi, yi in poly:
        cond = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi)
        res ^= cond
        xj, yj = xi, yi
    return res


# --- network geometry -------------------------------------------------------
NODES = np.array([[q["x"], q["y"]] for q in DATA["nodes"]])
NODE_R = np.array([q["r"] for q in DATA["nodes"]])


def link_path(l):
    p0 = NODES[l["i"]] if l.get("i") is not None else np.array(l["p0"])
    if l["geom"] == "arc":
        p1 = NODES[l["j"]]
        s = l["s"]
        d = p1 - p0
        L = math.hypot(*d)
        if abs(s) < 0.05:
            return f"M{pt(p0)}L{pt(p1)}"
        r = (L * L / 4 + s * s) / (2 * abs(s))
        nrm = np.array([-d[1], d[0]]) / L
        apex = (p0 + p1) / 2 + nrm * s
        cross = (apex[0] - p0[0]) * (p1[1] - apex[1]) - (apex[1] - p0[1]) * (p1[0] - apex[0])
        sweep = 1 if cross > 0 else 0
        large = 1 if abs(s) > L / 2 else 0
        return f"M{pt(p0)}A{n(r)} {n(r)} 0 {large} {sweep} {pt(p1)}"
    p1 = NODES[l["j"]] if l.get("j") is not None else np.array(l["p1"])
    return f"M{pt(p0)}Q{pt(l['c'])} {pt(p1)}"


def link_tier(l):
    w = l.get("width", 2)
    warm = l.get("warm", 0)
    size = "bold" if w >= 3.25 else ("mid" if w >= 2.5 else "thin")
    tone = "gold" if warm >= 20 else "pearl"
    return size, tone


# --- graticule: projected circles as SVG elliptical arcs --------------------
def frame(tilt, roll):
    b, c = math.radians(tilt), math.radians(roll)
    rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
    rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    m = rz @ rx
    return m @ np.array([0, -1.0, 0]), m @ np.array([1.0, 0, 0]), m @ np.array([0, 0, 1.0])


def circle_arc(c3, u, w, rad):
    """Visible part (z > 0) of the projected 3-D circle c3 + rad(cos t u + sin t w)."""
    m = np.array([[u[0], w[0]], [u[1], w[1]]]) * rad * RG
    cen = np.array([CX + c3[0] * RG, CY + c3[1] * RG])
    # z(t) = c3z + rad(cos t uz + sin t wz) = c3z + A cos(t - phi)
    A = rad * math.hypot(u[2], w[2])
    if A < 1e-9:
        if c3[2] <= 0:
            return None
        t0, span = 0.0, 2 * math.pi
    else:
        ratio = -c3[2] / A
        if ratio >= 1:
            return None
        phi = math.atan2(w[2], u[2])
        if ratio <= -1:
            t0, span = 0.0, 2 * math.pi
        else:
            h = math.acos(ratio)
            t0, span = phi - h, 2 * h
    U, S, Vt = np.linalg.svd(m)
    rx_, ry_ = S[0], S[1]
    if ry_ < 0.3:
        ry_ = 0.3
    rot = math.degrees(math.atan2(U[1, 0], U[0, 0]))
    sweep = 1 if np.linalg.det(m) > 0 else 0

    def P(t):
        return cen + m @ np.array([math.cos(t), math.sin(t)])

    if span >= 2 * math.pi - 1e-6:
        a, b = P(0), P(math.pi)
        return (f"M{pt(a)}A{n(rx_)} {n(ry_)} {n(rot)} 0 {sweep} {pt(b)}"
                f"A{n(rx_)} {n(ry_)} {n(rot)} 0 {sweep} {pt(a)}")
    a, b = P(t0 + 0.002), P(t0 + span - 0.002)
    large = 1 if span > math.pi else 0
    return f"M{pt(a)}A{n(rx_)} {n(ry_)} {n(rot)} {large} {sweep} {pt(b)}"


def graticule():
    g = DATA["graticule"]
    npole, e1, e2 = frame(g["tilt"], g["roll"])
    paths = []
    for lat in np.arange(-90 + g["lat_phase"], 90, g["step"]):
        if abs(lat) > 80:
            continue
        ph = math.radians(lat)
        d = circle_arc(npole * math.sin(ph), e1, e2, math.cos(ph))
        if d:
            paths.append(d)
    for lon in np.arange(g["lon_phase"], 180, g["step"]):
        lm = math.radians(lon)
        dirv = math.cos(lm) * e1 + math.sin(lm) * e2
        d = circle_arc(np.zeros(3), dirv, npole, 1.0)
        if d:
            paths.append(d)
    return paths


# --- dot lattice ------------------------------------------------------------
def lattice(polys):
    lt = DATA["lattice"]
    d0, c = lt["pitch"], lt["falloff"]
    ox, oy = lt["phase"]
    i = np.arange(-90, 91)
    I, J = np.meshgrid(i, i)
    ij = np.c_[I.ravel(), J.ravel()]
    q = np.c_[ij[:, 0] * d0 + ox, ij[:, 1] * d0 + oy]
    r = np.hypot(q[:, 0], q[:, 1]) / RG
    k = 1 - c * r * r
    p = np.c_[CX + q[:, 0] * k, CY + q[:, 1] * k]
    keep = (np.hypot(p[:, 0] - CX, p[:, 1] - CY) < RG - 4) & (r < 1.15)
    p, k, ij = p[keep], k[keep], ij[keep]
    hit = np.zeros(len(p), bool)
    for poly in polys:
        lo, hi = poly.min(0) - 1, poly.max(0) + 1
        box = (p[:, 0] > lo[0]) & (p[:, 0] < hi[0]) & (p[:, 1] > lo[1]) & (p[:, 1] < hi[1])
        idx = np.flatnonzero(box)
        hit[idx[inside(poly, p[idx])]] = True
    return p[hit], k[hit], ij[hit]


def dotted_rows(pts, scales, ij, r0, tol=0.3, q=0.05, bands=(0.86, 0.94)):
    """Encode the lattice as dotted strokes, the way it is drawn by hand.

    Each run of neighbouring dots in a lattice row becomes one straight
    segment stroked with stroke-dasharray="0 D" and round caps, so a run of
    n dots costs two anchors. Runs are split wherever the evenly spaced
    model (pitch quantised to `q`) would move any dot by more than `tol` px,
    which absorbs the spherical falloff and the slight bow of the rows.
    Returns {(pitch, size band): [subpath, ...]}.
    """
    groups = {}
    edges = np.array([-1, bands[0], bands[1], 9])
    order = np.lexsort((ij[:, 0], ij[:, 1]))
    pts, scales, ij = pts[order], scales[order], ij[order]
    runs, cur = [], [0]
    for k in range(1, len(pts)):
        if ij[k, 1] == ij[k - 1, 1] and ij[k, 0] == ij[k - 1, 0] + 1:
            cur.append(k)
        else:
            runs.append(cur)
            cur = [k]
    runs.append(cur)

    def fits(idx):
        a, b = pts[idx[0]], pts[idx[-1]]
        m = len(idx) - 1
        if m == 0:
            return 0.0, (a, a, 0.0)
        L = math.hypot(*(b - a))
        u = (b - a) / L
        dq = round(L / m / q) * q
        pred = a + u * (np.arange(m + 1)[:, None] * dq)
        return float(np.max(np.hypot(*(pred - pts[idx]).T))), (a, u, dq)

    for run in runs:
        s0 = 0
        while s0 < len(run):
            e = s0
            while e + 1 < len(run) and fits(run[s0:e + 2])[0] <= tol:
                e += 1
            idx = run[s0:e + 1]
            _, (a, u, dq) = fits(idx)
            band = int(np.searchsorted(edges, np.median(scales[idx])) - 1)
            m = len(idx) - 1
            if m == 0:
                sub = f"M{n(a[0], 1)} {n(a[1], 1)}h.1"
                key = (None, band)
            else:
                end = a + u * (m * dq + 0.3)
                sub = f"M{n(a[0], 1)} {n(a[1], 1)}L{n(end[0], 1)} {n(end[1], 1)}"
                key = (round(dq, 2), band)
            groups.setdefault(key, []).append(sub)
            s0 = e + 1
    # single dots join any group of the same band (only their first dash shows)
    for (dq, band) in [k for k in groups if k[0] is None]:
        host = next((k for k in groups if k[1] == band and k[0] is not None), None)
        if host:
            groups[host] += groups.pop((dq, band))
        else:
            groups[(7.0, band)] = groups.pop((dq, band))
    widths = {b: 2 * r0 * float(np.clip(np.median(scales[
        (scales > edges[b]) & (scales <= edges[b + 1])]) if np.any(
        (scales > edges[b]) & (scales <= edges[b + 1])) else 1, 0.78, 1)) for b in range(3)}
    return groups, widths


# --- SVG --------------------------------------------------------------------
def build():
    o = []
    a = o.append
    a('<?xml version="1.0" encoding="UTF-8"?>')
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    a('<title>Network globe - geometric reconstruction</title>')
    a('<defs>')
    a(f'<clipPath id="globeClip"><circle cx="{CX}" cy="{CY}" r="{RG}"/></clipPath>')
    # ocean: base radial shading + light from the upper left
    a(f'<radialGradient id="gOcean" gradientUnits="userSpaceOnUse" cx="{CX}" cy="{CY}" r="{RG}">'
      '<stop offset="0" stop-color="#0131B6"/><stop offset=".55" stop-color="#012A9F"/>'
      '<stop offset=".74" stop-color="#0233B6"/><stop offset=".86" stop-color="#0349E0"/>'
      '<stop offset=".93" stop-color="#1A6BFA"/><stop offset="1" stop-color="#3C8CFA"/></radialGradient>')
    a(f'<radialGradient id="gLit" gradientUnits="userSpaceOnUse" cx="{n(CX - .42 * RG)}" '
      f'cy="{n(CY - .38 * RG)}" r="{n(1.05 * RG)}">'
      '<stop offset="0" stop-color="#4C8DFF" stop-opacity=".45"/>'
      '<stop offset=".55" stop-color="#2F6CF5" stop-opacity=".14"/>'
      '<stop offset="1" stop-color="#1B4FD8" stop-opacity="0"/></radialGradient>')
    a(f'<radialGradient id="gRim" gradientUnits="userSpaceOnUse" cx="{CX}" cy="{CY}" r="{RG}">'
      '<stop offset=".95" stop-color="#5FA7FA" stop-opacity="0"/>'
      '<stop offset=".972" stop-color="#6DB3FA" stop-opacity=".45"/>'
      '<stop offset=".986" stop-color="#B9E4FC" stop-opacity=".85"/>'
      '<stop offset=".995" stop-color="#E8F9FE"/>'
      '<stop offset="1" stop-color="#F6FCFF"/></radialGradient>')
    a(f'<linearGradient id="gLand" gradientUnits="userSpaceOnUse" x1="{n(CX - RG)}" y1="{n(CY - RG)}" '
      f'x2="{n(CX)}" y2="{n(CY + .2 * RG)}">'
      '<stop offset="0" stop-color="#CFE4FD"/><stop offset=".45" stop-color="#A9CAFA"/>'
      '<stop offset="1" stop-color="#7FAAF5"/></linearGradient>')
    # node: white core, thin yellow ring, orange falloff (stops are radius-relative)
    a('<radialGradient id="gNode">'
      '<stop offset="0" stop-color="#FFFFFF"/><stop offset=".27" stop-color="#FFFFFF"/>'
      '<stop offset=".31" stop-color="#FFF6B8"/><stop offset=".36" stop-color="#FFE03A"/>'
      '<stop offset=".5" stop-color="#FFB527" stop-opacity=".78"/>'
      '<stop offset=".72" stop-color="#FF931C" stop-opacity=".28"/>'
      '<stop offset="1" stop-color="#FF8412" stop-opacity="0"/></radialGradient>')
    a('<filter id="fGlow" x="-10%" y="-10%" width="120%" height="120%">'
      '<feGaussianBlur stdDeviation="2.6"/></filter>')
    a('<filter id="fBloom" x="-50%" y="-50%" width="200%" height="200%">'
      '<feGaussianBlur stdDeviation="3"/></filter>')
    a('<filter id="fDots" x="-2%" y="-2%" width="104%" height="104%">'
      '<feGaussianBlur in="SourceGraphic" stdDeviation="1.1" result="b"/>'
      '<feComposite in="SourceGraphic" in2="b" operator="over"/></filter>')
    a('</defs>')

    # outer halo + sphere
    a('<g id="globe" clip-path="url(#globeClip)">')
    a(f'<circle id="ocean" cx="{CX}" cy="{CY}" r="{RG}" fill="url(#gOcean)"/>')
    a(f'<circle id="ocean-light" cx="{CX}" cy="{CY}" r="{RG}" fill="url(#gLit)"/>')

    light = DATA["land"]["light"]
    d = "".join(cubic_path(p["segs"]) for p in light)
    a(f'<path id="land-pale" d="{d}" fill="url(#gLand)" fill-opacity=".95" fill-rule="evenodd"/>')

    a('<g id="graticule" fill="none" stroke="#9CCBFF" stroke-width="1" stroke-opacity=".32">')
    for gp in graticule():
        a(f'<path d="{gp}"/>')
    a('</g>')

    polys = [sample_cubics(p["segs"]) for p in DATA["land"]["dotted"]]
    pts, sc, ij = lattice(polys)
    groups, widths = dotted_rows(pts, sc, ij, DATA["lattice"]["dot_r"])
    a('<g id="land-dots" fill="none" stroke="#DFF8FF" stroke-linecap="round" filter="url(#fDots)">')
    for (dq, band), subs in sorted(groups.items()):
        a(f'<path d="{"".join(subs)}" stroke-width="{n(widths[band])}" stroke-dasharray="0 {n(dq)}"/>')
    a('</g>')

    a(f'<circle id="rim-light" cx="{CX}" cy="{CY}" r="{RG}" fill="url(#gRim)"/>')
    a('</g>')

    # network: glow under-strokes, then crisp cores
    width = {"bold": 3.0, "mid": 2.3, "thin": 1.5}
    core = {"gold": "#FFE98F", "pearl": "#FFF8E8"}
    glow = {"gold": "#FFB42A", "pearl": "#FFD27A"}
    solid = [l for l in DATA["links"] if l["kind"] == "solid"]
    dashed = [l for l in DATA["links"] if l["kind"] == "dashed"]
    a('<g id="links-glow" fill="none" stroke-linecap="round" filter="url(#fGlow)">')
    for l in solid:
        size, tone = link_tier(l)
        a(f'<path d="{link_path(l)}" stroke="{glow[tone]}" stroke-width="{n(width[size] * 2.5)}" '
          f'stroke-opacity="{".65" if tone == "gold" else ".4"}"/>')
    a('</g>')
    a('<g id="links" fill="none" stroke-linecap="round">')
    for l in solid:
        size, tone = link_tier(l)
        a(f'<path d="{link_path(l)}" stroke="{core[tone]}" stroke-width="{n(width[size])}"/>')
    a('</g>')
    a('<g id="routes-dashed" fill="none" stroke="#D9F1FF" stroke-width="1.6" '
      'stroke-dasharray="7 5" stroke-linecap="round" stroke-opacity=".85">')
    for l in dashed:
        a(f'<path d="{link_path(l)}"/>')
    a('</g>')

    a('<g id="nodes">')
    a('<g id="node-bloom" filter="url(#fBloom)" fill="#FFB02A" fill-opacity=".35">')
    for (x, y), r in zip(NODES, NODE_R):
        a(f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(r * 2.6)}"/>')
    a('</g>')
    for (x, y), r in zip(NODES, NODE_R):
        a(f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(r * 3.4)}" fill="url(#gNode)"/>')
    a('</g>')

    a(f'<circle id="rim-highlight" cx="{CX}" cy="{CY}" r="{n(RG - 4.5)}" fill="none" stroke="#F2FCFF" '
      'stroke-width="2.2" stroke-opacity=".85"/>')
    a(f'<circle id="rim-edge" cx="{CX}" cy="{CY}" r="{n(RG - 1.3)}" fill="none" stroke="#3B9DE6" '
      'stroke-width="2.6"/>')
    a('</svg>')
    return "\n".join(o)


if __name__ == "__main__":
    print(build())
