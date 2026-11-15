#!/usr/bin/env python3
"""Build the map data embedded in index.html (<script id="vn-data">).

Inputs
  vietnam63-base.json  Vietnam's 63 provinces as first built from geoBoundaries (OCHA ROAP /
                             Government of Viet Nam district boundaries, 2020, CC BY 3.0 IGO), in the
                             app's Mercator units, with Trường Sa drawn in a 40% inset.
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
  3. Neighbouring countries come from Natural Earth over a wide window (they fade into fog in the
     app), with coastlines and international borders as separate line layers.
  4. China's 34 provincial-level units (china_table.py) get their shapes from Natural Earth: the
     31 mainland units from the admin-1 layer, Hong Kong, Macau and Taiwan from the country layer.
     Along the Vietnamese border they are trimmed and stretched to meet the app's own Vietnam.
"""
import json, math, re, sys
from pathlib import Path

from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon, box
from shapely.ops import polylabel, unary_union

import china_table

ROOT = Path(__file__).resolve().parent
BASE = ROOT / 'vietnam63-base.json'
INDEX = ROOT / 'index.html'

# ---------------------------------------------------------------- projection (same as the app)
B = json.loads(BASE.read_text(encoding='utf-8'))
PROJ = B['meta']['proj']
def merc(lat): return 180 / math.pi * math.log(math.tan(math.pi / 4 + lat * math.pi / 360))
def imerc(m): return (2 * math.atan(math.exp(m * math.pi / 180)) - math.pi / 2) * 180 / math.pi
def px(lon): return (lon - PROJ['lon0']) * PROJ['s']
def py(lat): return (PROJ['mtop'] - merc(lat)) * PROJ['s']
def lon_of(x): return x / PROJ['s'] + PROJ['lon0']
def lat_of(y): return imerc(PROJ['mtop'] - y / PROJ['s'])
def P(lon, lat): return [round(px(lon)), round(py(lat))]
KM_PER_UNIT_EQ = 111.32 / PROJ['s']

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
    """inset = t + TS_SCALE * true. Vote for t, refine on inliers, and check every control point."""
    cents = [(sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)) for r in inset_rings]
    ctrl = [(px(lon), py(lat)) for _, lat, lon in TS_CONTROL]
    k = TS_SCALE
    def km_off(t):
        return [min(math.dist((t[0] + k * q[0], t[1] + k * q[1]), c) for c in cents) / k * KM_PER_UNIT_EQ for q in ctrl]
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
            if math.dist(pr, c) / k * KM_PER_UNIT_EQ < 8: pairs.append((q, c))
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
            pts.append((px(x * sc[0] + tr[0]), py(max(-85.0, min(85.0, y * sc[1] + tr[1])))))
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

