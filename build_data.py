#!/usr/bin/env python3
"""Build the map data embedded in index.html (<script id="vn-data">).

Inputs
  vietnam63-base.json  Vietnam's 63 provinces as first built from geoBoundaries (OCHA ROAP /
                             Government of Viet Nam district boundaries, 2020, CC BY 3.0 IGO), in the
                             old Mercator units, with Trường Sa drawn in a 40% inset.
  <world-atlas>/countries-50m.json
                             Natural Earth 1:50m admin-0 countries (public domain). Get it with:
                               npm pack world-atlas@2.0.2 && tar xzf world-atlas-2.0.2.tgz
  ne_50m_admin_1_states_provinces.geojson
                             Natural Earth 1:50m admin-1 states and provinces (public domain), for
                             China's 31 mainland units. Get it with:
                               curl -LO https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_1_states_provinces.geojson
  china_table.py             China's 34 units: names, pinyin, capitals, 2020 census population.
Requires Python 3.10+ and shapely 2 (pip install shapely).

Usage
  python3 build_data.py path/to/world-atlas/package path/to/ne_50m_admin_1_states_provinces.geojson

What it does
  1. Regions and provinces follow the statistics table of the Atlat Địa lí Việt Nam ("Hành chính"
     page): regions I–VI in the Atlat's order and wording, provinces numbered 1–63 (STT) with the
     table's area (km²) and 2021 population (thousand people; Niên giám thống kê 2021, NXB Thống kê 2022).
  2. Trường Sa is moved out of the 40% inset back to its true position. The inset transform is
     re-derived here from named islands and checked before it is used.
  3. Everything is drawn in an equal-area projection (Albers conic), so sizes on the map are true
     everywhere: China is 29 times Vietnam on the screen as on the ground. One world unit is about
     0.62 km, as in the old Mercator map, so the app's zoom limits and line widths are unchanged.
  4. China's 34 provincial-level units (china_table.py) get their shapes from Natural Earth: the
     31 mainland units from the admin-1 layer, Hong Kong, Macau and Taiwan from the country layer.
     Along the Vietnamese border they are trimmed and stretched to meet the app's own Vietnam.
     Their published areas (china_table.py) are checked against the drawn shapes.
  5. The other countries within about 1,250 km of Vietnam and China are drawn as shapes only, each
     with its capital and sometimes one more city. Beyond that the app shows only fog.
  6. Every unit and country gets one of eight jade tones (used when it is not the country being
     learned) so that no two neighbours share one, and China gets an even five-colouring in the
     Atlat colours for when it is.
"""
import json, math, re, sys
from pathlib import Path

from shapely.geometry import LineString, MultiLineString, MultiPolygon, Point, Polygon, box
from shapely.ops import polylabel, unary_union

import china_table

ROOT = Path(__file__).resolve().parent
BASE = ROOT / 'vietnam63-base.json'
INDEX = ROOT / 'index.html'

# ---------------------------------------------------------------- projections
B = json.loads(BASE.read_text(encoding='utf-8'))
MB = B['meta']['proj']                    # the base file's Mercator: lon0, mtop, s units per degree
def merc(lat): return 180 / math.pi * math.log(math.tan(math.pi / 4 + lat * math.pi / 360))
def imerc(m): return (2 * math.atan(math.exp(m * math.pi / 180)) - math.pi / 2) * 180 / math.pi
def mpx(lon): return (lon - MB['lon0']) * MB['s']
def mpy(lat): return (MB['mtop'] - merc(lat)) * MB['s']
def m_to_ll(x, y): return x / MB['s'] + MB['lon0'], imerc(MB['mtop'] - y / MB['s'])
KM_PER_MERC_UNIT_EQ = 111.32 / MB['s']

# The app's projection: Albers equal-area conic on the sphere, standard parallels 20°N and 45°N,
# centred on 105°E. Scale is within 6% of true in every direction over Vietnam and China.
KU = 111.32 / 180                         # km per world unit at the standard parallels
ALB = {'lon0': 105.0, 'lat0': 24.0, 'lat1': 20.0, 'lat2': 45.0, 'R': round(6371.0088 / KU, 3), 'ku': KU}
_rad = math.radians
_N = (math.sin(_rad(ALB['lat1'])) + math.sin(_rad(ALB['lat2']))) / 2
_C = math.cos(_rad(ALB['lat1'])) ** 2 + 2 * _N * math.sin(_rad(ALB['lat1']))
def _rho(lat): return ALB['R'] * math.sqrt(_C - 2 * _N * math.sin(_rad(lat))) / _N
_RHO0 = _rho(ALB['lat0'])
def proj(lon, lat):
    """lon/lat -> world units (x east, y south). No wrap-around: Natural Earth is cut at ±180°."""
    r, t = _rho(lat), _N * _rad(lon - ALB['lon0'])
    return r * math.sin(t), r * math.cos(t) - _RHO0
def P(lon, lat):
    x, y = proj(lon, lat)
    return [round(x), round(y)]
def from_merc(x, y): return proj(*m_to_ll(x, y))

# ---------------------------------------------------------------- compact path codec
# "M x yl dx dy dx dy ... z" with integer world units; negative numbers carry their own separator.
def parse_rings(d):
    out = []
    for m in re.finditer(r'M(-?\d+) (-?\d+)l([^z]*)z', d):
        x, y = int(m.group(1)), int(m.group(2))
        ring = [(x, y)]
        nums = list(map(int, re.findall(r'-?\d+', m.group(3))))
        for i in range(0, len(nums) - 1, 2):
            x += nums[i]; y += nums[i + 1]; ring.append((x, y))
        out.append(ring)
    return out

def enc_num(n, first=False):
    return str(n) if (n < 0 or first) else ' ' + str(n)

