// Typed pinyin: putting tone marks on syllables, and checking an answer against an entry.
// No browser APIs, so Node can test it.
//
// The learner types letters (nihao, ni hao, ni3hao3, nv3) and taps a tone key, which marks the
// last syllable typed (nǐ). Checking accepts tone marks or tone numbers, spaces, apostrophes
// and hyphens between syllables or none, ü written as ü, v or u:, and either the dictionary
// pinyin of the entry or the pinyin as said in the word (yǒu → you).
import { splitPinyin, SYLLABLES } from './pinyin.js';
import { chineseChars } from './extract.js';

const TONE_MARKS = { a: 'āáǎà', e: 'ēéěè', i: 'īíǐì', o: 'ōóǒò', u: 'ūúǔù', ü: 'ǖǘǚǜ' };

// A marked letter -> [plain letter, tone].
const MARKED = new Map();
for (const [base, marks] of Object.entries(TONE_MARKS)) [...marks].forEach((m, i) => MARKED.set(m, [base, i + 1]));

const plain = (ch) => (MARKED.get(ch) || [ch])[0];

// One syllable -> { base, tone }: the letters without a mark (ü kept as ü), and the tone 1–4,
// or 5 for neutral or none. A tone number 0–5 at the end is read too.
export function syllableParts(syllable) {
  let s = String(syllable ?? '').normalize('NFC').toLowerCase().trim();
  let tone = 5;
  const digit = s.match(/[0-5]$/);
  if (digit) {
    tone = digit[0] === '0' ? 5 : Number(digit[0]);
    s = s.slice(0, -1);
  }
  s = s.replace(/u:/g, 'ü').replace(/v/g, 'ü');
  let base = '';
  for (const ch of s) {
    const m = MARKED.get(ch);
    if (m) {
      base += m[0];
      tone = m[1];
    } else base += ch;
  }
  return { base, tone };
}

// Where the mark goes (the standard rule): on a or e when there is one; on o in "ou";
// otherwise on the last vowel (iu → u, ui → i).
export function markSyllable(letters, tone) {
  const { base } = syllableParts(letters);
  if (!(tone >= 1 && tone <= 4)) return base;
  let at = -1;
  if (base.includes('a')) at = base.indexOf('a');
  else if (base.includes('e')) at = base.indexOf('e');
  else if (base.includes('ou')) at = base.indexOf('o');
  else {
    for (let i = base.length - 1; i >= 0; i--) {
      if ('aeiouü'.includes(base[i])) {
        at = i;
        break;
      }
    }
  }
  if (at < 0) return base;
  return base.slice(0, at) + TONE_MARKS[base[at]][tone - 1] + base.slice(at + 1);
}

// The spelling the syllable table uses: ü is "v", except after j, q, x and y where it is "u".
function tableForm(base) {
  return base.replace(/([jqxy])ü/g, '$1u').replace(/ü/g, 'v');
}

// Puts a tone on the last syllable typed in a text field: "nihao" + 3 -> "nihǎo",
// "nǐhao" + 3 -> "nǐhǎo", "ni3" + 2 -> "ní", "nv" + 3 -> "nǚ". Tone 5 removes the mark.
export function applyToneToLast(text, tone) {
  const str = String(text ?? '').normalize('NFC');
  const m = str.match(/[a-zA-Z0-5:\u00c0-\u024f]+$/);
  if (!m) return str;
  const before = str.slice(0, str.length - m[0].length);
  const run = m[0].replace(/[0-5]$/, '').replace(/u:/gi, 'ü');
  if (!/[a-zA-Zü\u00c0-\u024f]/.test(run)) return str; // no letters to mark
  const chars = [...run];
  const bases = chars.map((ch) => plain(ch.toLowerCase()).replace('v', 'ü'));
  const base = bases.join('');
  let len = Math.min(6, base.length);
  for (; len > 1; len--) if (SYLLABLES.has(tableForm(base.slice(-len)))) break;
  const start = chars.length - len;
  return before + chars.slice(0, start).join('') + markSyllable(base.slice(start), tone);
}

// Only the letters, no marks, no spaces: for a loose comparison when the pinyin cannot be cut.
export function lettersOnly(text) {
  return [...String(text ?? '').normalize('NFC').toLowerCase().replace(/u:/g, 'ü')]
    .map((ch) => plain(ch))
    .join('')
    .replace(/v/g, 'ü')
    .replace(/[^a-zü]/g, '');
}

// The syllables of a pinyin text for a word, as { base, tone }, or null when it cannot be cut
// into one syllable per character.
export function toSyllables(text, chars) {
  const cleaned = String(text ?? '')
    .normalize('NFC')
    .replace(/u:/gi, 'ü')
    .replace(/[.?!,;:。？！，；：'’\-]/g, ' ');
  const syllables = splitPinyin(cleaned, chars);
  return syllables ? syllables.map(syllableParts) : null;
}

// Checks a typed answer against an entry: { correct, close, message, expected }.
// correct: letters and tones right (or letters right when tones are not required and none
// were typed). close: letters right but tones wrong or missing. Otherwise wrong.
export function gradePinyin(input, entry, { tonesRequired = true } = {}) {
  const chars = chineseChars(entry?.word || '');
  const forms = [entry?.pinyin, entry?.said].map((s) => String(s || '').trim()).filter(Boolean);
  const out = { correct: false, close: false, message: '', expected: forms[0] || '' };
  if (!forms.length || !String(input ?? '').trim()) return out;
  const typed = toSyllables(input, chars);
  if (!typed) {
    const letters = lettersOnly(input);
    if (letters && forms.some((f) => lettersOnly(f) === letters)) {
      out.close = true;
      out.message = 'Right letters: check the tones and how the syllables are cut';
    } else out.message = 'Not quite';
    return out;
  }
  let best = null;
  for (const form of forms) {
    const expected = toSyllables(form, chars);
    if (!expected || expected.length !== typed.length) continue;
    if (!expected.every((s, i) => s.base === typed[i].base)) continue;
    const expectedHasTones = expected.some((s) => s.tone !== 5);
    const typedHasTones = typed.some((s) => s.tone !== 5);
    if (expected.every((s, i) => s.tone === typed[i].tone)) {
      out.correct = true;
      out.expected = form;
      return out;
    }
    if (!typedHasTones && expectedHasTones) {
      if (!tonesRequired) {
        out.correct = true;
        out.expected = form;
        out.message = 'Right letters (tones not checked)';
        return out;
      }
      best = best || { close: true, message: 'Right letters: add the tones', expected: form };
    } else best = best || { close: true, message: 'Right letters, wrong tones', expected: form };
  }
  if (best) Object.assign(out, best);
  else out.message = 'Not quite';
  return out;
}