# Window drawn around Vietnam and China; everything beyond it is solid fog in the app.
EXT_LON = (71.5, 137.0)
EXT_LAT = (-3.0, 55.5)

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
    """Each unit's shape in the app's units: the 31 mainland units from Natural Earth admin-1,
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
            pts = [[(px(lon), py(lat)) for lon, lat in r] for r in rings]
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

def five_colours(codes, nb):
    """Give each unit one of the five atlas colours so that no two neighbours share one."""
    order = sorted(codes, key=lambda c: -len(nb[c]))
    col = {}
    def go(i):
        if i == len(order): return True
        c = order[i]
        for k in range(5):
            if all(col.get(n) != k for n in nb[c]):
                col[c] = k
                if go(i + 1): return True
                del col[c]
        return False
    assert go(0)
    return col

def build_china(admin1_path, countries, vn_app, gaps, cores):
    geoms = china_geoms(admin1_path, countries)
    # Along the Vietnamese border, Natural Earth and the app's Vietnam disagree by a few km.
    # Guangxi and Yunnan give up what overlaps Vietnam and take the slivers in between, so that
    # the two countries meet exactly.
    pieces = [] if gaps.is_empty else list(getattr(gaps, 'geoms', [gaps]))
    for code in ('45', '53'):
        g = geoms[code]
        near = [q for q in pieces if q.distance(g) < 1.5]
        if near: g = unary_union([g, *near]).buffer(0)
        geoms[code] = g.difference(vn_app).buffer(0)
    units = china_table.check()
    for u in units:
        g = geoms[u['c']]
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
    col = five_colours(codes, nb)
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
        x0 = min(u['box'][0] for u in us); y0 = min(u['box'][1] for u in us)
        x1 = max(u['box'][0] + u['box'][2] for u in us); y1 = max(u['box'][1] + u['box'][3] for u in us)
        r['bbox'] = [x0, y0, x1 - x0, y1 - y0]
    allb = [p for u in units for r in parse_rings(u['d']) for p in r]
    mainb = [p for u in units if u['c'] in mainland for r in parse_rings(u['d']) for p in r]
    return {
        'regions': regions, 'units': units,
        'outline': encode([r for poly in to_polys(outline_geom) for r in poly]),
        'outline2': encode([r for c in china_table.NE_COUNTRY for poly in to_polys(geoms[c]) for r in poly]),
        'bbox': bbox(allb), 'mainland_bbox': bbox(mainb),
    }, geoms

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
    hue.update({'n': 'Thừa Thiên Huế', 'alt': ['Huế', 'Thừa Thiên - Huế', 'TT Huế', 'Thành phố Huế'], 'city': False,
                'cap': 'Huế', 'capXY': P(107.5905, 16.4637)})
    hcm = BY['79']
    hcm.update({'n': 'TP. Hồ Chí Minh', 'alt': ['Hồ Chí Minh', 'Hồ Chí Minh City', 'Thành phố Hồ Chí Minh', 'TP HCM']})
    for p in D['provinces']:
        p['note'] = NOTES.get(p['c'], '')
        p['to'] = merged_into_en(p['to'])
        p.pop('k', None)

    # 2. Trường Sa back to its true position (Khánh Hòa's rings and the national outline).
    ts = next(i for i in D['insets'] if i['kind'] == 'ts')
    fx, fy, fw, fh = ts['frame']
    inside = lambda r: all(fx <= x <= fx + fw and fy <= y <= fy + fh for x, y in r)
    kh_rings = parse_rings(BY['56']['d'])
    t, off = fit_inset([r for r in kh_rings if inside(r)])
    print(f'Trường Sa inset: t=({t[0]:.1f}, {t[1]:.1f}), control points within {min(off):.1f}–{max(off):.1f} km')
    untransform = lambda r: [((x - t[0]) / TS_SCALE, (y - t[1]) / TS_SCALE) for x, y in r] if inside(r) else r
    kh_new = [untransform(r) for r in kh_rings]
    BY['56']['d'] = encode(kh_new)
    out_rings = [untransform(r) for r in parse_rings(D['outline'])]
    D['outline'] = encode(out_rings)
    ts_pts = [p for r0, r in zip(kh_rings, kh_new) if inside(r0) for p in r]
    hs = next(i for i in D['insets'] if i['kind'] == 'hs')
    hx, hy, hw, hh = hs['frame']
    hs_pts = [p for r in parse_rings(BY['48']['d']) for p in r if hx <= p[0] <= hx + hw and hy <= p[1] <= hy + hh]
    ts_box, hs_box = bbox(ts_pts), bbox(hs_pts)
    D['archipelagos'] = [
        {'code': '48', 'name': 'Hoàng Sa Archipelago', 'en': 'Paracel Islands', 'of': 'Đà Nẵng', 'box': hs_box},
        {'code': '56', 'name': 'Trường Sa Archipelago', 'en': 'Spratly Islands', 'of': 'Khánh Hòa', 'box': ts_box},
    ]
    del D['insets']

    # Province geometry facts the app needs.
    for p in D['provinces']:
        rings = parse_rings(p['d'])
        p['box'] = bbox(max(rings, key=ring_area))
    for i, r in enumerate(REGIONS):
        boxes = [p['box'] for p in D['provinces'] if p['r'] == i]
        x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
        x1 = max(b[0] + b[2] for b in boxes); y1 = max(b[1] + b[3] for b in boxes)
        r['bbox'] = [x0, y0, x1 - x0, y1 - y0]
    D['regions'] = REGIONS

    # 3. Neighbouring countries.
    countries, arcs = topo_decode(Path(world_atlas_dir) / 'countries-50m.json')
    ext = box(px(EXT_LON[0]), py(EXT_LAT[1]), px(EXT_LON[1]), py(EXT_LAT[0]))
    vn_ne = next(c for c in countries if c['name'] == 'Vietnam')
    others = [c for c in countries if c['name'] != 'Vietnam' and c['geom'].intersects(ext)]
    vn_app = unary_union([Polygon(r).buffer(0) for p in D['provinces'] for r in parse_rings(p['d']) if len(r) >= 3])
    neigh = unary_union([c['geom'].intersection(ext) for c in others])
    # Guard: no foreign polygon may sit on Hoàng Sa or Trường Sa (Palawan and Borneo lie just east
    # and south of Trường Sa, so test the archipelagos' cores, not their bounding boxes).
    cores = [box(px(111.0), py(17.3), px(113.0), py(15.6)), box(px(111.5), py(11.6), px(116.5), py(7.4))]
    for c in others:
        for g in getattr(c['geom'], 'geoms', [c['geom']]):
            assert not any(core.contains(g.representative_point()) for core in cores), c['name']
    # Fill the slivers where Natural Earth's border and Vietnam's own border disagree, without
    # spilling into the sea: only where Natural Earth has land, close to both Vietnam and a neighbour.
    near = 12  # world units ≈ 7 km
    filler = vn_app.buffer(near).intersection(neigh.buffer(near)).intersection(unary_union([neigh, vn_ne['geom']]))
    gaps = filler.difference(vn_app).difference(neigh)
    print(f'border sliver filler: {gaps.area:.0f} unit² ({gaps.area * KM_PER_UNIT_EQ ** 2:.0f} km² before simplification)')
    land = unary_union([neigh, filler]).simplify(1.2, preserve_topology=True)
    land_polys = to_polys(land, min_area=3)
    # International borders between neighbours (arcs shared by two non-Vietnam countries).
    users = {}
    for ci, c in enumerate(countries):
        for a in set(c['arcs']): users.setdefault(a, set()).add(ci)
    vn_i = countries.index(vn_ne)
    border_lines = []
    # China's own outline is drawn solid from its units, so its borders are left out here.
    cn_i = next(i for i, c in enumerate(countries) if c['id'] == '156')
    for a, us in users.items():
        if len(us) >= 2 and vn_i not in us and cn_i not in us and any(countries[u] in others for u in us):
            ln = LineString(arcs[a]).intersection(ext)
            border_lines.extend(to_lines(ln.simplify(1.2)))

    # 3b. China's 34 units.
    D['china'], _ = build_china(admin1_path, countries, vn_app, gaps, cores)

    # 4. Labels and decoration. Everything outside Vietnam uses standard English names; the sea
    #    Vietnam calls Biển Đông uses Vietnam's official English name, East Sea.
    D['deco'] = {
        'countries': [
            {'t': 'CHINA', 'at': P(104.5, 41.2), 'big': True}, {'t': 'LAOS', 'at': P(103.1, 19.7)},
            {'t': 'CAMBODIA', 'at': P(104.8, 12.9)}, {'t': 'THAILAND', 'at': P(101.4, 15.7)},
            {'t': 'MYANMAR', 'at': P(96.2, 21.6)}, {'t': 'MALAYSIA', 'at': P(102.2, 4.6)},
            {'t': 'MALAYSIA', 'at': P(116.6, 5.4)}, {'t': 'BRUNEI', 'at': P(114.5, 4.35)},
            {'t': 'PHILIPPINES', 'at': P(121.6, 16.7)}, {'t': 'INDONESIA', 'at': P(113.6, -0.9)},
            {'t': 'INDIA', 'at': P(79.5, 22.5)}, {'t': 'INDIA', 'at': P(93.4, 25.6)},
            {'t': 'MONGOLIA', 'at': P(103.5, 46.5)}, {'t': 'RUSSIA', 'at': P(126.5, 52.3)},
            {'t': 'KAZAKHSTAN', 'at': P(76.5, 47.2)}, {'t': 'KYRGYZSTAN', 'at': P(74.8, 41.6)},
            {'t': 'NEPAL', 'at': P(84.0, 28.3)}, {'t': 'BHUTAN', 'at': P(90.4, 27.45)},
            {'t': 'BANGLADESH', 'at': P(89.6, 24.6)}, {'t': 'NORTH KOREA', 'at': P(126.9, 40.4)},
            {'t': 'SOUTH KOREA', 'at': P(128.0, 36.4)}, {'t': 'JAPAN', 'at': P(133.6, 35.2)},
        ],
        'islands': [
            {'t': 'Borneo', 'at': P(113.4, 1.4)},
        ],
        'water': [
            {'t': 'East Sea', 'at': P(113.3, 13.6), 'big': True}, {'t': 'Gulf of Tonkin', 'at': P(108.1, 20.25)},
            {'t': 'Gulf of Thailand', 'at': P(101.75, 10.4)}, {'t': 'Andaman Sea', 'at': P(96.6, 11.6)},
            {'t': 'Sulu Sea', 'at': P(120.0, 8.6)}, {'t': 'Pacific Ocean', 'at': P(126.0, 16.0), 'big': True},
            {'t': 'Yellow Sea', 'at': P(123.2, 35.4)}, {'t': 'East China Sea', 'at': P(125.0, 28.6)},
            {'t': 'Sea of Japan', 'at': P(134.6, 40.2)}, {'t': 'Bay of Bengal', 'at': P(88.0, 15.5)},
            {'t': 'Taiwan Strait', 'at': P(119.4, 24.6)},
        ],
        'capitals': [
            {'t': 'Vientiane', 'at': P(102.6331, 17.9757)}, {'t': 'Phnom Penh', 'at': P(104.9160, 11.5564)},
            {'t': 'Bangkok', 'at': P(100.5018, 13.7563)}, {'t': 'Naypyidaw', 'at': P(96.13, 19.76)},
            {'t': 'Kuala Lumpur', 'at': P(101.6869, 3.139)}, {'t': 'Bandar Seri Begawan', 'at': P(114.9398, 4.9031)},
            {'t': 'Manila', 'at': P(120.9842, 14.5995)}, {'t': 'Ulaanbaatar', 'at': P(106.9057, 47.8864)},
            {'t': 'Pyongyang', 'at': P(125.7625, 39.0392)}, {'t': 'Seoul', 'at': P(126.978, 37.5665)},
            {'t': 'New Delhi', 'at': P(77.209, 28.6139)}, {'t': 'Kathmandu', 'at': P(85.324, 27.7172)},
            {'t': 'Thimphu', 'at': P(89.6386, 27.4728)}, {'t': 'Dhaka', 'at': P(90.4125, 23.8103)},
            {'t': 'Bishkek', 'at': P(74.5698, 42.8746)},
        ],
        'grid': {'lon': list(range(72, 137, 2)), 'lat': list(range(-2, 56, 2)), 'tropic': 23.4367},
    }

    vx0, vy0, vw, vh = D['meta']['country_bbox']
    tb = [min(vx0, hs_box[0], ts_box[0]), min(vy0, hs_box[1], ts_box[1])]
    tb += [max(vx0 + vw, hs_box[0] + hs_box[2], ts_box[0] + ts_box[2]) - tb[0],
           max(vy0 + vh, hs_box[1] + hs_box[3], ts_box[1] + ts_box[3]) - tb[1]]
    ex0, ey0, ex1, ey1 = ext.bounds
    D['meta'].update({
        'built': B['meta'].get('built'),
        'snapshot': 'The 63 provincial-level units, grouped and numbered as in the statistics table of the Atlat Địa lí Việt Nam',
        'stats': 'Area and 2021 population from the Atlat table (Niên giám thống kê 2021, NXB Thống kê 2022)',
        'china_snapshot': 'China’s 34 provincial-level units, numbered and grouped as in the China Statistical Yearbook',
        'china_stats': 'Population from the Seventh National Population Census, 1 November 2020 (NBS Communiqué No. 3); Hong Kong, Macau and Taiwan as quoted there',
        'china_boundaries': 'Natural Earth 1:50m admin-1 (public domain); Hong Kong, Macau and Taiwan from Natural Earth 1:50m countries',
        'territory_bbox': [round(v) for v in tb],
        'extent': [round(ex0), round(ey0), round(ex1 - ex0), round(ey1 - ey0)],
    })
    for k in ('w', 'h'): D['meta'].pop(k, None)
    D['land'] = [encode(rings) for rings in land_polys]
    D['borders'] = encode(border_lines)
    D.pop('others', None)

    blob = json.dumps(D, ensure_ascii=False, separators=(',', ':'))
    html = INDEX.read_text(encoding='utf-8')
    new, n = re.subn(r'(<script id="vn-data" type="application/json">).*?(</script>)',
                     lambda m: m.group(1) + blob + m.group(2), html, count=1, flags=re.S)
    assert n == 1
    INDEX.write_text(new, encoding='utf-8')
    print(f'wrote {len(blob):,} bytes of map data: provinces {sum(len(p["d"]) for p in D["provinces"]):,}, '
          f'China {sum(len(u["d"]) for u in D["china"]["units"]):,} + outline {len(D["china"]["outline"]) + len(D["china"]["outline2"]):,}, '
          f'land {sum(map(len, D["land"])):,} ({len(land_polys)} polygons), borders {len(D["borders"]):,} ({len(border_lines)} lines)')

if __name__ == '__main__':
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
