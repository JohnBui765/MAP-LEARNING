#!/usr/bin/env python3
"""China's 34 provincial-level units: the data table used by build_data.py and make_cn_fonts.py.

Order and grouping follow the China Statistical Yearbook (National Bureau of Statistics), which
lists the 31 mainland units region by region: North, Northeast, East, South Central, Southwest,
Northwest. Hong Kong, Macau and Taiwan, which the census does not cover, come last as a seventh
group. The number (stt) is the row in that order, 1-34, like the Atlat number for Vietnam.

Population: the Seventh National Population Census, 1 November 2020 (NBS, Communiqué No. 3),
in persons. The communiqué's total for the mainland, 1,411,778,724, is the 31 units plus
2,000,000 servicemen counted separately; check() verifies that the 31 figures add up to it.
The figures for Hong Kong, Macau and Taiwan are the ones the communiqué quotes from those
territories' own statistics offices (end of 2020).

Codes are the two-digit GB/T 2260 codes. Pinyin carries tone marks. Vietnamese names are the
usual Hán-Việt forms.
"""
import unicodedata

REGIONS = [
    {'num': 'I', 'zh': '华北', 'py': 'Huáběi', 'en': 'North China', 'short': 'North', 'vi': 'Hoa Bắc'},
    {'num': 'II', 'zh': '东北', 'py': 'Dōngběi', 'en': 'Northeast China', 'short': 'Northeast', 'vi': 'Đông Bắc'},
    {'num': 'III', 'zh': '华东', 'py': 'Huádōng', 'en': 'East China', 'short': 'East', 'vi': 'Hoa Đông'},
    {'num': 'IV', 'zh': '中南', 'py': 'Zhōngnán', 'en': 'South Central China', 'short': 'South Central', 'vi': 'Trung Nam'},
    {'num': 'V', 'zh': '西南', 'py': 'Xīnán', 'en': 'Southwest China', 'short': 'Southwest', 'vi': 'Tây Nam'},
    {'num': 'VI', 'zh': '西北', 'py': 'Xīběi', 'en': 'Northwest China', 'short': 'Northwest', 'vi': 'Tây Bắc'},
    {'num': 'VII', 'zh': '港澳台', 'py': 'Gǎng-Ào-Tái', 'en': 'Hong Kong, Macau and Taiwan', 'short': 'HK, Macau, Taiwan',
     'vi': 'Hồng Kông, Ma Cao, Đài Loan', 'note': 'Administered separately; not covered by the census.'},
]

TYPES = {
    'province': {'en': 'Province', 'zh': '省', 'py': 'Shěng'},
    'municipality': {'en': 'Municipality', 'zh': '直辖市', 'py': 'Zhíxiáshì'},
    'autonomous': {'en': 'Autonomous region', 'zh': '自治区', 'py': 'Zìzhìqū'},
    'sar': {'en': 'Special administrative region', 'zh': '特别行政区', 'py': 'Tèbié Xíngzhèngqū'},
}