def encode(rings):
    parts = []
    for ring in rings:
        pts = []
        for x, y in ring:
            p = (int(round(x)), int(round(y)))
            if not pts or p != pts[-1]: pts.append(p)
        if len(pts) > 2 and pts[0] == pts[-1]: pts.pop()
        if len(pts) < 2: continue
        s = f'M{pts[0][0]} {pts[0][1]}l'
        first = True
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            s += enc_num(bx - ax, first) + enc_num(by - ay)
            first = False
        parts.append(s + 'z')
    return ''.join(parts)

def ring_area(r):
    return abs(sum(r[i - 1][0] * r[i][1] - r[i][0] * r[i - 1][1] for i in range(len(r)))) / 2

def bbox(points):
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    return [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]

def round_sig(v, n=3):
    if v <= 0: return 0
    d = n - 1 - int(math.floor(math.log10(v)))
    return int(round(v, d)) if d <= 0 else round(v, d)

# ---------------------------------------------------------------- Atlat statistics table
# English names follow the General Statistics Office's own translations; 'short' is for tight spaces.
REGIONS = [
    {'num': 'I', 'vi': 'Đồng bằng sông Hồng', 'en': 'Red River Delta', 'short': 'Red River Delta', 'area': 21278.6, 'pop': 23223.1},
    {'num': 'II', 'vi': 'Trung du và miền núi Bắc Bộ', 'en': 'Northern Midlands and Mountain Areas', 'short': 'Northern Midlands & Mountains', 'area': 95184.2, 'pop': 12925.0},
    {'num': 'III', 'vi': 'Bắc Trung Bộ và Duyên hải miền Trung', 'en': 'North Central and Central Coastal Areas', 'short': 'North Central & Central Coast', 'area': 95847.9, 'pop': 20584.9},
    {'num': 'IV', 'vi': 'Tây Nguyên', 'en': 'Central Highlands', 'short': 'Central Highlands', 'area': 54548.3, 'pop': 6033.8},
    {'num': 'V', 'vi': 'Đông Nam Bộ', 'en': 'Southeast', 'short': 'Southeast', 'area': 23551.4, 'pop': 18315.0},
    {'num': 'VI', 'vi': 'Đồng bằng sông Cửu Long', 'en': 'Mekong River Delta', 'short': 'Mekong River Delta', 'area': 40922.6, 'pop': 17422.6},
]

# Notes in plain English (province names stay Vietnamese; laws are cited by number).
NOTES = {
    '01': 'Absorbed Hà Tây province, Mê Linh district (from Vĩnh Phúc) and 4 communes of Lương Sơn (from Hòa Bình) on 1 August 2008 (Resolution 15/2008/QH12).',
    '10': 'Than Uyên district moved from Lào Cai to Lai Châu in 2004 (Resolution 22/2003/QH11).',
    '11': 'Created in 2004 from the old Lai Châu province (Resolution 22/2003/QH11).',
    '12': 'Re-created in 2004 from the old Lai Châu province, gaining Than Uyên district from Lào Cai (Resolution 22/2003/QH11).',
    '17': 'Lost 4 communes of Lương Sơn district to Hà Nội on 1 August 2008 (Resolution 15/2008/QH12).',
    '22': 'Includes the Vân Đồn and Cô Tô island districts.',
    '26': 'Lost Mê Linh district to Hà Nội on 1 August 2008 (Resolution 15/2008/QH12).',
    '31': 'Includes the Cát Hải (Cát Bà) and Bạch Long Vĩ island districts.',
    '45': 'Includes Cồn Cỏ island district.',
    '46': 'Listed as Thừa Thiên Huế province in the Atlat. It became Huế, a centrally-run city, on 1 January 2025 (Resolution 175/2024/QH15).',
    '48': 'Includes Hoàng Sa district (the Paracel Islands), 305 km² of the official area.',
    '49': 'Includes the Cù Lao Chàm islands (Hội An).',
    '51': 'Includes Lý Sơn island district.',
    '56': 'Includes Trường Sa district (the Spratly Islands), 496 km² of the official area.',
    '60': 'Includes Phú Quý island district.',
    '67': 'Created in 2004 from Đắk Lắk (Resolution 22/2003/QH11).',
    '77': 'Includes Côn Đảo island district.',
    '79': 'Official name: Thành phố Hồ Chí Minh (Hồ Chí Minh City).',
    '91': 'Includes the Phú Quốc and Kiên Hải islands.',
    '92': 'Centrally-run city since 2004 (Resolution 22/2003/QH11).',
    '93': 'Created in 2004 from the old Cần Thơ province (Resolution 22/2003/QH11).',
    '94': 'Includes Cù Lao Dung island district.',
}

def merged_into_en(to):
    """'tỉnh Tuyên Quang' → 'Tuyên Quang province'; 'Thành phố Huế' → 'Huế city'."""
    if to == 'Thành phố Hồ Chí Minh': return 'Hồ Chí Minh City'
    if to.startswith('Thành phố '): return to[len('Thành phố '):] + ' city'
    if to.startswith('tỉnh '): return to[len('tỉnh '):] + ' province'
    raise ValueError(to)
