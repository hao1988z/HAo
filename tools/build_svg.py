#!/usr/bin/env python3
"""Geometric reconstruction of art/reference.webp as a hand-built SVG.

Every shape is generated from a small set of measured parameters instead of
being traced from pixels:

* Wall courses: one cylinder-perspective curve  y = Y0 + d * S(x),
  S(x) = sqrt(1 + ((x - CX) / F)^2)  (a hyperbola). It is fitted once as a
  two-segment cubic Bezier template (max error 0.004 px); every course line
  is the same template scaled vertically by d, so all courses share identical
  handle structure and tangents.
* Brick joints: true vertical lines on a uniform 89 px running bond.
* Light wedges, floor bands and sun beams: straight-edged polygons.
* Light effects: linear gradients, opacity and Gaussian blur only (no blend
  modes, so the file behaves the same in browsers, Illustrator and Express).

Usage:  python3 tools/build_svg.py > art/brick-room.svg
"""

W, H = 1870, 841

# --- Wall: cylindrical perspective (fitted to the reference, RMS 1.2 px) ----
Y0, CX, F = 576.75, 940.0, 1470.0   # eye level, axis, focal length
C0, PITCH = 92.60, 31.016           # course 0 height on the axis, course pitch
K_FIRST, K_FLOOR = -3, 19           # first visible course line, wall/floor line

# S(x) as a 2-segment cubic: (x, S) for P0 P1 P2 P3 | P1' P2' P3'.
# Both handles at the centre anchor are horizontal, so the join is smooth.
TEMPLATE = [(-20.0, 1.194357), (341.248, 1.059985), (645.664, 1.0),
            (940.0, 1.0),
            (1238.68, 1.0), (1541.54, 1.061987), (1890.0, 1.190651)]

BRICK = 89.0                        # brick length in screen px
PHASE = {0: 78.5, 1: 34.0}          # first joint x for even / odd courses

# --- Light wedges on the wall (straight edges, measured) --------------------
LEFT_WEDGE = [(237.5, -10), (700.0, 333.0), (1135.7, -10)]
RIGHT_WEDGE = [(1593.4, -10), (1890.0, 333.7), (1890.0, -10)]

# --- Floor -----------------------------------------------------------------
VX, VY = 926.0, 620.0               # vanishing point of the floor plaid
Y_TOP, Y_BOT = 670.0, 860.0         # band extents (clipped by the floor edge)


def n(v):
    """Compact number formatting."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def S(x):
    return (1 + ((x - CX) / F) ** 2) ** 0.5


def course_y(k, x):
    return Y0 + (C0 + k * PITCH - Y0) * S(x)


def course_path(k, start="M"):
    d = C0 + k * PITCH - Y0
    p = [(x, Y0 + d * s) for x, s in TEMPLATE]
    return (f"{start}{n(p[0][0])} {n(p[0][1])}"
            f"C{n(p[1][0])} {n(p[1][1])} {n(p[2][0])} {n(p[2][1])} {n(p[3][0])} {n(p[3][1])}"
            f"C{n(p[4][0])} {n(p[4][1])} {n(p[5][0])} {n(p[5][1])} {n(p[6][0])} {n(p[6][1])}")


def clip_x(points, lo=-20.0, hi=1890.0):
    """Sutherland-Hodgman clip of a polygon to the artboard's x range."""
    for keep, edge in ((lambda p: p[0] >= lo, lo), (lambda p: p[0] <= hi, hi)):
        out = []
        for i, cur in enumerate(points):
            prev = points[i - 1]
            if keep(cur) != keep(prev):
                t = (edge - prev[0]) / (cur[0] - prev[0])
                out.append((edge, prev[1] + t * (cur[1] - prev[1])))
            if keep(cur):
                out.append(cur)
        points = out
    return points


def poly(points):
    pts = []
    for x, y in clip_x(points):
        p = (round(x, 2), round(y, 2))
        if not pts or p != pts[-1]:
            pts.append(p)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    return "M" + " ".join(f"{n(x)} {n(y)}" for x, y in pts) + "Z"