# (code, short name, full name, pinyin, pinyin of the full name, English, Vietnamese,
#  abbreviations [(character, pinyin), ...], type, capital (zh, pinyin, English, Vietnamese, lat, lon) or None,
#  population 2020, note)
UNITS = [
    # I. North China 华北
    ('11', '北京', '北京市', 'Běijīng', 'Běijīng Shì', 'Beijing', 'Bắc Kinh', [('京', 'Jīng')], 'municipality', None, 21893095,
     'Capital of the People’s Republic of China.'),
    ('12', '天津', '天津市', 'Tiānjīn', 'Tiānjīn Shì', 'Tianjin', 'Thiên Tân', [('津', 'Jīn')], 'municipality', None, 13866009, ''),
    ('13', '河北', '河北省', 'Héběi', 'Héběi Shěng', 'Hebei', 'Hà Bắc', [('冀', 'Jì')], 'province',
     ('石家庄', 'Shíjiāzhuāng', 'Shijiazhuang', 'Thạch Gia Trang', 38.0428, 114.5149), 74610235, 'Surrounds Beijing and Tianjin.'),
    ('14', '山西', '山西省', 'Shānxī', 'Shānxī Shěng', 'Shanxi', 'Sơn Tây', [('晋', 'Jìn')], 'province',
     ('太原', 'Tàiyuán', 'Taiyuan', 'Thái Nguyên', 37.8706, 112.5489), 34915616, 'Not to be confused with Shǎnxī 陕西 (Shaanxi), to its west.'),
    ('15', '内蒙古', '内蒙古自治区', 'Nèi Měnggǔ', 'Nèi Měnggǔ Zìzhìqū', 'Inner Mongolia', 'Nội Mông', [('蒙', 'Měng')], 'autonomous',
     ('呼和浩特', 'Hūhéhàotè', 'Hohhot', 'Hô Hòa Hạo Đặc', 40.8414, 111.7519), 24049155, 'Autonomous region of the Mongols.'),
    # II. Northeast China 东北
    ('21', '辽宁', '辽宁省', 'Liáoníng', 'Liáoníng Shěng', 'Liaoning', 'Liêu Ninh', [('辽', 'Liáo')], 'province',
     ('沈阳', 'Shěnyáng', 'Shenyang', 'Thẩm Dương', 41.8057, 123.4315), 42591407, ''),
    ('22', '吉林', '吉林省', 'Jílín', 'Jílín Shěng', 'Jilin', 'Cát Lâm', [('吉', 'Jí')], 'province',
     ('长春', 'Chángchūn', 'Changchun', 'Trường Xuân', 43.8171, 125.3235), 24073453, ''),
    ('23', '黑龙江', '黑龙江省', 'Hēilóngjiāng', 'Hēilóngjiāng Shěng', 'Heilongjiang', 'Hắc Long Giang', [('黑', 'Hēi')], 'province',
     ('哈尔滨', 'Hā’ěrbīn', 'Harbin', 'Cáp Nhĩ Tân', 45.8038, 126.5350), 31850088, 'The northernmost unit; named after the Amur (Black Dragon) river.'),
    # III. East China 华东
    ('31', '上海', '上海市', 'Shànghǎi', 'Shànghǎi Shì', 'Shanghai', 'Thượng Hải', [('沪', 'Hù')], 'municipality', None, 24870895,
     'The most populous city proper in China.'),
    ('32', '江苏', '江苏省', 'Jiāngsū', 'Jiāngsū Shěng', 'Jiangsu', 'Giang Tô', [('苏', 'Sū')], 'province',
     ('南京', 'Nánjīng', 'Nanjing', 'Nam Kinh', 32.0603, 118.7969), 84748016, ''),
    ('33', '浙江', '浙江省', 'Zhèjiāng', 'Zhèjiāng Shěng', 'Zhejiang', 'Chiết Giang', [('浙', 'Zhè')], 'province',
     ('杭州', 'Hángzhōu', 'Hangzhou', 'Hàng Châu', 30.2741, 120.1551), 64567588, ''),
    ('34', '安徽', '安徽省', 'Ānhuī', 'Ānhuī Shěng', 'Anhui', 'An Huy', [('皖', 'Wǎn')], 'province',
     ('合肥', 'Héféi', 'Hefei', 'Hợp Phì', 31.8206, 117.2272), 61027171, ''),
    ('35', '福建', '福建省', 'Fújiàn', 'Fújiàn Shěng', 'Fujian', 'Phúc Kiến', [('闽', 'Mǐn')], 'province',
     ('福州', 'Fúzhōu', 'Fuzhou', 'Phúc Châu', 26.0745, 119.2965), 41540086, 'Faces Taiwan across the Taiwan Strait.'),
    ('36', '江西', '江西省', 'Jiāngxī', 'Jiāngxī Shěng', 'Jiangxi', 'Giang Tây', [('赣', 'Gàn')], 'province',
     ('南昌', 'Nánchāng', 'Nanchang', 'Nam Xương', 28.6820, 115.8579), 45188635, ''),
    ('37', '山东', '山东省', 'Shāndōng', 'Shāndōng Shěng', 'Shandong', 'Sơn Đông', [('鲁', 'Lǔ')], 'province',
     ('济南', 'Jǐnán', 'Jinan', 'Tế Nam', 36.6512, 117.1201), 101527453, 'Second most populous unit.'),
    # IV. South Central China 中南
    ('41', '河南', '河南省', 'Hénán', 'Hénán Shěng', 'Henan', 'Hà Nam', [('豫', 'Yù')], 'province',
     ('郑州', 'Zhèngzhōu', 'Zhengzhou', 'Trịnh Châu', 34.7466, 113.6254), 99365519, 'Third most populous unit.'),
    ('42', '湖北', '湖北省', 'Húběi', 'Húběi Shěng', 'Hubei', 'Hồ Bắc', [('鄂', 'È')], 'province',
     ('武汉', 'Wǔhàn', 'Wuhan', 'Vũ Hán', 30.5928, 114.3055), 57752557, ''),
    ('43', '湖南', '湖南省', 'Húnán', 'Húnán Shěng', 'Hunan', 'Hồ Nam', [('湘', 'Xiāng')], 'province',
     ('长沙', 'Chángshā', 'Changsha', 'Trường Sa', 28.2282, 112.9388), 66444864, 'Its capital Chángshā 长沙 shares its Hán-Việt name with Trường Sa; the two are unrelated.'),
    ('44', '广东', '广东省', 'Guǎngdōng', 'Guǎngdōng Shěng', 'Guangdong', 'Quảng Đông', [('粤', 'Yuè')], 'province',
     ('广州', 'Guǎngzhōu', 'Guangzhou', 'Quảng Châu', 23.1291, 113.2644), 126012510, 'The most populous unit of China.'),
    ('45', '广西', '广西壮族自治区', 'Guǎngxī', 'Guǎngxī Zhuàngzú Zìzhìqū', 'Guangxi', 'Quảng Tây', [('桂', 'Guì')], 'autonomous',
     ('南宁', 'Nánníng', 'Nanning', 'Nam Ninh', 22.8170, 108.3665), 50126804, 'Autonomous region of the Zhuang. Borders Vietnam (Hà Giang, Cao Bằng, Lạng Sơn, Quảng Ninh).'),
    ('46', '海南', '海南省', 'Hǎinán', 'Hǎinán Shěng', 'Hainan', 'Hải Nam', [('琼', 'Qióng')], 'province',
     ('海口', 'Hǎikǒu', 'Haikou', 'Hải Khẩu', 20.0444, 110.1989), 10081232,
     'Island province since 1988, part of Guangdong before. On this map Hoàng Sa and Trường Sa stay with Đà Nẵng and Khánh Hòa.'),
    # V. Southwest China 西南
    ('50', '重庆', '重庆市', 'Chóngqìng', 'Chóngqìng Shì', 'Chongqing', 'Trùng Khánh', [('渝', 'Yú')], 'municipality', None, 32054159,
     'Municipality since 1997, carved out of Sichuan.'),
    ('51', '四川', '四川省', 'Sìchuān', 'Sìchuān Shěng', 'Sichuan', 'Tứ Xuyên', [('川', 'Chuān'), ('蜀', 'Shǔ')], 'province',
     ('成都', 'Chéngdū', 'Chengdu', 'Thành Đô', 30.5728, 104.0668), 83674866, ''),
    ('52', '贵州', '贵州省', 'Guìzhōu', 'Guìzhōu Shěng', 'Guizhou', 'Quý Châu', [('黔', 'Qián'), ('贵', 'Guì')], 'province',
     ('贵阳', 'Guìyáng', 'Guiyang', 'Quý Dương', 26.6470, 106.6302), 38562148, ''),
    ('53', '云南', '云南省', 'Yúnnán', 'Yúnnán Shěng', 'Yunnan', 'Vân Nam', [('滇', 'Diān'), ('云', 'Yún')], 'province',
     ('昆明', 'Kūnmíng', 'Kunming', 'Côn Minh', 25.0389, 102.7183), 47209277, 'Borders Vietnam (Điện Biên, Lai Châu, Lào Cai, Hà Giang), Laos and Myanmar.'),
    ('54', '西藏', '西藏自治区', 'Xīzàng', 'Xīzàng Zìzhìqū', 'Tibet', 'Tây Tạng', [('藏', 'Zàng')], 'autonomous',
     ('拉萨', 'Lāsà', 'Lhasa', 'Lhasa', 29.6520, 91.1721), 3648100, 'Autonomous region of the Tibetans; the least populous unit of the mainland.'),
    # VI. Northwest China 西北
    ('61', '陕西', '陕西省', 'Shǎnxī', 'Shǎnxī Shěng', 'Shaanxi', 'Thiểm Tây', [('陕', 'Shǎn'), ('秦', 'Qín')], 'province',
     ('西安', 'Xī’ān', 'Xi’an', 'Tây An', 34.3416, 108.9398), 39528999, 'Written Shaanxi in English to tell it from Shānxī 山西; the pinyin is Shǎnxī.'),
    ('62', '甘肃', '甘肃省', 'Gānsù', 'Gānsù Shěng', 'Gansu', 'Cam Túc', [('甘', 'Gān'), ('陇', 'Lǒng')], 'province',
     ('兰州', 'Lánzhōu', 'Lanzhou', 'Lan Châu', 36.0611, 103.8343), 25019831, ''),
    ('63', '青海', '青海省', 'Qīnghǎi', 'Qīnghǎi Shěng', 'Qinghai', 'Thanh Hải', [('青', 'Qīng')], 'province',
     ('西宁', 'Xīníng', 'Xining', 'Tây Ninh', 36.6171, 101.7782), 5923957, 'Named after Qinghai Lake, the largest lake in China.'),
    ('64', '宁夏', '宁夏回族自治区', 'Níngxià', 'Níngxià Huízú Zìzhìqū', 'Ningxia', 'Ninh Hạ', [('宁', 'Níng')], 'autonomous',
     ('银川', 'Yínchuān', 'Yinchuan', 'Ngân Xuyên', 38.4872, 106.2309), 7202654, 'Autonomous region of the Hui.'),
    ('65', '新疆', '新疆维吾尔自治区', 'Xīnjiāng', 'Xīnjiāng Wéiwú’ěr Zìzhìqū', 'Xinjiang', 'Tân Cương', [('新', 'Xīn')], 'autonomous',
     ('乌鲁木齐', 'Wūlǔmùqí', 'Ürümqi', 'Urumqi', 43.8256, 87.6168), 25852345, 'Autonomous region of the Uyghurs; the largest unit by area.'),
    # VII. Hong Kong, Macau and Taiwan 港澳台 (administered separately)
    ('81', '香港', '香港特别行政区', 'Xiānggǎng', 'Xiānggǎng Tèbié Xíngzhèngqū', 'Hong Kong', 'Hồng Kông', [('港', 'Gǎng')], 'sar', None, 7474200,
     'Special administrative region since 1997, a British colony before. Population at the end of 2020 from its Census and Statistics Department, as quoted in the census communiqué.'),
    ('82', '澳门', '澳门特别行政区', 'Àomén', 'Àomén Tèbié Xíngzhèngqū', 'Macau', 'Ma Cao', [('澳', 'Ào')], 'sar', None, 683218,
     'Special administrative region since 1999, under Portuguese administration before. Population at the end of 2020 from its Statistics and Census Service, as quoted in the census communiqué.'),
    ('71', '台湾', '台湾省', 'Táiwān', 'Táiwān Shěng', 'Taiwan', 'Đài Loan', [('台', 'Tái')], 'province',
     ('台北', 'Táiběi', 'Taipei', 'Đài Bắc', 25.0330, 121.5654), 23561236,
     'Listed by the People’s Republic as a province; governed separately by the Republic of China (Taiwan). Population at the end of 2020 from Taiwan’s statistics, as quoted in the census communiqué.'),
]
REGION_SPANS = [(1, 5), (6, 8), (9, 15), (16, 21), (22, 26), (27, 31), (32, 34)]
MAINLAND_TOTAL = 1409778724          # the 31 units; the communiqué total 1,411,778,724 adds 2,000,000 servicemen