# STT, province code (QĐ 124/2004), area km², population 2021 (thousand)
TABLE = [
    (1, '01', 3359.8, 8330.8), (2, '22', 6207.9, 1350.8), (3, '26', 1236.0, 1191.8), (4, '27', 822.7, 1462.9),
    (5, '30', 1668.3, 1936.8), (6, '33', 930.2, 1284.6), (7, '31', 1526.5, 2072.4), (8, '35', 861.9, 875.2),
    (9, '34', 1584.6, 1873.9), (10, '37', 1411.8, 1007.6), (11, '36', 1668.8, 1836.3),
    (12, '02', 7927.6, 887.1), (13, '04', 6700.4, 542.2), (14, '12', 9068.7, 478.4), (15, '10', 6364.3, 761.9),
    (16, '11', 9539.9, 625.1), (17, '08', 5868.0, 801.7), (18, '06', 4860.0, 323.7), (19, '20', 8310.2, 796.9),
    (20, '15', 6892.7, 842.7), (21, '14', 14109.8, 1287.7), (22, '19', 3522.0, 1323.2), (23, '25', 3534.6, 1507.5),
    (24, '24', 3895.9, 1875.2), (25, '17', 4590.3, 871.7),
    (26, '38', 11114.7, 3716.4), (27, '40', 16486.5, 3409.8), (28, '42', 5994.5, 1314.1), (29, '44', 7998.8, 910.7),
    (30, '45', 4701.2, 647.8), (31, '46', 4947.1, 1153.8), (32, '48', 1284.7, 1195.5), (33, '49', 10574.9, 1518.5),
    (34, '51', 5155.3, 1244.1), (35, '52', 6066.4, 1508.3), (36, '54', 5026.0, 875.5), (37, '56', 5199.6, 1248.1),
    (38, '58', 3355.7, 596.0), (39, '60', 7942.6, 1246.3),
    (40, '62', 9677.3, 568.8), (41, '64', 15510.1, 1569.7), (42, '66', 13070.4, 1909.0), (43, '67', 6509.3, 664.4),
    (44, '68', 9781.2, 1321.9),
    (45, '70', 6873.6, 1024.3), (46, '72', 4041.7, 1181.9), (47, '75', 5863.6, 3169.1), (48, '74', 2694.6, 2596.8),
    (49, '79', 2095.4, 9166.8), (50, '77', 1982.6, 1176.1),
    (51, '80', 4494.8, 1725.8), (52, '87', 3382.3, 1601.3), (53, '89', 3536.8, 1909.5), (54, '91', 6352.9, 1752.3),
    (55, '82', 2556.4, 1779.4), (56, '92', 1440.4, 1247.0), (57, '86', 1525.7, 1029.0), (58, '83', 2379.7, 1295.7),
    (59, '93', 1622.2, 729.9), (60, '84', 2390.8, 1018.6), (61, '94', 3298.2, 1206.8), (62, '95', 2667.9, 918.5),
    (63, '96', 5274.5, 1208.8),
]
REGION_SPANS = [(1, 11), (12, 25), (26, 39), (40, 44), (45, 50), (51, 63)]

def check_table():
    assert sorted(t[0] for t in TABLE) == list(range(1, 64))
    assert len({t[1] for t in TABLE}) == 63
    for r, (a, b) in zip(REGIONS, REGION_SPANS):
        rows = [t for t in TABLE if a <= t[0] <= b]
        sa, sp = sum(t[2] for t in rows), sum(t[3] for t in rows)
        # The printed totals are rounded independently of the rows.
        assert abs(sa - r['area']) <= 0.35 and abs(sp - r['pop']) <= 0.35, (r['num'], sa, sp)

# ---------------------------------------------------------------- Trường Sa: inset → true position
# Public gazetteer positions (lat, lon) of named features spread across the archipelago.
TS_CONTROL = [
    ('Song Tử Tây', 11.4294, 114.3314), ('Song Tử Đông', 11.452, 114.357), ('Thị Tứ', 11.0547, 114.2847),
    ('Loại Ta', 10.6705, 114.4214), ('Ba Bình', 10.3772, 114.3664), ('Sơn Ca', 10.376, 114.478),
    ('Nam Yết', 10.181, 114.361), ('Sinh Tồn', 9.8833, 114.3167), ('Trường Sa Lớn', 8.6444, 111.9194),
    ('An Bang', 7.8667, 112.9167), ('Phan Vinh', 8.95, 113.683), ('Đá Tây', 8.85, 112.2), ('Thuyền Chài', 8.167, 113.3),
]
TS_SCALE = 0.4  # the inset was drawn at 40%

def fit_inset(inset_rings):
    """inset = t + TS_SCALE * true, in the base file's Mercator units. Vote for t, refine on inliers,
    and check every control point."""
    cents = [(sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)) for r in inset_rings]
    ctrl = [(mpx(lon), mpy(lat)) for _, lat, lon in TS_CONTROL]
    k = TS_SCALE
    def km_off(t):
        return [min(math.dist((t[0] + k * q[0], t[1] + k * q[1]), c) for c in cents) / k * KM_PER_MERC_UNIT_EQ for q in ctrl]
    best = None
    for q in ctrl:
        for c in cents:
            t = (c[0] - k * q[0], c[1] - k * q[1])
            cost = sum(min(v, 15) for v in km_off(t))
            if best is None or cost < best[0]: best = (cost, t)
    t = best[1]
    for _ in range(5):
        pairs = []
        for q in ctrl:
            pr = (t[0] + k * q[0], t[1] + k * q[1])
            c = min(cents, key=lambda c: math.dist(pr, c))
            if math.dist(pr, c) / k * KM_PER_MERC_UNIT_EQ < 8: pairs.append((q, c))
        t = (sum(c[0] - k * q[0] for q, c in pairs) / len(pairs), sum(c[1] - k * q[1] for q, c in pairs) / len(pairs))
    off = km_off(t)
    assert len(pairs) == len(ctrl) and max(off) < 7, off
    return t, off

# ---------------------------------------------------------------- Natural Earth
def topo_decode(path):
    T = json.loads(Path(path).read_text())
    sc, tr = T['transform']['scale'], T['transform']['translate']
    arcs = []
    for a in T['arcs']:
        x = y = 0; pts = []
        for dx, dy in a:
            x += dx; y += dy
            pts.append(proj(x * sc[0] + tr[0], max(-85.0, min(85.0, y * sc[1] + tr[1]))))
        arcs.append(pts)
    def ring(ix):
        out = []
        for i in ix:
            seg = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(seg if not out else seg[1:])
        return out
    geoms = []
    for g in T['objects']['countries']['geometries']:
        if g['type'] not in ('Polygon', 'MultiPolygon'): continue
        polys = g['arcs'] if g['type'] == 'MultiPolygon' else [g['arcs']]
        shp = []
        for P_ in polys:
            rings = [ring(r) for r in P_]
            if len(rings[0]) >= 4: shp.append(Polygon(rings[0], [r for r in rings[1:] if len(r) >= 4]))
        geoms.append({'name': g['properties']['name'], 'id': g.get('id'), 'geom': unary_union([p.buffer(0) for p in shp]),
                      'arcs': [abs(i) if i >= 0 else ~i for P_ in polys for r in P_ for i in r]})
    return geoms, arcs