def u_band(ua, ub, y1=Y_TOP, y2=Y_BOT):
    """Quad between two receding floor lines x = VX + u * (y - VY)."""
    return poly([(VX + ua * (y1 - VY), y1), (VX + ub * (y1 - VY), y1),
                 (VX + ub * (y2 - VY), y2), (VX + ua * (y2 - VY), y2)])


def u_clip_rect(ua, ub, y1, y2):
    """Cross band (y1..y2) limited to the receding strip ua..ub."""
    big = 60.0
    ua, ub = max(ua, -big), min(ub, big)
    return poly([(VX + ua * (y1 - VY), y1), (VX + ub * (y1 - VY), y1),
                 (VX + ub * (y2 - VY), y2), (VX + ua * (y2 - VY), y2)])


def line_band(left, right, y1, y2):
    """Quad between two straight lines x = a + b * y (sun beams)."""
    (al, bl), (ar, br) = left, right
    return poly([(al + bl * y1, y1), (ar + br * y1, y1),
                 (ar + br * y2, y2), (al + bl * y2, y2)])


def apex(left, right):
    (al, bl), (ar, br) = left, right
    y = (ar - al) / (bl - br)
    return al + bl * y, y


# Plaid: receding strips (u) x cross rows (y). Each light check is a quad
# bounded by two receding lines and two horizontal lines: (u0, u1, y0, y1, a).
U = (-60.0, -5.3, -3.25, -2.3, 2.0, 3.0, 3.95, 5.4, 60.0)  # strip boundaries
R1, R2, R3, R5, R6 = (700, 718), (718, 735), (736, 754), (766, 797), (797, 860)
CHECKS = [
    (U[0], U[4], *R1, .34),                      # far row
    (U[3], U[4], *R2, .3),
    (U[1], U[3], *R3, .46), (U[4], U[6], *R3, .5), (U[7], U[8], *R3, .5),
    (U[3], U[6], *R5, .58), (U[7], U[8], 754, 787, .55),
    (U[0], U[2], *R6, 'fade'),
]

# Far zone gingham: alternating receding stripes and evenly spaced rows.
FAR_U0, FAR_DU = -12.0, 0.9
FAR_ROWS = [(684, 688), (692, 698), (701, 705)]

# Receding white veils (u range, opacity).
RECEDING = [(-7.0, -5.2, .1), (-5.2, -4.1, .3), (-4.1, -3.85, .18),
            (-1.95, -1.6, .16), (-0.2, 0.05, .1), (0.4, 1.27, .18)]

# Vertical reflection bands (x0, x1, opacity).
VERTICAL = [(44, 54, .24), (108, 150, .17), (198, 241, .22), (302, 336, .17),
            (412, 455, .2), (557, 604, .22), (693, 721, .2), (790, 837, .3),
            (837, 880, .12), (912, 936, .22), (985, 1038, .2), (1216, 1248, .17),
            (1300, 1345, .17), (1544, 1570, .24), (1607, 1657, .14),
            (1673, 1721, .2)]
GLINT = (1127, 1169)                # cyan light strip (x range)

# Sun beams: edge lines x = a + b * y fitted to the reference.
BEAM_1 = ((3174.3, -3.524), (2474.4, -2.47))      # left beam
BEAM_2 = ((280.5, 1.103), (-512.2, 2.249))        # centre-right fan
BEAM_3 = ((-1358.3, 3.547), (-2105.7, 4.684))     # right beam