# Natural Earth admin-1 codes (iso_3166_2) for the 31 mainland units.
NE_ISO = {
    'CN-BJ': '11', 'CN-TJ': '12', 'CN-HE': '13', 'CN-SX': '14', 'CN-NM': '15',
    'CN-LN': '21', 'CN-JL': '22', 'CN-HL': '23',
    'CN-SH': '31', 'CN-JS': '32', 'CN-ZJ': '33', 'CN-AH': '34', 'CN-FJ': '35', 'CN-JX': '36', 'CN-SD': '37',
    'CN-HA': '41', 'CN-HB': '42', 'CN-HN': '43', 'CN-GD': '44', 'CN-GX': '45', 'CN-HI': '46',
    'CN-CQ': '50', 'CN-SC': '51', 'CN-GZ': '52', 'CN-YN': '53', 'CN-XZ': '54',
    'CN-SN': '61', 'CN-GS': '62', 'CN-QH': '63', 'CN-NX': '64', 'CN-XJ': '65',
}
# Natural Earth country ids (world-atlas) for the three units outside the admin-1 layer.
NE_COUNTRY = {'81': '344', '82': '446', '71': '158'}
# Neighbours that the two data sets cannot find by shared edges.
EXTRA_NEIGHBOURS = [('44', '81'), ('44', '82')]
# Area in km²: the figure each provincial government publishes (to the 10 km² most give); Hong Kong,
# Macau and Taiwan from their own statistics offices. build_data.py measures the drawn shapes on the
# equal-area map and reports any unit more than 10% away (Ningxia, whose Natural Earth boundary is too
# small at this scale, and Macau, which is too small for it).
AREA = {
    '11': 16410, '12': 11966, '13': 188800, '14': 156700, '15': 1183000, '21': 148600, '22': 187400,
    '23': 473000, '31': 6341, '32': 107200, '33': 105500, '34': 140100, '35': 124000, '36': 166900,
    '37': 155800, '41': 167000, '42': 185900, '43': 211800, '44': 179700, '45': 237600, '46': 35400,
    '50': 82400, '51': 486000, '52': 176200, '53': 394100, '54': 1228400, '61': 205600, '62': 425800,
    '63': 722300, '64': 66400, '65': 1664900, '81': 1114, '82': 33, '71': 36197,
}
# Traditional-character spellings that differ from the simplified ones, so that a name typed on a
# traditional keyboard is accepted too.
TRADITIONAL = {
    '15': ['內蒙古'], '21': ['遼寧'], '23': ['黑龍江'], '32': ['江蘇'], '37': ['山東'], '44': ['廣東'],
    '45': ['廣西'], '50': ['重慶'], '52': ['貴州'], '53': ['雲南'], '61': ['陝西'], '62': ['甘肅'],
    '64': ['寧夏'], '82': ['澳門'], '71': ['臺灣', '台灣'],
}


