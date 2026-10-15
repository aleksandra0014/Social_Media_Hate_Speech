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


@pytest.mark.parametrize('text, expected', [
    ('>cytat z innego komentarza\n\n@[user]: moja odpowiedź tutaj', 'moja odpowiedź tutaj'),
    ('> pierwszy\n>> drugi\nwłasne zdanie', 'własne zdanie'),
    ('@[user]: tak właśnie było', 'tak właśnie było'),
    ('No jasne ( ͡° ͜ʖ ͡°) xD', 'No jasne [lenny] xD'),
    ('Szkoda ( ͡° ʖ̯ ͡°) i tyle (⌐ ͡■ ͜ʖ ͡■)', 'Szkoda [lenny] i tyle [lenny]'),
    ('a > b to prawda', 'a > b to prawda'),
    ('@[user]: >cytat w tej samej linii\nodpowiedź autora tutaj', 'odpowiedź autora tutaj'),
    ('@[user] @[user] : braki w paliwie', 'braki w paliwie'),
    ('@[user]: :D zawsze to samo', ':D zawsze to samo'),
])
def test_clean_text_quotes_replies_lenny(text, expected):
    assert clean_text(text) == expected


@pytest.mark.parametrize('text, reason', [
    ('>długi cytat z zupełnie innego komentarza\n@[user]: xD', VERY_SHORT),
    ('>sam cytat bez odpowiedzi autora', NO_TEXT),
    ('xD ( ͡° ͜ʖ ͡°) ok', VERY_SHORT),
    ('>krótki cytat\n@[user]: ale to jest moja pełna odpowiedź', None),
])
def test_rule_reason_ignores_quotes_and_lenny(text, reason):
    assert rule_reason(text, 3) == reason