# The map reaches about 1,250 km beyond Vietnam and China: the fog is solid by about 1,100 km,
# so nothing further could ever be seen.
VIS_KM = 1250

def to_polys(geom, min_area=0.0):
    """Each polygon as its list of rings (outer first, then holes), so the app can cull per polygon."""
    out = []
    polys = [geom] if isinstance(geom, Polygon) else list(getattr(geom, 'geoms', []))
    for p in polys:
        if not isinstance(p, Polygon) or p.is_empty or p.area < min_area: continue
        out.append([list(p.exterior.coords)] + [list(h.coords) for h in p.interiors])
    return out

def to_lines(geom):
    if geom.is_empty: return []
    if isinstance(geom, LineString): return [list(geom.coords)]
    out = []
    for g in getattr(geom, 'geoms', []): out.extend(to_lines(g))
    return out

# ---------------------------------------------------------------- China's 34 units
def china_geoms(admin1_path, countries):
    """Each unit's shape in world units: the 31 mainland units from Natural Earth admin-1,
    Hong Kong, Macau and Taiwan from the Natural Earth country layer."""
    G = json.loads(Path(admin1_path).read_text(encoding='utf-8'))
    geoms = {}
    for f in G['features']:
        pr = f['properties']
        if pr.get('adm0_a3') != 'CHN': continue
        code = china_table.NE_ISO[pr['iso_3166_2']]
        g = f['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        shp = []
        for rings in polys:
            pts = [[proj(lon, lat) for lon, lat in r] for r in rings]
            if len(pts[0]) >= 4: shp.append(Polygon(pts[0], [h for h in pts[1:] if len(h) >= 4]))
        geoms[code] = unary_union([p.buffer(0) for p in shp])
    missing = set(china_table.NE_ISO.values()) - set(geoms)
    assert not missing, missing
    by_id = {c['id']: c for c in countries}
    for code, cid in china_table.NE_COUNTRY.items(): geoms[code] = by_id[cid]['geom']
    # Guangdong and the two special administrative regions come from different layers: cut the
    # regions out of Guangdong so that their shared edges are identical.
    geoms['44'] = geoms['44'].difference(geoms['81']).difference(geoms['82']).buffer(0)
    return geoms

def segments(rings):
    """Every edge of the rounded rings as an unordered key, for finding shared borders."""
    keys = set()
    for r in rings:
        for i in range(len(r)):
            a, b = r[i], r[(i + 1) % len(r)]
            if a != b: keys.add((a, b) if a < b else (b, a))
    return keys

def colouring(nodes, nb, k, balanced=True):
    """Give each node one of k colours so that no two neighbours share one. Balanced: the least-used
    free colour, so every colour appears about equally. Backtracks if the greedy pass gets stuck."""
    order = sorted(nodes, key=lambda c: (-len(nb[c]), str(c)))
    col, used = {}, [0] * k
    def go(i):
        if i == len(order): return True
        c = order[i]
        taken = {col.get(n) for n in nb[c]}
        for x in sorted((x for x in range(k) if x not in taken), key=lambda x: (used[x], x) if balanced else x):
            col[c] = x; used[x] += 1
            if go(i + 1): return True
            used[x] -= 1; del col[c]
        return False
    assert go(0)
    return col

def build_china(admin1_path, countries, vn_app, gaps, cores):
    geoms = china_geoms(admin1_path, countries)
    # Along the Vietnamese border, Natural Earth and the app's Vietnam disagree by a few km.
    # Guangxi and Yunnan give up what overlaps Vietnam and take the slivers in between, so that
    # the two countries meet exactly.
    pieces = [] if gaps.is_empty else list(getattr(gaps, 'geoms', [gaps]))
    taken = []
    for code in ('45', '53'):
        g = geoms[code]
        near = [q for q in pieces if q.distance(g) < 1.5]
        taken += near
        if near: g = unary_union([g, *near]).buffer(0)
        geoms[code] = g.difference(vn_app).buffer(0)
    units = china_table.check()
    for u in units:
        g = geoms[u['c']]
        # The published area (china_table.AREA), checked against the drawn shape: on the equal-area
        # map, square world units times KU² are square kilometres.
        drawn = g.area * KU * KU
        if abs(drawn / u['area'] - 1) > 0.10: print(f"  {u['en']}: drawn {drawn:,.0f} km², published {u['area']:,} km²")
        u['d'] = encode([r for poly in to_polys(g) for r in poly])
        rings = parse_rings(u['d'])
        main = max(rings, key=ring_area)
        u['box'] = bbox(main)
        # The label point is the centre of the largest circle that fits inside the main polygon;
        # sz is that circle's diameter (the app shows the name once sz is wide enough on screen).
        poly = max((Polygon(q[0], q[1:]) for q in to_polys(g)), key=lambda q: q.area)
        pt = polylabel(poly, tolerance=1.0)
        u['lab'] = [round(pt.x), round(pt.y)]
        u['sz'] = round(2 * poly.boundary.distance(pt), 1)
        u['capXY'] = P(u['capLL'][1], u['capLL'][0]) if u['capLL'] else None
        del u['capLL']
        for poly in to_polys(g):
            assert not any(core.contains(Polygon(poly[0]).representative_point()) for core in cores), u['en']
    # Neighbours share at least one edge. Hong Kong and Macau touch Guangdong by construction.
    segs = {u['c']: segments(parse_rings(u['d'])) for u in units}
    nb = {u['c']: set() for u in units}
    codes = [u['c'] for u in units]
    for i, a in enumerate(codes):
        for b in codes[i + 1:]:
            if segs[a] & segs[b]: nb[a].add(b); nb[b].add(a)
    for a, b in china_table.EXTRA_NEIGHBOURS: nb[a].add(b); nb[b].add(a)
    col = colouring(codes, nb, 5)
    by = {u['c']: u for u in units}
    for u in units:
        u['nb'] = sorted(nb[u['c']], key=lambda c: by[c]['stt'])
        u['col'] = col[u['c']]
    mainland = [u['c'] for u in units if u['c'] not in china_table.NE_COUNTRY]
    shared = set.union(*[segs[a] & segs[b] for a in codes for b in codes if a < b]) if codes else set()
    outline_geom = unary_union([geoms[c] for c in mainland]).buffer(0)
    outline_lines = outline_geom.boundary
    loose = 0
    for c in mainland:
        for (a, b) in segs[c] - shared:
            if LineString([a, b]).distance(outline_lines) > 0.6: loose += 1
    print(f'China: {sum(len(segs[c]) for c in codes):,} edges, {len(shared):,} shared by two units, {loose} inner edges without a twin')
    regions = [dict(r) for r in china_table.REGIONS]
    for i, r in enumerate(regions):
        us = [u for u in units if u['r'] == i]
        r['pop'] = sum(u['pop'] for u in us)
        r['area'] = sum(u['area'] for u in us)
        x0 = min(u['box'][0] for u in us); y0 = min(u['box'][1] for u in us)
        x1 = max(u['box'][0] + u['box'][2] for u in us); y1 = max(u['box'][1] + u['box'][3] for u in us)
        r['bbox'] = [x0, y0, x1 - x0, y1 - y0]
    allb = [p for u in units for r in parse_rings(u['d']) for p in r]
    mainb = [p for u in units if u['c'] in mainland for r in parse_rings(u['d']) for p in r]
    return {
        'regions': regions, 'units': units, 'area': sum(u['area'] for u in units),
        'outline': encode([r for poly in to_polys(outline_geom) for r in poly]),
        'outline2': encode([r for c in china_table.NE_COUNTRY for poly in to_polys(geoms[c]) for r in poly]),
        'bbox': bbox(allb), 'mainland_bbox': bbox(mainb),
    }, geoms, taken

# ---------------------------------------------------------------- the other countries: shape and one or two cities
# Natural Earth names -> the names shown, for the countries near enough to be seen.
COUNTRY_NAMES = {
    'Laos': 'Laos', 'Cambodia': 'Cambodia', 'Thailand': 'Thailand', 'Myanmar': 'Myanmar', 'Malaysia': 'Malaysia',
    'Singapore': 'Singapore', 'Brunei': 'Brunei', 'Indonesia': 'Indonesia', 'Philippines': 'Philippines',
    'Mongolia': 'Mongolia', 'Russia': 'Russia', 'Kazakhstan': 'Kazakhstan', 'Kyrgyzstan': 'Kyrgyzstan',
    'Tajikistan': 'Tajikistan', 'Uzbekistan': 'Uzbekistan', 'Afghanistan': 'Afghanistan', 'Pakistan': 'Pakistan',
    'India': 'India', 'Nepal': 'Nepal', 'Bhutan': 'Bhutan', 'Bangladesh': 'Bangladesh', 'Sri Lanka': 'Sri Lanka',
    'North Korea': 'North Korea', 'South Korea': 'South Korea', 'Japan': 'Japan', 'Iran': 'Iran',
    'Turkmenistan': 'Turkmenistan', 'Siachen Glacier': 'Siachen Glacier',
}
# Each country's capital, and for some one more city (name, lat, lon). Kept only where the map reaches.
CITIES = [
    ('Vientiane', 17.9757, 102.6331), ('Luang Prabang', 19.8856, 102.1347),
    ('Phnom Penh', 11.5564, 104.9282), ('Siem Reap', 13.3671, 103.8448),
    ('Bangkok', 13.7563, 100.5018), ('Chiang Mai', 18.7883, 98.9853),
    ('Naypyidaw', 19.7633, 96.0785), ('Yangon', 16.8409, 96.1735),
    ('Kuala Lumpur', 3.1390, 101.6869), ('Kota Kinabalu', 5.9804, 116.0735),
    ('Singapore', 1.3521, 103.8198), ('Bandar Seri Begawan', 4.9031, 114.9398),
    ('Manila', 14.5995, 120.9842), ('Davao', 7.1907, 125.4553),
    ('Medan', 3.5952, 98.6722), ('Pontianak', -0.0263, 109.3425),
    ('Ulaanbaatar', 47.8864, 106.9057),
    ('Pyongyang', 39.0392, 125.7625), ('Seoul', 37.5665, 126.9780), ('Busan', 35.1796, 129.0756),
    ('Tokyo', 35.6762, 139.6503), ('Fukuoka', 33.5904, 130.4017),
    ('Vladivostok', 43.1155, 131.8855), ('Irkutsk', 52.2870, 104.3050),
    ('Astana', 51.1694, 71.4491), ('Almaty', 43.2220, 76.8512),
    ('Bishkek', 42.8746, 74.5698), ('Dushanbe', 38.5598, 68.7870), ('Tashkent', 41.2995, 69.2401),
    ('Kabul', 34.5553, 69.2075), ('Islamabad', 33.6844, 73.0479), ('Lahore', 31.5204, 74.3587),
    ('New Delhi', 28.6139, 77.2090), ('Kolkata', 22.5726, 88.3639),
    ('Kathmandu', 27.7172, 85.3240), ('Thimphu', 27.4728, 89.6390), ('Dhaka', 23.8103, 90.4125),
    ('Colombo', 6.9271, 79.8612), ('Ashgabat', 37.9601, 58.3261), ('Mashhad', 36.2605, 59.6168),
]

# ---------------------------------------------------------------- main build
def main(world_atlas_dir, admin1_path):
    check_table()
    D = json.loads(BASE.read_text(encoding='utf-8'))
    BY = {p['c']: p for p in D['provinces']}

    # 1. Regions in Atlat order: old 0 (TD&MN) ↔ old 1 (ĐBSH) swap places; the rest keep their index.
    remap = {0: 1, 1: 0, 2: 2, 3: 3, 4: 4, 5: 5}
    for p in D['provinces']: p['r'] = remap[p['r']]
    for stt, code, area, pop in TABLE:
        p = BY[code]; p['stt'], p['area'], p['pop'] = stt, area, pop
    for i, (a, b) in enumerate(REGION_SPANS):
        assert all(BY[code]['r'] == i for stt, code, *_ in TABLE if a <= stt <= b), i
    D['provinces'].sort(key=lambda p: p['stt'])

    # Names as in the Atlat table.
    hue = BY['46']
    hue.update({'n': 'Thừa Thiên Huế', 'alt': ['Huế', 'Thừa Thiên - Huế', 'TT Huế', 'Thành phố Huế'], 'city': False, 'cap': 'Huế'})
    hcm = BY['79']
    hcm.update({'n': 'TP. Hồ Chí Minh', 'alt': ['Hồ Chí Minh', 'Hồ Chí Minh City', 'Thành phố Hồ Chí Minh', 'TP HCM']})
    for p in D['provinces']:
        p['note'] = NOTES.get(p['c'], '')
        p['to'] = merged_into_en(p['to'])
        p.pop('k', None)

    # 2. Trường Sa back to its true position, still in the base file's Mercator units.
    ts = next(i for i in D['insets'] if i['kind'] == 'ts')
    fx, fy, fw, fh = ts['frame']
    inside = lambda r: all(fx <= x <= fx + fw and fy <= y <= fy + fh for x, y in r)
    kh_rings = parse_rings(BY['56']['d'])
    t, off = fit_inset([r for r in kh_rings if inside(r)])
    print(f'Trường Sa inset: t=({t[0]:.1f}, {t[1]:.1f}), control points within {min(off):.1f}–{max(off):.1f} km')
    untransform = lambda r: [((x - t[0]) / TS_SCALE, (y - t[1]) / TS_SCALE) for x, y in r] if inside(r) else r
    ts_mask = [inside(r) for r in kh_rings]
    BY['56']['d'] = encode([untransform(r) for r in kh_rings])
    D['outline'] = encode([untransform(r) for r in parse_rings(D['outline'])])
    hs = next(i for i in D['insets'] if i['kind'] == 'hs')
    hx, hy, hw, hh = hs['frame']
    in_hs = lambda pt: hx <= pt[0] <= hx + hw and hy <= pt[1] <= hy + hh
    hs_pts_m = [p for r in parse_rings(BY['48']['d']) for p in r if in_hs(p)]
    mainland_m = [p for q in D['provinces'] for i, r in enumerate(parse_rings(q['d']))
                  if not (q['c'] == '56' and ts_mask[i]) and not all(in_hs(v) for v in r) for p in r]

    # 3. Everything into the equal-area projection. Shared vertices stay shared, so neighbours still
    #    meet exactly; label sizes are scaled by how much each province's area changed.
    conv = lambda r: [from_merc(x, y) for x, y in r]
    for p in D['provinces']:
        old = parse_rings(p['d'])
        new = [conv(r) for r in old]
        p['d'] = encode(new)
        mo, mn = max(old, key=ring_area), max(parse_rings(p['d']), key=ring_area)
        p['sz'] = round(p['sz'] * math.sqrt(ring_area(mn) / max(ring_area(mo), 1e-9)), 1)
        p['lab'] = [round(v) for v in from_merc(*p['lab'])]
        if p.get('capXY'): p['capXY'] = [round(v) for v in from_merc(*p['capXY'])]
    hue['capXY'] = P(107.5905, 16.4637)
    D['outline'] = encode([conv(r) for r in parse_rings(D['outline'])])
    kh_new = parse_rings(BY['56']['d'])
    ts_box = bbox([p for r, m in zip(kh_new, ts_mask) if m for p in r])
    hs_box = bbox([P(*m_to_ll(*p)) for p in hs_pts_m])
    country_box = bbox([from_merc(*p) for p in mainland_m])
    D['archipelagos'] = [
        {'code': '48', 'name': 'Hoàng Sa Archipelago', 'en': 'Paracel Islands', 'of': 'Đà Nẵng', 'box': hs_box},
        {'code': '56', 'name': 'Trường Sa Archipelago', 'en': 'Spratly Islands', 'of': 'Khánh Hòa', 'box': ts_box},
    ]
    del D['insets']
    for p in D['provinces']:
        p['box'] = bbox(max(parse_rings(p['d']), key=ring_area))
    for i, r in enumerate(REGIONS):
        boxes = [p['box'] for p in D['provinces'] if p['r'] == i]
        x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
        x1 = max(b[0] + b[2] for b in boxes); y1 = max(b[1] + b[3] for b in boxes)
        r['bbox'] = [x0, y0, x1 - x0, y1 - y0]
    D['regions'] = REGIONS

    # 4. The neighbourhood, within VIS_KM of Vietnam and China.
    countries, arcs = topo_decode(Path(world_atlas_dir) / 'countries-50m.json')
    by_id = {c['id']: c for c in countries}
    vn_app = unary_union([Polygon(r).buffer(0) for p in D['provinces'] for r in parse_rings(p['d']) if len(r) >= 3])
    vis = unary_union([vn_app, by_id['156']['geom']]).simplify(20).buffer(VIS_KM / KU, 8)
    vn_ne = next(c for c in countries if c['name'] == 'Vietnam')
    others = [c for c in countries if c['name'] != 'Vietnam' and c['geom'].intersects(vis)]
    neigh = unary_union([c['geom'].intersection(vis) for c in others])
    # Guard: no foreign polygon may sit on Hoàng Sa or Trường Sa (Palawan and Borneo lie just east
    # and south of Trường Sa, so test the archipelagos' cores, not their bounding boxes).
    llbox = lambda lo0, la0, lo1, la1: Polygon([proj(lo0, la0), proj(lo1, la0), proj(lo1, la1), proj(lo0, la1)])
    cores = [llbox(111.0, 17.3, 113.0, 15.6), llbox(111.5, 11.6, 116.5, 7.4)]
    for c in others:
        for g in getattr(c['geom'], 'geoms', [c['geom']]):
            assert not any(core.contains(g.representative_point()) for core in cores), c['name']
    # Fill the slivers where Natural Earth's border and Vietnam's own border disagree, without
    # spilling into the sea: only where Natural Earth has land, close to both Vietnam and a neighbour.
    near = 12  # world units ≈ 7 km
    filler = vn_app.buffer(near).intersection(neigh.buffer(near)).intersection(unary_union([neigh, vn_ne['geom']]))
    gaps = filler.difference(vn_app).difference(neigh)
    print(f'border sliver filler: {gaps.area * KU * KU:.0f} km² before simplification')

    # 4b. China's 34 units.
    D['china'], cgeoms, taken = build_china(admin1_path, countries, vn_app, gaps, cores)
    china_ids = {'156', *china_table.NE_COUNTRY.values()}

    # 4c. The other countries, as shapes. Slivers along Vietnam's border go to the nearest one.
    unnamed = sorted(c['name'] for c in others if c['id'] not in china_ids and c['name'] not in COUNTRY_NAMES)
    if unnamed: print('not drawn (no name in COUNTRY_NAMES):', ', '.join(unnamed))
    shown = [c for c in others if c['id'] not in china_ids and c['name'] in COUNTRY_NAMES]
    clipped = {c['id']: c['geom'].intersection(vis) for c in shown}
    for q in (getattr(gaps, 'geoms', [gaps]) if not gaps.is_empty else []):
        if any(q.equals(x) for x in taken): continue
        cid = min(clipped, key=lambda i: clipped[i].distance(q))
        clipped[cid] = unary_union([clipped[cid], q])
    touches_core = lambda g: g.distance(vn_app) < 50 or g.distance(by_id['156']['geom']) < 50
    out_countries = []
    for c in shown:
        g = clipped[c['id']]
        tol, min_area = (1.2, 3) if touches_core(g) else (2.5, 40)
        polys = to_polys(g.simplify(tol, preserve_topology=True), min_area=min_area)
        if not polys: continue
        out_countries.append({'n': COUNTRY_NAMES[c['name']], 'id': c['id'], 'd': encode([r for poly in polys for r in poly]), 'geom': g})
    # International borders between the neighbours (arcs shared by two countries other than
    # Vietnam and China, whose own outlines the app draws).
    users = {}
    for ci, c in enumerate(countries):
        for a in set(c['arcs']): users.setdefault(a, set()).add(ci)
    skip = {countries.index(vn_ne)} | {i for i, c in enumerate(countries) if c['id'] in china_ids}
    border_lines = []
    for a, us in users.items():
        if len(us) >= 2 and not (us & skip) and any(countries[u] in others for u in us):
            ln = LineString(arcs[a]).intersection(vis)
            border_lines.extend(to_lines(ln.simplify(1.5)))

    # 5. Jade tones: one of eight for every province, unit and country, never shared by two
    #    neighbours, so whichever country is being learned, the others read as a varied jade.
    nodes, geo = [], {}
    for p in D['provinces']: nodes.append(('v', p['c'])); geo[('v', p['c'])] = unary_union([Polygon(r).buffer(0) for r in parse_rings(p['d']) if len(r) >= 3])
    for u in D['china']['units']: nodes.append(('c', u['c'])); geo[('c', u['c'])] = cgeoms[u['c']]
    for c in out_countries: nodes.append(('x', c['id'])); geo[('x', c['id'])] = c['geom']
    nbj = {n: set() for n in nodes}
    for p in D['provinces']:
        for q in p['nb']: nbj[('v', p['c'])].add(('v', q))
    for u in D['china']['units']:
        for q in u['nb']: nbj[('c', u['c'])].add(('c', q))
    simp = {n: geo[n].simplify(2) for n in nodes}
    grown = {n: simp[n].buffer(3) for n in nodes}
    bb = {n: grown[n].bounds for n in nodes}
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            if a[0] == b[0] and a[0] in 'vc': continue          # already known from the tables
            A, Q = bb[a], bb[b]
            if A[2] < Q[0] or Q[2] < A[0] or A[3] < Q[1] or Q[3] < A[1]: continue
            if grown[a].intersects(simp[b]): nbj[a].add(b); nbj[b].add(a)
    jade = colouring(nodes, nbj, 8)
    for p in D['provinces']: p['jade'] = jade[('v', p['c'])]
    for u in D['china']['units']: u['jade'] = jade[('c', u['c'])]
    for c in out_countries:
        c['jade'] = jade[('x', c['id'])]
        del c['geom'], c['id']

    # 6. Labels and decoration. Everything outside Vietnam uses standard English names; the sea
    #    Vietnam calls Biển Đông uses Vietnam's official English name, East Sea.
    in_vis = lambda lon, lat: vis.contains(Point(proj(lon, lat)))
    labels = [
        ('CHINA', 104.5, 37.6, True), ('LAOS', 103.1, 19.7), ('CAMBODIA', 104.8, 12.9), ('THAILAND', 101.4, 15.7),
        ('MYANMAR', 96.2, 21.6), ('MALAYSIA', 102.2, 4.6), ('MALAYSIA', 116.6, 5.4), ('BRUNEI', 114.5, 4.35),
        ('PHILIPPINES', 121.6, 16.7), ('INDONESIA', 113.6, -0.9), ('INDIA', 79.5, 22.5), ('INDIA', 93.4, 25.6),
        ('MONGOLIA', 103.5, 46.5), ('RUSSIA', 126.5, 52.3), ('RUSSIA', 96.0, 54.5), ('KAZAKHSTAN', 76.5, 47.2),
        ('KYRGYZSTAN', 74.8, 41.6), ('TAJIKISTAN', 71.0, 38.8), ('UZBEKISTAN', 64.5, 41.6), ('AFGHANISTAN', 66.0, 34.2),
        ('PAKISTAN', 69.8, 29.6), ('TURKMENISTAN', 59.6, 39.0), ('IRAN', 59.4, 33.2), ('NEPAL', 84.0, 28.3), ('BHUTAN', 90.4, 27.45), ('BANGLADESH', 89.6, 24.6),
        ('SRI LANKA', 80.7, 7.8), ('NORTH KOREA', 126.9, 40.4), ('SOUTH KOREA', 128.0, 36.4), ('JAPAN', 133.6, 35.2),
    ]
    D['deco'] = {
        'countries': [dict({'t': t, 'at': P(lo, la)}, **({'big': True} if big else {})) for t, lo, la, *rest in labels for big in [bool(rest and rest[0])] if in_vis(lo, la)],
        'islands': [{'t': 'Borneo', 'at': P(113.4, 1.4)}],
        'water': [
            {'t': 'East Sea', 'at': P(113.3, 13.6), 'big': True}, {'t': 'Gulf of Tonkin', 'at': P(108.1, 20.25)},
            {'t': 'Gulf of Thailand', 'at': P(101.75, 10.4)}, {'t': 'Andaman Sea', 'at': P(96.6, 11.6)},
            {'t': 'Sulu Sea', 'at': P(120.0, 8.6)}, {'t': 'Pacific Ocean', 'at': P(129.5, 14.0), 'big': True},
            {'t': 'Philippine Sea', 'at': P(127.5, 21.5)},
            {'t': 'Yellow Sea', 'at': P(123.2, 35.4)}, {'t': 'East China Sea', 'at': P(125.0, 28.6)},
            {'t': 'Sea of Japan', 'at': P(134.6, 40.2)}, {'t': 'Bay of Bengal', 'at': P(88.0, 15.5)},
            {'t': 'Taiwan Strait', 'at': P(119.4, 24.6)},
        ],
        'capitals': [{'t': t, 'at': P(lon, lat)} for t, lat, lon in CITIES if in_vis(lon, lat)],
        'grid': {'lon': list(range(50, 162, 2)), 'lat': list(range(-12, 72, 2)), 'tropic': 23.4367},
    }

    tb = [min(country_box[0], hs_box[0], ts_box[0]), min(country_box[1], hs_box[1], ts_box[1])]
    tb += [max(country_box[0] + country_box[2], hs_box[0] + hs_box[2], ts_box[0] + ts_box[2]) - tb[0],
           max(country_box[1] + country_box[3], hs_box[1] + hs_box[3], ts_box[1] + ts_box[3]) - tb[1]]
    ex0, ey0, ex1, ey1 = vis.bounds
    vn_area = round(sum(r['area'] for r in REGIONS), 1)
    D['meta'].update({
        'built': B['meta'].get('built'),
        'snapshot': 'The 63 provincial-level units, grouped and numbered as in the statistics table of the Atlat Địa lí Việt Nam',
        'stats': 'Area and 2021 population from the Atlat table (Niên giám thống kê 2021, NXB Thống kê 2022)',
        'china_snapshot': 'China’s 34 provincial-level units, numbered and grouped as in the China Statistical Yearbook',
        'china_stats': 'Population from the Seventh National Population Census, 1 November 2020 (NBS Communiqué No. 3); Hong Kong, Macau and Taiwan as quoted there. Areas as published by each provincial government and statistics office.',
        'china_boundaries': 'Natural Earth 1:50m admin-1 (public domain); Hong Kong, Macau and Taiwan from Natural Earth 1:50m countries',
        'proj': ALB, 'vn_area': vn_area,
        'country_bbox': [round(v) for v in country_box],
        'territory_bbox': [round(v) for v in tb],
        'extent': [math.floor(ex0), math.floor(ey0), math.ceil(ex1 - ex0), math.ceil(ey1 - ey0)],
    })
    for k in ('w', 'h'): D['meta'].pop(k, None)
    D['countries'] = out_countries
    D['borders'] = encode(border_lines)
    D.pop('others', None); D.pop('land', None)

    blob = json.dumps(D, ensure_ascii=False, separators=(',', ':'))
    html = INDEX.read_text(encoding='utf-8')
    new, n = re.subn(r'(<script id="vn-data" type="application/json">).*?(</script>)',
                     lambda m: m.group(1) + blob + m.group(2), html, count=1, flags=re.S)
    assert n == 1
    INDEX.write_text(new, encoding='utf-8')
    ca = D['china']['area']
    print(f'China: {ca:,} km² = {ca / vn_area:.1f} × Vietnam ({vn_area:,} km², Atlat)')
    print(f'wrote {len(blob):,} bytes of map data: provinces {sum(len(p["d"]) for p in D["provinces"]):,}, '
          f'China {sum(len(u["d"]) for u in D["china"]["units"]):,} + outline {len(D["china"]["outline"]) + len(D["china"]["outline2"]):,}, '
          f'countries {sum(len(c["d"]) for c in out_countries):,} ({len(out_countries)}), borders {len(D["borders"]):,} ({len(border_lines)} lines), '
          f'cities {len(D["deco"]["capitals"])}')

if __name__ == '__main__':
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
