"""Text preparation for the Polish RoBERTa model fine-tuned on BAN-PL (notebooks 06 and 07).

The same function `model_input` is used for training (BAN-PL) and for prediction (our clean Wykop comments),
so the model sees text in one form in both places.

1. Preprocessing from the BAN-PL paper (Kołos et al. 2024, sec. 5.5) - always applied:
   - newlines removed,
   - a space after the addressed-user token 'USERNAME:'.

2. Removing BAN-PL artefacts that would bias the model (DEBIAS=True in notebook 06):
   - BAN-PL placeholders do not occur in our data, and some of them correlate with the class
     ({USERNAME}: 78% neutral vs 59% harmful, #[pseudonym]: 0.8% vs 5.7%). They are mapped to the forms our
     pipeline produces ({USERNAME} -> '@[user]', {URL} -> '[link]') and then cleaned with
     src.preprocessing.cleaning.clean_text - exactly like our comments (quotes, mentions, links, emoji removed,
     lenny face -> [lenny]). Surnames/pseudonyms become ordinary surnames (several, so that no single token
     becomes a 'harmful' marker); addresses and numbers are dropped.
   - Profanity masking differs between the classes: Wykop's automatic mask '#!$%@?' is almost only in the
     neutral class (3.0% vs 0.008%), because banned texts were stored unmasked. A model would learn
     '#!$%@?' = neutral. Our comments use another mask ('p------a': first and last letter kept, 7% of texts),
     which BAN-PL never shows. Both masks are therefore unmasked with the BAN-PL vulgarism list
     (resources/polish_vulgarisms_extended_2.0.txt) - the same idea as unmask_profanities in the BAN-PL repo.
"""
import re
import zlib
from pathlib import Path

from src.preprocessing.cleaning import clean_text

PREPROCESSING_VERSION = 'banpl-v1'

# --- 1. paper -------------------------------------------------------------------------------------------
_NEWLINES = re.compile(r'\s*\n\s*')
_USERNAME_COLON = re.compile(r'(\{USERNAME\}|USERNAME):(?=\S)')


def paper_preprocess(text):
    text = _USERNAME_COLON.sub(r'\1: ', str(text))
    return _NEWLINES.sub(' ', text).strip()


# --- 2. BAN-PL placeholders -> our format ---------------------------------------------------------------
_SURNAMES = ('Kowalski', 'Nowak', 'Wiśniewski', 'Wójcik', 'Kamiński', 'Lewandowski', 'Zieliński', 'Szymański')
_NAME_TAG = re.compile(r'#?\[(?:surname|pseudonym)\]')
_DROP_TAGS = re.compile(r'\[(?:address|number)\]')


def _surname(match):
    # deterministic, varied surname (no single token correlated with a class)
    return _SURNAMES[zlib.crc32(match.string.encode('utf-8')) % len(_SURNAMES)]


def banpl_to_project(text):
    text = str(text).replace('{USERNAME}', '@[user]').replace('{URL}', '[link]')
    text = text.replace('[phonenumber]', '[phone]')
    text = _NAME_TAG.sub(_surname, text)
    text = _DROP_TAGS.sub(' ', text)
    return clean_text(text)


# --- profanity masks ------------------------------------------------------------------------------------
# preferred stems when several dictionary words fit the mask (most frequent Polish vulgarisms first)
_STEMS = ('pierdol', 'kurw', 'wypierdal', 'wypierdol', 'spierdal', 'spierdol', 'jeb', 'wyjeb', 'zjeb',
          'pojeb', 'chuj', 'huj', 'pizd', 'gówn', 'dup', 'sra', 'szmat', 'cip')
# words Wykop also masks, though not vulgar (seen in our data: r--ź, b--ń, g---t, s--s, b---a)
_EXTRA = ('rzeź', 'rzezi', 'broń', 'broni', 'bomba', 'bomby', 'bombę', 'gwałt', 'gwałtu', 'gwałty', 'gwałcić',
          'gwałciciel', 'gwałciciela', 'gwałciciele', 'gwałcicieli', 'seks', 'seksu', 'zabić', 'zabił',
          'zabili', 'zabijać', 'nazista', 'naziści', 'nazistów', 'pedofil', 'pedofila', 'pedofile',
          'zabójstwo', 'morderstwo', 'terrorysta', 'terroryści', 'zamach', 'kurwa', 'kurwy', 'pierdolić',
          'gówno', 'gówna', 'gównem', 'gównie', 'burdel', 'burdelu', 'murzyn', 'murzyna', 'murzyni', 'murzynów',
          'ruchać', 'faszyzm', 'faszyzmu', 'alkohol', 'bombardować', 'bombardowań', 'bombardowanie', 'cwele',
          'cweli')
_HASH_MASK = re.compile(r'([^\W\d_]*)#!\$%@\?([^\W\d_]*)')
_DASH_MASK = re.compile(r'(?<![\w-])([^\W\d_])(-{2,})([^\W\d_]{1,3})?(?![\w-])')


class Unmasker:
    """Replaces masked profanities with dictionary words (first word by stem priority)."""

    def __init__(self, vocab_path):
        words = {w.strip().lower() for w in Path(vocab_path).read_text(encoding='utf-8').splitlines()
                 if w.strip() and ' ' not in w.strip()}
        words |= set(_EXTRA)
        rank = lambda w: (next((i for i, s in enumerate(_STEMS) if w.startswith(s)), len(_STEMS)), len(w), w)
        self.words = sorted(words, key=rank)
        self.cache = {}

    def _find(self, prefix, suffix, length=None):
        key = (prefix.lower(), suffix.lower(), length)
        if key not in self.cache:
            p, s = key[0], key[1]
            self.cache[key] = next((w for w in self.words if w.startswith(p) and w.endswith(s)
                                    and (length is None or len(w) == length)
                                    and (length is not None or len(w) > len(p) + len(s))), None)
        return self.cache[key]

    @staticmethod
    def _case(word, like):
        return word.capitalize() if like[:1].isupper() else word

    def _hash(self, m):
        prefix, suffix = m.group(1), m.group(2)
        if not prefix and not suffix:     # whole word masked - the most common one
            return 'kurwa'
        word = self._find(prefix, suffix) or (self._find('', suffix) if prefix else None) or 'kurwa'
        return self._case(word, prefix or m.group(0))

    def _dash(self, m):
        first, dashes, rest = m.group(1), m.group(2), m.group(3) or ''
        if not rest:                      # 'k--' : not a mask we can resolve
            return m.group(0)
        word = self._find(first, rest, len(first) + len(dashes) + len(rest))
        return self._case(word, first) if word else m.group(0)

    def __call__(self, text):
        text = str(text)
        if '#!$%@?' in text:
            text = _HASH_MASK.sub(self._hash, text)
        if '--' in text:
            text = _DASH_MASK.sub(self._dash, text)
        return text


def model_input(text, unmasker=None, from_banpl=False, debias=True):
    """Text exactly as the model sees it (training and prediction)."""
    text = str(text)
    if from_banpl and debias:
        text = banpl_to_project(text)
    if debias and unmasker is not None:
        text = unmasker(text)
    return paper_preprocess(text)
