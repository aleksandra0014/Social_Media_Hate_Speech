import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from disagreements_xlsx import to_sheet  # noqa: E402
from gold_build import write_review  # noqa: E402

DIS = pd.DataFrame({'item_id': ['P1', 'P2', 'P3'], 'platform': 'wykop', 'text': ['a', 'b', 'c'],
                    'marta': ['1/1', '0/0', '1/0'], 'ola': ['1/0', '1/0', '0/0'],
                    'decision': ['1/1', '', '0-0'], 'codebook_change': ['', 'pkt 4.5', '']})


def test_decision_column_split_into_dropdown_columns():
    s = to_sheet(DIS)
    assert s[['hate', 'hate_migrants']].values.tolist() == [['1', '1'], ['', ''], ['0', '0']]
    assert 'decision' not in s and s['codebook_change'].tolist() == ['', 'pkt 4.5', '']
    assert list(s.columns[-4:]) == ['hate', 'hate_migrants', 'note', 'codebook_change']


def test_rerun_keeps_decisions_from_earlier_xlsx(tmp_path):
    path = tmp_path / 'disagreements.xlsx'
    s = to_sheet(DIS)
    s.loc[1, ['hate', 'hate_migrants', 'note']] = ['1', '0', 'wyzwisko wobec rządu']
    write_review(s, path)
    again = to_sheet(DIS, pd.read_excel(path, dtype=str).fillna(''))
    assert again.loc[1, ['hate', 'hate_migrants', 'note']].tolist() == ['1', '0', 'wyzwisko wobec rządu']
    assert again.loc[0, 'hate_migrants'] == '1'