def units():
    """The table as a list of dicts, numbered 1-34 and grouped into the seven regions."""
    out = []
    for i, row in enumerate(UNITS, 1):
        code, zh, full, py, full_py, en, vi, ab, kind, cap, pop, note = row
        r = next(k for k, (a, b) in enumerate(REGION_SPANS) if a <= i <= b)
        out.append({
            'c': code, 'zh': zh, 'full': full, 'py': py, 'fullPy': full_py, 'en': en, 'vi': vi,
            'ab': [list(a) for a in ab], 'type': kind, 'typeEn': TYPES[kind]['en'], 'city': cap is None,
            'cap': cap[0] if cap else '', 'capPy': cap[1] if cap else '', 'capEn': cap[2] if cap else '', 'capVi': cap[3] if cap else '',
            'capLL': [cap[4], cap[5]] if cap else None,
            'r': r, 'stt': i, 'pop': pop, 'area': AREA[code], 'note': note, 'tw': TRADITIONAL.get(code, []),
        })
    return out


def syllables(py):
    """Rough syllable count: one per run of vowels; spaces, apostrophes and hyphens separate runs."""
    s = unicodedata.normalize('NFD', py.lower()).replace('ü', 'v')
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    n, invowel = 0, False
    for ch in s:
        v = ch in 'aeiouv'
        if v and not invowel: n += 1
        invowel = v
    return n


