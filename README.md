# Map Learning

A practice app for Vietnam's 63 provincial-level units, grouped and numbered as in the
statistics table of the *Atlat Địa lí Việt Nam*, with China's 34 provincial-level units drawn
north of them and named in Chinese with pinyin. It is built for the iPhone: install it on the
Home Screen and it works offline, like a native app. It also runs on a laptop.
Address: **https://johnbui765.github.io/MAP-LEARNING/**

- **Regions I–VI in the Atlat's order**, each named in English and Vietnamese, with the
  provinces numbered 1–63 as in the table. The **Table** tab shows the table itself (area and
  2021 population); tap a row to find it on the map.
- **Labels never overlap.** Province names and capital names are placed around each other;
  whatever does not fit waits until you zoom in. Small provinces show their Atlat number.
- **Made for fingers:** pinch, double-tap to zoom in, two-finger tap to zoom out, flick to
  glide. If a tap could mean more than one small province, the map zooms in instead of guessing.
- **China is the second country to learn**, in its six regions as the China Statistical Yearbook
  groups them (North, Northeast, East, South Central, Southwest, Northwest) plus Hong Kong, Macau
  and Taiwan. Every mode works for China: Daily review, Find it, Name it, Neighbours, Rebuild and
  Sprint, with its own progress and personal bests. Names are **typed, as in Hanzi Drill**: the
  pinyin with the tone keys under the box (ā á ǎ à mark the last syllable typed; tone numbers such
  as guang3dong1 work too), or the characters, simplified or traditional. Right letters with wrong
  tones show in orange and count as a miss. Tap a unit for its name in Chinese, pinyin, Vietnamese
  and English, its handwriting (KaiTi) form, capital, region, area and 2020 census population.
- **The country you learn is in colour, the other in jade, every other country in grey.** The chip
  at the end of the region row (or the Vietnam | China switch in Table, Practice and Progress)
  changes which country is learned. Vietnam and China swap: one in the Atlat colours, the other in
  eight tones of jade. Region borders are drawn heavier for the country being learned.
- **True size.** The map is drawn in an equal-area projection, so China is shown 29 times the size
  of Vietnam, as it is (a Mercator map makes it look about 41 times). Zoom out to see all of China.
- **The map is a circle** that holds Vietnam and China, centred near 106°E 32.5°N with a radius of
  about 3,100 km. The countries inside it (Laos, Cambodia, Thailand, Myanmar, India, Mongolia,
  Russia, Korea, Japan and others) are drawn as grey shapes with their capitals. Beyond its edge the
  mist thickens and covers every pixel, at every zoom, painted by the graphics chip; zoomed right
  out, you see the whole circle. Hoàng Sa and Trường Sa are at their true positions.

The app is in English; province names are in Vietnamese, and China's names in Chinese with pinyin.
Typed pinyin is checked by three files copied unchanged from Hanzi Drill (`pinyincheck.js`,
`pinyin.js`, `extract.js`, which come from Hanzi Grid); to update them, copy them again.

## Put it online (GitHub Pages)

1. Create a new public repository named `MAP-LEARNING` (GitHub writes a hyphen for the space).
2. Upload every file in this folder. All files sit at the top level, so there are no folders to keep.
3. In the repository, open Settings, then Pages. Under "Build and deployment", choose
   "Deploy from a branch", branch `main`, folder `/ (root)`, and save.
4. After a minute the app is at `https://johnbui765.github.io/MAP-LEARNING/`.

The app's identity on your devices is `/MAP-LEARNING/` (the manifest `id`), and its offline
cache (`map-learning-`) and saved progress (`map-learning.v1`) are named after the repository
too, so they never mix with your other apps on the same address. If the repository is ever
renamed, devices treat it as a different app. Always open the address with the capital letters
exactly as above.

## Install it

- **iPhone:** open the link in Safari, tap Share, then "Add to Home Screen".
- **Laptop:** open the link in Chrome or Edge and click the install icon in the address bar.

After the first visit it works without internet. If you installed an older version, remove it
from the Home Screen and add it again so iOS picks up the new icon and launch screen.

## Your progress

