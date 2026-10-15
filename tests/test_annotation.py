import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from annotation_agreement import clean_sheet, cohen_kappa, fleiss_kappa, krippendorff_alpha, norm  # noqa: E402
from annotation_sample import HOSTILE, MIGRATION, fold, split_quote  # noqa: E402
from wykop import mask_text  # noqa: E402


def test_alpha_matches_krippendorff_2011_nominal_example():
    # Krippendorff (2011), "Computing Krippendorff's Alpha-Reliability": alpha = 0.743
    a = [1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None]
    b = [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, 3]
    c = [None, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, None]
    d = [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, None]
    units = [[str(v) for v in col if v is not None] for col in zip(a, b, c, d)]
    assert round(krippendorff_alpha(units), 3) == 0.743


def test_alpha_edge_cases():
    assert krippendorff_alpha([['1', '1'], ['0', '0'], ['1', '1']]) == 1
    assert pd.isna(krippendorff_alpha([['1', '1'], ['1', '1']]))


def test_fleiss_kappa_matches_fleiss_1971_example():
    # Fleiss (1971): 10 items, 14 raters, 5 categories, kappa = 0.210
    table = [[0, 0, 0, 0, 14], [0, 2, 6, 4, 2], [0, 0, 3, 5, 6], [0, 3, 9, 2, 0], [2, 2, 8, 1, 1],
             [7, 7, 0, 0, 0], [3, 2, 6, 3, 0], [2, 5, 3, 2, 2], [6, 5, 2, 1, 0], [0, 2, 2, 3, 7]]
    units = [[str(cat) for cat, k in enumerate(row) for _ in range(k)] for row in table]
    assert round(fleiss_kappa(units), 3) == 0.210


def test_fleiss_kappa_needs_complete_items():
    assert pd.isna(fleiss_kappa([['1', '1', '0'], ['1', '0']]))


def test_cohen_kappa():
    assert cohen_kappa(['1', '0', '1', '0'], ['1', '0', '1', '0']) == 1
    assert cohen_kappa(['1', '1', '0', '0'], ['0', '0', '1', '1']) == -1


@pytest.mark.parametrize('raw, expected', [('tak', '1'), ('Nie', '0'), ('1.0', '1'), (' 0 ', '0'), ('nan', '')])
def test_norm(raw, expected):
    assert norm(raw) == expected


def test_clean_sheet():
    df = pd.DataFrame({'item_id': ['P1', 'P2', 'P3', 'P4'],
                       'hate': ['1', 'może', '', 'tak'],
                       'uncertain': ['', '1', '', '0'],
                       'note': ['', '', '', '']})
    out, problems = clean_sheet(df, 'X')
    found = {(p[1], p[2], p[4]) for p in problems}
    assert ('P2', 'hate', 'value not 0/1') in found
    assert ('P3', 'hate', 'missing') in found
    assert ('P2', 'note', 'uncertain=1 without note') in found
    assert list(out['hate']) == ['1', '', '', '1']
    assert list(out['uncertain']) == ['', '1', '', '']


@pytest.mark.parametrize('text, migration', [
    ('Ukraińcy znowu dostali socjal', True),
    ('Kolejny inżynier z Afryki', True),
    ('Ukraina płaci za prąd z umowy', False),
    ('inżynieria społeczna w wojsku', False),
])
def test_migration_pattern(text, migration):
    assert bool(MIGRATION.search(fold(text))) is migration


def test_hostile_pattern_ignores_neutral_deportation_news():
    assert not HOSTILE.search(fold('Z Polski deportowano 3 tys. osób'))
    assert HOSTILE.search(fold('wypierdalać z Polski'))


def test_wykop_masks_like_bluesky():
    assert mask_text('@jan_kowalski: pisz na a.b@x.pl albo 600 700 800, https://x.pl/a') == \
        '@[user]: pisz na [email] albo [phone], [link]'


def test_split_quote_moves_quotes_to_context():
    own, quote = split_quote('>Dziś widziałem samych obcych\n>> i jeszcze tu\n\n@[user]: Ło matko, solidna podstawa xD')
    assert own == '@[user]: Ło matko, solidna podstawa xD'
    assert quote == 'Dziś widziałem samych obcych\ni jeszcze tu'
    assert split_quote('bez cytatu') == ('bez cytatu', '')
    assert split_quote('@[user]: >cytat\nmoja odpowiedź') == ('@[user]:\nmoja odpowiedź', 'cytat')
