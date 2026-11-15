#!/usr/bin/env python3
"""Make the small Chinese fonts the app uses for China's names (dev only; the app ships the result).

    python3 make_cn_fonts.py path/to/NotoSansSC[wght].ttf path/to/ukai.ttc

Needs fontTools and brotli (pip install fonttools brotli). The two source fonts are the ones kept
in the Hanzi Grid repository (CHINESE-HANDWRITING-PRACTICE-1/fonts/source/). Writes, next to
this script:
  noto-sans-sc-400-subset.woff2   print style (黑体), Regular weight
  noto-sans-sc-600-subset.woff2   print style, SemiBold weight (map labels)
      Both cut down to the characters china_table.py uses, plus Latin letters, digits,
      punctuation and the pinyin tone letters.
  ukai-cn-subset.woff2            AR PL UKai CN (楷体, the handwriting style), the Chinese
                                  characters only (the facts panel shows each name in it)
  FONTS.txt                       the notice both licences ask for
Why so small: the full fonts are 17 MB each; these are under 60 KB together, so the app stays
quick to install and fits in the offline cache.
"""
import datetime
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTCollection, TTFont
from fontTools.varLib import instancer

import china_table

ROOT = Path(__file__).resolve().parent
TODAY = datetime.date.today().isoformat()
HANZI = china_table.all_characters()
# Latin letters, digits, punctuation and the pinyin tone letters (ā á ǎ à … ǖ ǘ ǚ ǜ).
LATIN_RANGES = [(0x20, 0x7E), (0xA0, 0xA0), (0xB7, 0xB7), (0xC0, 0xFF), (0x100, 0x101), (0x112, 0x113), (0x12A, 0x12B),
                (0x143, 0x148), (0x14C, 0x14D), (0x16A, 0x16B), (0x1CD, 0x1DC), (0x1F8, 0x1F9), (0x1E3E, 0x1E3F),
                (0x2010, 0x2027), (0x3001, 0x3002)]
LATIN = [chr(cp) for a, b in LATIN_RANGES for cp in range(a, b + 1)]


def cut_down(font, characters, notice):
    """Keep only `characters` in `font` and write `notice` into its description (name ID 10)."""
    options = subset.Options()
    options.name_IDs = ['*']           # keep every name record: the licences ask to keep the copyright
    options.name_languages = ['*']
    options.hinting = False
    options.notdef_outline = True
    options.layout_features = ['*']
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=[ord(ch) for ch in characters])
    subsetter.subset(font)
    font['name'].setName(notice, 10, 3, 1, 0x409)
    font.flavor = 'woff2'
    return font


def main(noto_path, ukai_path):
    notices = []
    for weight, style in ((400, 'Regular'), (600, 'SemiBold')):
        noto = TTFont(noto_path)
        noto = instancer.instantiateVariableFont(noto, {'wght': weight}, updateFontNames=True)
        have = {chr(cp) for cp in noto.getBestCmap()}
        wanted = [ch for ch in HANZI + LATIN if ch in have]
        missing = [ch for ch in HANZI if ch not in have]
        notice = (f'Modified version of Noto Sans SC for Map Learning: the {style} ({weight}) weight of the variable font, '
                  f'reduced on {TODAY} with fontTools to {len(HANZI)} Chinese characters (China’s provinces, capitals and '
                  'abbreviations) plus Latin, pinyin and punctuation; hinting removed; saved as WOFF2. '
                  'Licensed under the SIL Open Font License 1.1 (see OFL-notosanssc.txt).')
        out = ROOT / f'noto-sans-sc-{weight}-subset.woff2'
        cut_down(noto, wanted, notice).save(str(out))
        print(f'{out.name}: {out.stat().st_size / 1024:.1f} KB, missing {missing or "none"}')
        notices.append((out.name, notice))

    kai = TTCollection(ukai_path).fonts[0]       # face 0 is "AR PL UKai CN"
    have = {chr(cp) for cp in kai.getBestCmap()}
    missing = [ch for ch in HANZI if ch not in have]
    notice = (f'Modified version of AR PL UKai CN for Map Learning: reduced on {TODAY} with fontTools to {len(HANZI)} '
              'Chinese characters (China’s provinces, capitals and abbreviations); hinting removed; saved as WOFF2. '
              'Licensed under the Arphic Public License (see LICENSE-ukai.txt).')
    out = ROOT / 'ukai-cn-subset.woff2'
    cut_down(kai, [ch for ch in HANZI if ch in have], notice).save(str(out))
    print(f'{out.name}: {out.stat().st_size / 1024:.1f} KB, missing {missing or "none"}')
    notices.append((out.name, notice))

    text = ['Fonts used by Map Learning for China’s names', '=' * 46, '',
            'The map labels and the table use Be Vietnam Pro (OFL.txt) for Vietnamese and English, and the two',
            'Noto Sans SC files below for Chinese characters and pinyin. The facts panel shows each Chinese name in',
            'the KaiTi (handwriting) style of AR PL UKai CN, the font Hanzi Grid prints its practice sheets with.',
            'All three are MODIFIED (cut-down) copies, made by make_cn_fonts.py from the full fonts kept in the',
            'Hanzi Grid repository (CHINESE-HANDWRITING-PRACTICE-1/fonts/source/). The same notice is written into',
            'each file’s "Description" name record.', '']
    for name, notice in notices: text += [name, '  ' + notice, '']
    text += ['Noto Sans SC: Copyright 2014-2021 Adobe (https://github.com/notofonts/noto-cjk), SIL Open Font License 1.1',
             '  (OFL-notosanssc.txt). The name does not use the Reserved Font Name "Source".',
             'AR PL UKai CN: Copyright 1999 Arphic Technology Co., Ltd., Arphic Public License (LICENSE-ukai.txt, unchanged).', '']
    (ROOT / 'FONTS.txt').write_text('\n'.join(text), encoding='utf-8')
    print(f'FONTS.txt written; {len(HANZI)} Chinese characters: {"".join(HANZI)}')


if __name__ == '__main__':
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
