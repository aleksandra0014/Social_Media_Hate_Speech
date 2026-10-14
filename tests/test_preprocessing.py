import pandas as pd
import pytest

from src.preprocessing.cleaning import clean_text
from src.preprocessing.filters import (DUPLICATE, EMOJI_ONLY, NO_TEXT, NON_POLISH, VERY_SHORT,
                                       assign_drop_reason, rule_reason)
from src.preprocessing.lang import build_detector

CFG = {'min_words': 3, 'languages': ['pl', 'en', 'de', 'ru', 'uk'],
       'min_pl_confidence': 0.5, 'drop_duplicates': True}


@pytest.fixture(scope='module')
def detector():
    return build_detector(CFG['languages'])


@pytest.mark.parametrize('text, reason', [
    ('😂😂👍', EMOJI_ONLY),
    ('https://x.com/abc', NO_TEXT),
    ('@[user] [link]', NO_TEXT),
    ('123 !!!', NO_TEXT),
    ('', NO_TEXT),
    ('no właśnie', VERY_SHORT),
    ('#migracja #granica @[user] tak', VERY_SHORT),
    ('To jest normalny polski komentarz', None),
])
def test_rule_reason(text, reason):
    assert rule_reason(text, 3) == reason


def test_assign_drop_reason(detector):
    df = pd.DataFrame({
        'text': [
            'Rząd znowu nie ma pomysłu na politykę migracyjną',
            'The government has no idea what to do about migration',
            'Rząd znowu nie ma pomysłu na politykę migracyjną!!! [link]',
            '😂😂',
        ],
        'created_at': ['2024-01-01T10:00', '2024-01-01T11:00', '2024-01-01T12:00', '2024-01-01T13:00'],
    })
    assert list(assign_drop_reason(df, CFG, detector).fillna('keep')) == [
        'keep', NON_POLISH, DUPLICATE, EMOJI_ONLY]


@pytest.mark.parametrize('text, expected', [
    ('Patrz #migracja 👉 https://a.pl/x @[user]  ok', 'Patrz migracja ok'),
    ('Tekst [link] dalej', 'Tekst dalej'),
    ('Zdanie 1.\n\n\n  Zdanie 2. 🇵🇱', 'Zdanie 1.\nZdanie 2.'),
    ('Pisz na [email] albo @jan.bsky.social', 'Pisz na albo'),
])
def test_clean_text(text, expected):
    assert clean_text(text) == expected
