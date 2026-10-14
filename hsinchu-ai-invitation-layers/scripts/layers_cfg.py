# Element definitions in source (1024x1536) pixel coordinates
GLOBE = (823.0, 941.0, 344.0)            # cx, cy, r (outer glass rim)
# bottom edge where the front waves pass over the globe: (x, y) spline points
GLOBE_CUT = [(400, 1075), (470, 1100), (540, 1125), (640, 1150), (740, 1168), (840, 1176), (940, 1168), (1024, 1150)]
GLOBE_CUT_FEATHER = 14
BADGES = {  # name: (cx, cy, r)
    'cloud':  (925.32, 725.68, 45.0),
    'server': (813.66, 844.02, 47.8),
    'chip':   (586.57, 995.34, 46.1),
    'people': (926.26, 1052.58, 44.2),
}
GOLD_ICONS = {
    'calendar': (137.70, 1265.04, 30.85),
    'location': (137.73, 1359.59, 30.70),
}
INFO_BOX = (46.4, 1198.4, 976.4, 1500.0, 24.0)   # border centre-line: x0, y0, x1, y1, corner radius
INFO_BOX_STROKE = 2.0                             # border width
INFO_BOX_FADE = (1385, 1405)                      # side borders disappear behind the waves here
FRONT_WAVE_TOP = 1372
# text / line elements: name -> (kind, [boxes x0,y0,x1,y1])
ELEMENTS = {
    'county':      ('navy', [(50, 68, 368, 138)]),
    'title':       ('navy', [(50, 158, 950, 472)]),
    'press':       ('blue', [(52, 474, 312, 578)]),
    'invitation':  ('gold', [(52, 600, 578, 652)]),
    'tagline':     ('navy', [(52, 698, 738, 748)]),
    'desc':        ('navy', [(52, 756, 718, 844)]),
    'rules':       ('gold', [(372, 94, 920, 112), (52, 585, 190, 599), (52, 671, 132, 686), (52, 857, 140, 873)]),
    'date':        ('navy', [(188, 1230, 918, 1294)]),
    'divider':     ('gold', [(98, 1305, 922, 1321)]),
    'place':       ('navy', [(188, 1333, 622, 1390)]),
    'regards':     ('gold', [(272, 1414, 752, 1462)]),
}