def build():
    o = []
    a = o.append
    a('<?xml version="1.0" encoding="UTF-8"?>')
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
      f'viewBox="0 0 {W} {H}">')
    a('<title>Curved brick room - geometric reconstruction</title>')

    # ---------------------------------------------------------------- defs
    a('<defs>')
    floor_edge = course_path(K_FLOOR)
    a(f'<clipPath id="noGlint"><rect x="-20" y="600" width="{GLINT[0] + 20}" height="300"/>'
      f'<rect x="{GLINT[1]}" y="600" width="{1890 - GLINT[1]}" height="300"/></clipPath>')
    a(f'<clipPath id="floorClip"><path d="{floor_edge}L1890 870L-20 870Z"/></clipPath>')

    # wall light wedges: multiply tint, fading toward the apex
    a('<linearGradient id="gWedgeL" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="333">'
      '<stop offset="0" stop-color="#A6B7E6" stop-opacity=".55"/>'
      '<stop offset=".26" stop-color="#A6B7E6" stop-opacity=".5"/>'
      '<stop offset=".42" stop-color="#A6B7E6" stop-opacity=".42"/>'
      '<stop offset=".52" stop-color="#A6B7E6" stop-opacity=".31"/>'
      '<stop offset=".66" stop-color="#A6B7E6" stop-opacity=".23"/>'
      '<stop offset=".86" stop-color="#A6B7E6" stop-opacity=".13"/>'
      '<stop offset="1" stop-color="#A6B7E6" stop-opacity=".03"/></linearGradient>')
    a('<linearGradient id="gWedgeR" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="334">'
      '<stop offset="0" stop-color="#AABBEC" stop-opacity=".5"/>'
      '<stop offset=".7" stop-color="#AABBEC" stop-opacity=".5"/>'
      '<stop offset="1" stop-color="#AABBEC" stop-opacity=".3"/></linearGradient>')
    # vertical light shaft inside the left wedge
    a('<linearGradient id="gShaft" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="320">'
      '<stop offset="0" stop-color="#FEF7EC" stop-opacity=".6"/>'
      '<stop offset=".4" stop-color="#FEF7EC" stop-opacity=".45"/>'
      '<stop offset=".75" stop-color="#FEF7EC" stop-opacity=".15"/>'
      '<stop offset="1" stop-color="#FEF7EC" stop-opacity="0"/></linearGradient>')
    a('<filter id="fShaft" x="-40%" y="-5%" width="180%" height="110%">'
      '<feGaussianBlur stdDeviation="9 4"/></filter>')
    # soft bevel under every mortar course
    a('<filter id="fBevel" x="-2%" y="-20%" width="104%" height="140%">'
      '<feGaussianBlur stdDeviation="1.4"/></filter>')

    # floor
    a('<linearGradient id="gFloor" gradientUnits="userSpaceOnUse" x1="0" y1="680" x2="0" y2="841">'
      '<stop offset="0" stop-color="#7DB2F4"/>'
      '<stop offset=".3" stop-color="#5FA0F1"/>'
      '<stop offset=".72" stop-color="#4891EE"/>'
      '<stop offset="1" stop-color="#3F8BEC"/></linearGradient>')
    a('<linearGradient id="gHaze" gradientUnits="userSpaceOnUse" x1="0" y1="680" x2="0" y2="730">'
      '<stop offset="0" stop-color="#E6EDF9" stop-opacity=".6"/>'
      '<stop offset=".3" stop-color="#E6EDF9" stop-opacity=".22"/>'
      '<stop offset="1" stop-color="#E6EDF9" stop-opacity="0"/></linearGradient>')
    a('<linearGradient id="gLight" gradientUnits="userSpaceOnUse" x1="0" y1="766" x2="0" y2="797">'
      '<stop offset="0" stop-color="#FFFFFF" stop-opacity=".66"/>'
      '<stop offset="1" stop-color="#FFFFFF" stop-opacity=".54"/></linearGradient>')
    a('<linearGradient id="gFar" gradientUnits="userSpaceOnUse" x1="0" y1="680" x2="0" y2="730">'
      '<stop offset="0" stop-color="#FFFFFF" stop-opacity=".3"/>'
      '<stop offset=".55" stop-color="#FFFFFF" stop-opacity=".2"/>'
      '<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>')
    a('<linearGradient id="gLightLow" gradientUnits="userSpaceOnUse" x1="0" y1="797" x2="0" y2="841">'
      '<stop offset="0" stop-color="#FFFFFF" stop-opacity=".4"/>'
      '<stop offset="1" stop-color="#FFFFFF" stop-opacity=".12"/></linearGradient>')
    a('<linearGradient id="gWarm" gradientUnits="userSpaceOnUse" x1="380" y1="0" x2="1080" y2="0">'
      '<stop offset="0" stop-color="#FFE9A0" stop-opacity="0"/>'
      '<stop offset=".12" stop-color="#FFE9A0" stop-opacity=".8"/>'
      '<stop offset=".8" stop-color="#FFEDB0" stop-opacity=".7"/>'
      '<stop offset="1" stop-color="#FFEDB0" stop-opacity="0"/></linearGradient>')
    a('<linearGradient id="gBeamA" gradientUnits="userSpaceOnUse" x1="0" y1="690" x2="0" y2="860">'
      '<stop offset=".09" stop-color="#FFE68E" stop-opacity="0"/>'
      '<stop offset=".17" stop-color="#FFE68E" stop-opacity=".85"/>'
      '<stop offset=".62" stop-color="#FFE68E" stop-opacity=".92"/>'
      '<stop offset=".655" stop-color="#FFF4E0" stop-opacity=".82"/>'
      '<stop offset="1" stop-color="#FFF4E0" stop-opacity=".62"/></linearGradient>')
    a('<linearGradient id="gBeamB" gradientUnits="userSpaceOnUse" x1="0" y1="690" x2="0" y2="860">'
      '<stop offset="0" stop-color="#FFE695" stop-opacity=".75"/>'
      '<stop offset=".3" stop-color="#FFE695" stop-opacity=".9"/>'
      '<stop offset="1" stop-color="#FFE29B" stop-opacity=".92"/></linearGradient>')
    a('<linearGradient id="gBeamC" gradientUnits="userSpaceOnUse" x1="0" y1="690" x2="0" y2="860">'
      '<stop offset="0" stop-color="#FFE47E" stop-opacity=".8"/>'
      '<stop offset=".62" stop-color="#FFE47E" stop-opacity=".95"/>'
      '<stop offset=".655" stop-color="#F3F7FF" stop-opacity=".5"/>'
      '<stop offset="1" stop-color="#F3F7FF" stop-opacity=".4"/></linearGradient>')
    a('<linearGradient id="gGlint" gradientUnits="userSpaceOnUse" x1="0" y1="690" x2="0" y2="841">'
      '<stop offset="0" stop-color="#7FE0FF" stop-opacity=".35"/>'
      '<stop offset=".2" stop-color="#66D8FF" stop-opacity=".6"/>'
      '<stop offset=".7" stop-color="#4CC6FF" stop-opacity=".66"/>'
      '<stop offset="1" stop-color="#3FB4FF" stop-opacity=".7"/></linearGradient>')
    a('<filter id="fGlow" x="-80%" y="-20%" width="260%" height="140%">'
      '<feGaussianBlur stdDeviation="8 12"/></filter>')
    a('<filter id="fSoft" x="-20%" y="-5%" width="140%" height="110%">'
      '<feGaussianBlur stdDeviation="1.5 0"/></filter>')
    a('</defs>')

    # ---------------------------------------------------------------- wall
    a('<g id="wall">')
    a(f'<rect id="wall-plaster" width="{W}" height="{H}" fill="#FEF7EC"/>')
    courses = "".join(course_path(k) for k in range(K_FIRST, K_FLOOR))
    a(f'<path id="mortar-bevel" d="{courses}" fill="none" stroke="#BCC4D6" '
      f'stroke-width="6" stroke-opacity=".32" transform="translate(0 4)" filter="url(#fBevel)"/>')
    a(f'<path id="mortar-courses" d="{courses}" fill="none" stroke="#93A4C6" '
      f'stroke-width="1.2" stroke-linecap="round"/>')
    joints = []
    for k in range(K_FIRST, K_FLOOR):
        x = PHASE[k % 2] - BRICK
        while x < W + BRICK:
            if -2 <= x <= W + 2:
                y1, y2 = course_y(k, x), course_y(k + 1, x)
                if y2 > 0:
                    joints.append(f"M{n(x)} {n(max(y1, -2))}V{n(y2)}")
            x += BRICK
    a(f'<path id="mortar-joints" d="{"".join(joints)}" fill="none" stroke="#93A4C6" '
      f'stroke-width="1.15"/>')
    a('</g>')

    # ---------------------------------------------------------------- light on the wall
    a('<g id="wall-light">')
    a(f'<path id="wedge-left" d="{poly(LEFT_WEDGE)}" fill="url(#gWedgeL)"/>')
    a(f'<path id="wedge-right" d="{poly(RIGHT_WEDGE)}" fill="url(#gWedgeR)"/>')
    a('<rect id="light-shaft" x="648" y="-10" width="94" height="330" fill="url(#gShaft)" '
      'filter="url(#fShaft)"/>')
    a('</g>')

    # ---------------------------------------------------------------- floor
    a('<g id="floor" clip-path="url(#floorClip)">')
    a(f'<rect id="floor-base" y="660" width="{W}" height="200" fill="url(#gFloor)"/>')

    a('<g id="plaid-checks" fill="#FFFFFF">')
    for ua, ub, y1, y2, op in CHECKS:
        fill = 'url(#gLightLow)' if op == 'fade' else None
        attr = f'fill="{fill}"' if fill else f'fill-opacity="{n(op)}"'
        a(f'<path d="{u_clip_rect(ua, ub, y1, y2)}" {attr}/>')
    a('</g>')

    a('<g id="far-gingham" fill="url(#gFar)">')
    u = FAR_U0
    while u < 12:
        a(f'<path d="{u_band(u, u + FAR_DU / 2, Y_TOP, 730)}"/>')
        u += FAR_DU
    for y1, y2 in FAR_ROWS:
        a(f'<rect x="0" y="{y1}" width="{W}" height="{y2 - y1}"/>')
    a('</g>')

    a('<g id="receding-light" fill="#FFFFFF">')
    for ua, ub, op in RECEDING:
        a(f'<path d="{u_band(ua, ub)}" fill-opacity="{n(op)}"/>')
    a('</g>')

    a('<g id="reflection-bands" fill="#FFFFFF">')
    for x0, x1, op in VERTICAL:
        a(f'<rect x="{x0}" y="660" width="{x1 - x0}" height="200" fill-opacity="{n(op)}"/>')
    a('</g>')

    a('<g id="bright-lines">')
    a('<rect x="0" y="755" width="1870" height="11" fill="#FFFFFF" fill-opacity=".42"/>')
    a('<rect x="0" y="727" width="1870" height="7" fill="#FFFFFF" fill-opacity=".3"/>')
    a('<rect x="0" y="709" width="1870" height="5" fill="#FFFFFF" fill-opacity=".22"/>')
    a('<rect x="380" y="755" width="700" height="11" fill="url(#gWarm)"/>')
    a('<rect x="380" y="727" width="700" height="7" fill="url(#gWarm)" fill-opacity=".8"/>')
    a('</g>')

    a('<g id="sun-beams">')
    a(f'<path id="beam-left" d="{line_band(BEAM_1[0], BEAM_1[1], apex(*BEAM_1)[1], Y_BOT)}" '
      f'fill="url(#gBeamA)"/>')
    a(f'<path id="beam-centre" d="{line_band(BEAM_2[0], BEAM_2[1], apex(*BEAM_2)[1], Y_BOT)}" '
      f'fill="url(#gBeamB)" clip-path="url(#noGlint)"/>')
    a(f'<path id="beam-right" d="{line_band(BEAM_3[0], BEAM_3[1], Y_TOP, Y_BOT)}" '
      f'fill="url(#gBeamC)"/>')
    a(f'<path id="beam-spill" d="{u_clip_rect(-2.3, -1.85, 766, 797)}" fill="#FFE9A0" '
      f'fill-opacity=".55"/>')
    a(f'<path id="beam-far-left" d="{u_band(-6.45, -6.1, 722, 764)}" fill="#FFF0BC" '
      f'fill-opacity=".4"/>')
    a('</g>')

    a('<g id="glint">')
    a(f'<rect x="{GLINT[0]}" y="690" width="{GLINT[1] - GLINT[0]}" height="160" '
      f'fill="url(#gGlint)" filter="url(#fSoft)"/>')
    a('<rect x="1122" y="705" width="52" height="100" fill="#D2F6FF" fill-opacity=".45" '
      'filter="url(#fGlow)"/>')
    a('</g>')

    a(f'<rect id="horizon-haze" y="660" width="{W}" height="120" fill="url(#gHaze)"/>')
    a('</g>')

    a(f'<path id="floor-edge" d="{floor_edge}" fill="none" stroke="#A9B8D6" '
      f'stroke-width="1.2" stroke-opacity=".8"/>')
    a('</svg>')
    return "\n".join(o)


if __name__ == "__main__":
    print(build())
