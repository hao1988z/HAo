#!/usr/bin/env python3
"""Build the Adobe Express import page for art/globe/globe.svg.

The Express HTML importer turns every SVG element into its own editable
vector layer, but it keeps only fill / stroke / stroke-width / stroke-opacity
/ stroke-dasharray: stroke-linecap, clip-path and group filters are dropped.
So the page is a stack of layers in the original paint order:

* editable SVG (native Express vector layers) for everything that survives
  that whitelist: ocean, pale land, graticule, links, routes, nodes, rim;
* inline data-URI SVG images (kept verbatim by the importer) for the parts
  that need the dropped features: the dotted lattice (round caps + soft
  glow) and the two blurred glow layers.

Usage:  python3 tools/build_globe_express.py > art/globe/globe-express.html
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG = (ROOT / "art/globe/globe.svg").read_text()
W = H = 1254


def block(svg, ident):
    """Return the element with id=ident (a <g>…</g> or a self-closed tag)."""
    start = svg.index(f' id="{ident}"')
    start = svg.rindex("<", 0, start)
    tag = re.match(r"<(\w+)", svg[start:]).group(1)
    head_end = svg.index(">", start)
    if svg[head_end - 1] == "/":
        return svg[start:head_end + 1]
    depth, i = 0, start
    pat = re.compile(rf"<(/?){tag}\b[^>]*?(/?)>")
    for m in pat.finditer(svg, start):
        if m.group(1):
            depth -= 1
        elif not m.group(2):
            depth += 1
        if depth == 0:
            return svg[start:m.end()]
    raise ValueError(ident)


def defs(svg, ids):
    out = []
    for ident in ids:
        m = re.search(rf'<(\w+) id="{ident}"', svg)
        out.append(block(svg, ident) if m else "")
    return "<defs>" + "".join(out) + "</defs>"


def open_svg():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}">')


def vector_layer(content, def_ids):
    return open_svg() + defs(SVG, def_ids) + content + "</svg>"


def image_layer(content, def_ids, alt):
    s = open_svg() + defs(SVG, def_ids) + content + "</svg>"
    s = s.replace('"', "'").replace("%", "%25").replace("#", "%23")
    return f'<img src="data:image/svg+xml;utf8,{s}" alt="{alt}" width="{W}" height="{H}">'


def build():
    globe_open = '<g id="globe">'
    layers = [
        vector_layer(globe_open + block(SVG, "ocean") + block(SVG, "ocean-light")
                     + block(SVG, "land-pale") + block(SVG, "graticule") + "</g>",
                     ["gOcean", "gLit", "gLand"]),
        image_layer(block(SVG, "land-dots"), ["fDots"], "dotted continents"),
        vector_layer(block(SVG, "rim-light"), ["gRim"]),
        image_layer(block(SVG, "links-glow"), ["fGlow"], "link glow"),
        vector_layer(block(SVG, "links") + block(SVG, "routes-dashed"), []),
        image_layer(block(SVG, "node-bloom"), ["fBloom"], "node bloom"),
        vector_layer(re.sub(r'<g id="node-bloom".*?</g>', "", block(SVG, "nodes"), flags=re.S)
                     + block(SVG, "rim-highlight") + block(SVG, "rim-edge"), ["gNode"]),
    ]
    body = "\n".join(layers)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="hz:slide-selector" content=".slide">
<meta name="hz:canvas-width" content="{W}">
<meta name="hz:canvas-height" content="{H}">
<title>Network Globe</title>
<style>
html,body{{margin:0;padding:0;background:#FFFFFF}}
.slide{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:#FFFFFF}}
.slide>svg,.slide>img{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;display:block}}
</style>
</head>
<body>
<div class="slide" data-canvas-width="{W}" data-canvas-height="{H}">
{body}
</div>
</body>
</html>
"""


if __name__ == "__main__":
    print(build(), end="")