def all_characters():
    """Every Chinese character the app shows for China (for the font subsets)."""
    chars = set()
    for u in units():
        chars.update(u['zh'] + u['full'] + u['cap'] + ''.join(a[0] for a in u['ab']))
    for r in REGIONS: chars.update(r['zh'])
    for t in TYPES.values(): chars.update(t['zh'])
    chars.update('中国省份楷体')
    return sorted(ch for ch in chars if '一' <= ch <= '鿿')


def check():
    us = units()
    assert len(us) == 34 and len({u['c'] for u in us}) == 34
    assert sum(u['pop'] for u in us if u['c'] not in NE_COUNTRY) == MAINLAND_TOTAL
    assert set(NE_ISO.values()) == {u['c'] for u in us if u['c'] not in NE_COUNTRY}
    for u in us:
        assert syllables(u['py']) == len(u['zh']), (u['zh'], u['py'])
        assert syllables(u['fullPy']) == len(u['full']), (u['full'], u['fullPy'])
        if u['cap']: assert syllables(u['capPy']) == len(u['cap']), (u['cap'], u['capPy'])
        for ch, py in u['ab']: assert syllables(py) == 1, (ch, py)
    assert REGION_SPANS[-1][1] == 34
    assert set(AREA) == {u['c'] for u in us}
    return us


if __name__ == '__main__':
    us = check()
    print(f'{len(us)} units, mainland total {MAINLAND_TOTAL:,}, {len(all_characters())} distinct characters')
    for u in us: print(f"{u['stt']:>2} {u['c']} {u['zh']:　<4} {u['py']:<14} {u['en']:<15} {u['vi']:<16} {u['pop']:>12,}")
