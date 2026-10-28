"""BAN-PL text preparation, VERSION 2 (notebooks/models_v2/06_banpl_roberta_finetune_v2 and 07_roberta_banpl_hate_v2).

Version 1 (src/classifier/banpl.py, 'banpl-v1') stays unchanged: the model in models/polish-roberta-base-v2-banpl
and its predictions were made with it. This module only adds the fixes found in the artefact audit
(notebooks/models_v2/06_..., step 1). Same input -> v1 vs v2 differ only in the points below.

What v1 already did (kept as it is in v2):
  - paper preprocessing: newlines removed, space after 'USERNAME:',
  - {USERNAME} -> '@[user]', {URL} -> '[link]', then clean_text like our comments (mentions, links, quotes, emoji
    removed, whitespace normalised - neutral texts had scraping whitespace: double spaces 21.7% vs 0.3%),
  - profanity masks unmasked with the BAN-PL vulgarism list: Wykop's '#!$%@?' (3.0% neutral vs 0.01% harmful)
    and our 'p------a' (7.7% of our Wykop comments, never in BAN-PL).

v2 changes (artefacts v1 left in, numbers = % of neutral vs % of harmful BAN-PL texts after v1):
  1. HASHTAGS ARE DROPPED, not turned into words.
     In BAN-PL 17.3% of harmful texts carry Wykop tags vs 1.1% of neutral ones (banned entries were stored with
     their tags, comments without). v1's clean_text turns '#mecz' into 'mecz', so tag words became 'harmful'
     markers: mecz 213 vs 4 texts, f1 91 vs 0, patostreamy 159 vs 1, przegryw 231 vs 6, and also topic words
     we care about (#ukraina, #polityka, #neuropa). Tags are metadata, not what the author wrote -> removed.
  2. '[pseudonym]' / '#[pseudonym]' ARE DROPPED, not replaced by a surname.
     0.8% neutral vs 5.7% harmful; v1 turned them into surnames, so 'Kowalski/Nowak/...' ended up in 7.9% vs
     12.5% of texts - a new shortcut. '[surname]' is balanced (7.7% vs 8.3%) and still becomes a surname.
  3. ASTERISK SELF-CENSORSHIP is unmasked like the other masks ('ch*j', 'k*rwa', '*****'): 1.1% vs 2.5% in
     BAN-PL; a word with letters kept around '*' is matched in the vulgarism list, '***' alone is dropped.
  4. UNRESOLVED DASH MASKS ('k--', a mask with no matching dictionary word) are dropped instead of left as
     dashes: BAN-PL never contains them, so for the model they were noise outside its training distribution.

Not changed (checked, documented in the notebook): text length (neutral texts are longer, median 138 vs 93
characters - a real property of the dataset, not a marker we can remove) and topic words (neutral comments talk
more about prices, the EU, companies) - both are limits of BAN-PL, reported, not 'fixed'.
"""
import re

from src.classifier.banpl import (Unmasker, _DASH_MASK, _DROP_TAGS, _surname, paper_preprocess)
from src.preprocessing.cleaning import clean_text

PREPROCESSING_VERSION = 'banpl-v2'

# 1. hashtags (also '#[pseudonym]' handled in 2.); '&#39;'-like entities are not tags
_HASHTAG = re.compile(r'(?<![\w&])#(?!\[)[^\W_][\w-]*')
# 2. pseudonyms dropped, surnames kept as varied surnames (as in v1)
_PSEUDONYM = re.compile(r'#?\[pseudonym\]')
_SURNAME = re.compile(r'\[surname\]')
# 3. asterisk masks: 'ch*j', 'k**wa', 'ch*ju' (letters around stars) or a bare run of stars
_STAR_WORD = re.compile(r'(?<![\w*])([^\W\d_]+)(\*+)([^\W\d_]*)(?![\w*])')
_STAR_RUN = re.compile(r'(?<![\w*])\*{3,}(?![\w*])')
_SPACES = re.compile(r'\s{2,}')


class UnmaskerV2(Unmasker):
    """v1 Unmasker + asterisk masks + unresolved dash masks dropped."""

    def _star(self, m):
        first, stars, rest = m.group(1), m.group(2), m.group(3)
        word = self._find(first, rest, len(first) + len(stars) + len(rest)) or self._find(first, rest)
        return self._case(word, first) if word else first + rest

    def _dash_v2(self, m):
        out = self._dash(m)
        return ' ' if out == m.group(0) else out          # v1 left it as 'k--'; v2 drops it

    def __call__(self, text):
        text = super().__call__(text)                     # v1: '#!$%@?' and resolvable 'p------a'
        if '--' in text:
            text = _DASH_MASK.sub(self._dash_v2, text)
        if '*' in text:
            text = _STAR_WORD.sub(self._star, text)
            text = _STAR_RUN.sub(' ', text)
        return _SPACES.sub(' ', text).strip()


def drop_hashtags(text):
    return _HASHTAG.sub(' ', text)


def banpl_to_project_v2(text):
    text = str(text).replace('{USERNAME}', '@[user]').replace('{URL}', '[link]')
    text = text.replace('[phonenumber]', '[phone]')
    text = _PSEUDONYM.sub(' ', text)                      # v2: dropped (v1: surname)
    text = _SURNAME.sub(_surname, text)
    text = _DROP_TAGS.sub(' ', text)
    text = drop_hashtags(text)                            # v2: before clean_text, which would keep the word
    return clean_text(text)


def model_input_v2(text, unmasker=None, from_banpl=False, debias=True):
    """Text exactly as the v2 model sees it (training and prediction).

    For our comments the input is the cleaned text from clean/comments.csv; clean_text already turned
    '#tag' into 'tag' there (tags occur in 0.6% of Wykop, 1.1% of Bluesky and 0.04% of YouTube topic
    comments), so tags cannot be dropped at prediction time - the important part is that the model no longer
    LEARNS tag words as a 'harmful' signal.
    """
    text = str(text)
    if from_banpl and debias:
        text = banpl_to_project_v2(text)
    if debias and unmasker is not None:
        text = unmasker(text)
    return paper_preprocess(text)