Progress is stored on each device separately. To move it, open Progress, then Details,
then "Back up progress", and use "Restore" on the other device. Coming from the earlier
Vietnam 63 app: back up your progress there and restore it here; the two apps keep separate
progress, and the old backup files are accepted.

## After editing any file

Change `VERSION` at the top of `sw.js` (for example to `PREFIX + 'v3'`). Otherwise installed
copies keep showing the cached version.

## Rebuilding the map data

The map data is embedded in `index.html`. `build_data.py` rebuilds it from
`vietnam63-base.json` (the provinces, stored in the old Mercator units and converted to the
equal-area projection), Natural Earth's countries (the neighbours, and Hong Kong, Macau and
Taiwan) and Natural Earth's admin-1 layer (China's 31 mainland units). It also finds the map's circle, gives
every province and unit its jade tone and checks China's published areas against the drawn shapes:

```sh
pip install shapely
npm pack world-atlas@2.0.2 && tar xzf world-atlas-2.0.2.tgz
curl -LO https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_1_states_provinces.geojson
python3 build_data.py package ne_50m_admin_1_states_provinces.geojson
```

The Atlat table (regions, numbers, area, population) is written out in the script and checked
against the table's region totals. China's table (names, pinyin, traditional spellings, capitals,
areas, 2020 census) is `china_table.py`, which checks itself (`python3 china_table.py`): the 31 mainland figures add up
to the census total, and every pinyin has one syllable per character. `make_splash.py
icon-1024.png` remakes the iPhone launch screens.

The three small Chinese fonts (`noto-sans-sc-*-subset.woff2`, `ukai-cn-subset.woff2`) are cut
from the full fonts kept in the Hanzi Grid repository with `make_cn_fonts.py` (needs
`pip install fonttools brotli`); `FONTS.txt` records what was changed, as the licences ask.

## Sources and licences

- Boundaries: district boundaries from OCHA ROAP and the Government of Viet Nam (2020),
  licensed CC BY 3.0 IGO, obtained through geoBoundaries (www.geoboundaries.org,
  William & Mary geoLab). Districts were merged into the 63 provinces and simplified
  to about 0.7 km.
- Regions, numbering, area and population: the statistics table of the Atlat Địa lí Việt Nam,
  quoting the Statistical Yearbook of Vietnam 2021 (Statistical Publishing House, 2022).
  English region names follow the General Statistics Office.
- Province codes: Decision 124/2004/QĐ-TTg. Boundary and status changes: Resolutions
  22/2003/QH11, 15/2008/QH12 and 175/2024/QH15. 2025 merger: Resolution 202/2025/QH15.
  Capitals: Atlat Địa lí Việt Nam.
- Neighbouring countries: Natural Earth 1:50m (public domain), via world-atlas, drawn as shapes
  with their capitals. Biển Đông is labelled East Sea, the name Vietnam uses in English; it is
  also known internationally as the South China Sea.
- Projection: Albers equal-area conic on the sphere, standard parallels 20°N and 45°N, centred on
  105°E; one world unit is about 0.62 km.
- China's units: boundaries from Natural Earth 1:50m admin-1 (public domain), with Hong Kong,
  Macau and Taiwan from the country layer; trimmed to Vietnam's own boundaries along the border.
  Natural Earth draws borders as administered on the ground. Numbered and grouped as in the
  China Statistical Yearbook. Population: Seventh National Population Census, 1 November 2020
  (National Bureau of Statistics, Communiqué No. 3); Hong Kong, Macau and Taiwan at the end of
  2020, as quoted there. Area: as published by each provincial government (Hong Kong, Macau and
  Taiwan by their statistics offices); the drawn shapes agree within a few per cent, except
  Ningxia, whose Natural Earth boundary is too small, and Macau. Names: simplified Chinese
  (with traditional spellings accepted when typed), Hanyu Pinyin, the usual Hán-Việt names,
  GB/T 2260 codes.
- Typefaces: Be Vietnam Pro, SIL Open Font License 1.1 (see `OFL.txt`); for Chinese, cut-down
  copies of Noto Sans SC (SIL Open Font License, `OFL-notosanssc.txt`) and AR PL UKai CN
  (Arphic Public License, `LICENSE-ukai.txt`), see `FONTS.txt`.
