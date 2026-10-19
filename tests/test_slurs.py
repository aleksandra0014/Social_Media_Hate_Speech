import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from annotation_sample import mark_context, pick, prefilled, slur_label  # noqa: E402
from preprocess_slurs import flag_frame  # noqa: E402
from src.lexicon.slurs import TERMS, find_slurs, slur_columns  # noqa: E402

names = lambda text: [t.name for t in find_slurs(text)]


@pytest.mark.parametrize('text, term', [
    ('Ukry to akurat fajni ludzie', 'ukry'),          # friendly tone still counts (pkt 4.12)
    ('Chachły znowu w kolejce', 'chachol'),
    ('NACHODŹCY na granicy', 'nachodzcy'),
    ('ukronaziści wszędzie', 'ukro-*'),
    ('kolejni ubogacacze', 'ubogacacze'),
    ('wypierdalać na Ukrainę', 'wypad_na_ukraine'),
    ('to jest dzicz', 'bydlo_holota'),
])
def test_slur_found_with_case_and_diacritics(text, term):
    assert term in names(text)


@pytest.mark.parametrize('text', [
    'Ukraina walczy', 'Ukraińcy pracują w Polsce', 'chochoł z Wesela', 'dziczyzna na obiad', 'upadek rządu',
    'ukrainiec', 'migranci na granicy',
])
def test_neutral_words_not_matched(text):
    assert names(text) == []


def test_all_patterns_compile_and_names_unique():
    assert len({t.name for t in TERMS}) == len(TERMS)


def test_slur_columns():
    assert slur_columns('nic tu nie ma') == ('', '', '')
    n, cat, ctx = slur_columns('ukry i Bandera')
    assert n == 'ukry; bandera' and ctx == '0'
    assert slur_columns('Bandera')[2] == '1'


def test_flag_frame_prelabels_1_1():
    df = pd.DataFrame({'comment_id': ['a', 'b', 'c'], 'text': ['ukropy won', 'dobry dzień', 'UPA w 1943']})
    out = flag_frame(df, 'comment_id')
    assert out['hate_auto'].tolist() == [1, 0, 0] and out['hate_migrants_auto'].tolist() == [1, 0, 0]
    assert out['slurs'].tolist() == ['ukrop', '', 'upa']   # context terms listed, not pre-labelled


def test_prefill_modes():
    assert slur_label('ukry, Bandera') == 'ukry; bandera (?)'
    assert prefilled('ukry; bandera (?)', 'all') == '1'
    assert prefilled('bandera (?)', 'strict') == '' and prefilled('ukry', 'strict') == '1'
    assert prefilled('ukry', 'none') == '' and prefilled('', 'all') == ''


def test_stage_output_used_when_present():
    assert mark_context('ukry; bandera') == 'ukry; bandera (?)' and mark_context('') == ''
    df = pd.DataFrame({'shown': ['Zwykły komentarz o pogodzie dzisiaj', 'Kolejny komentarz o pogodzie jutro'],
                       'post_migration': [False, False], 'slurs': ['ukry', pd.NA]})
    s = pick(df, 2, seed=1)   # first row: label from the stage file, not from the text
    assert s['slurs'].tolist() == ['ukry']


def test_slur_comments_stay_in_draw():
    # no migration or hostile word from the pool regexes, only a slur -> still picked as mig_hostile
    df = pd.DataFrame({'shown': ['Ci banderlogi znowu coś wymyślili dzisiaj', 'Zwykły komentarz o pogodzie dzisiaj'],
                       'post_migration': [False, False]})
    s = pick(df, 2, seed=1)
    assert s['pool'].tolist() == ['mig_hostile'] and s['slurs'].iloc[0] == 'banderlog'
