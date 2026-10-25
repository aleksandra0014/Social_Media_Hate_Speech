import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import annotation_sample  # noqa: E402

COLS = ['item_id', 'platform', 'event_folder', 'comment_id', 'post_id', 'pool', 'source', 'context_post',
        'context_parent', 'context_quote', 'text', 'slurs']


def fake_platform(platform):
    texts = ['Migranci znowu przyjechali do miasta dzisiaj', 'Uchodźcy dostali mieszkania od gminy wczoraj',
             'Imigranci pracują na budowie od rana do nocy']
    return pd.DataFrame({'comment_id': ['c1', 'c2', 'c3'], 'post_id': 'p', 'shown': texts, 'context_quote': '',
                         'context_post': '', 'context_parent': '', 'post_migration': True, 'source': 'clean',
                         'platform': platform, 'event_folder': 'e'})


def run(monkeypatch, tmp_path, *argv):
    monkeypatch.setattr(annotation_sample, 'OUT_ROOT', tmp_path)
    monkeypatch.setattr(annotation_sample, 'load_platform', fake_platform)
    monkeypatch.setattr(sys, 'argv', ['annotation_sample.py', '--name', 'gold_v1', '--annotators', 'A', *argv])
    annotation_sample.main()
    return pd.read_csv(tmp_path / 'gold_v1' / 'manifest.csv', dtype=str, keep_default_na=False)


def test_append_keeps_old_ids_and_skips_duplicates(monkeypatch, tmp_path):
    first = run(monkeypatch, tmp_path, '--platforms', 'wykop', '--n-per-platform', '2')
    with pytest.raises(SystemExit):   # no silent redraw of an existing round
        run(monkeypatch, tmp_path, '--platforms', 'youtube')
    both = run(monkeypatch, tmp_path, '--append', '--platforms', 'youtube', 'wykop', '--n-per-platform', '3')
    assert list(both.columns) == COLS
    assert both.head(len(first)).equals(first)                         # old rows and ids untouched
    new = both.iloc[len(first):]
    assert new['item_id'].tolist() == [f'P{i:04d}' for i in range(3, 3 + len(new))]
    assert set(new['platform']) == {'youtube', 'wykop'}
    assert not both.duplicated(['platform', 'comment_id']).any()        # wykop items already drawn are skipped
    assert len(pd.read_excel(tmp_path / 'gold_v1' / 'sheets' / 'gold_v1_A.xlsx')) == len(both)
