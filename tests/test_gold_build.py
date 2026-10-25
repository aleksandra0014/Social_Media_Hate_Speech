import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from gold_build import build_round, majority, pair, triage, write_review  # noqa: E402

LABELS = {  # item: (claude, gemini, gpt) as hate/hate_migrants
    'P1': ('1/1', '1/1', '1/1'), 'P2': ('1/1', '1/0', '1/1'), 'P3': ('0/0', '0/0', '0/0'),
    'P4': ('0/0', '0/0', ''), 'P5': ('1/0', '1/0', '1/0'),
}


def make_round(tmp_path, uncertain=('P5',)):
    base = tmp_path / 'gold_v1'
    (base / 'annotated').mkdir(parents=True)
    pd.DataFrame({'item_id': list(LABELS), 'platform': 'wykop', 'event_folder': 'e', 'comment_id': list(LABELS),
                  'post_id': 'x', 'pool': 'mig_other', 'context_post': '', 'context_parent': '',
                  'context_quote': '', 'text': 't'}).to_csv(base / 'manifest.csv', index=False)
    for k, a in enumerate(('claude', 'gemini', 'gpt')):
        v = [LABELS[i][k] for i in LABELS]
        pd.DataFrame({'item_id': list(LABELS), 'hate': [x[:1] for x in v], 'hate_migrants': [x[2:] for x in v],
                      'uncertain': ['1' if i in uncertain and a == 'gpt' else '' for i in LABELS],
                      'note': ['n' if i in uncertain and a == 'gpt' else '' for i in LABELS]}) \
            .to_csv(base / 'annotated' / f'gold_v1_{a}.csv', index=False)
    return base


def test_pair_and_majority():
    assert pair('0', '') == '0/0' and pair('0', '1') == '' and pair('tak', '1') == '1/1'
    assert majority(['1/1', '1/0', '1/1']) == '1/1' and majority(['1/1', '1/0']) == '' and majority(['', '']) == ''


def test_triage_reasons():
    pairs = pd.DataFrame({'a': ['1/1', '1/1', '0/0', '0/0'], 'b': ['1/1', '1/0', '0/0', '']}, index=list('wxyz'))
    unc = pd.DataFrame({'a': ['', '', '1', ''], 'b': ['', '', '', '']}, index=list('wxyz'))
    assert triage(pairs, unc, 0, 1).tolist() == ['', 'niezgoda', '', 'brak kodu']
    assert triage(pairs, unc, 0, 1, review_uncertain=True).tolist() == ['', 'niezgoda', 'uncertain', 'brak kodu']


def test_round_without_decisions_keeps_only_unanimous(tmp_path):
    gold, review, stats = build_round(make_round(tmp_path), 'gold_v1', check_share=0)
    g = gold.set_index('item_id')['label_source']
    assert g.to_dict() == {'P1': 'unanimous', 'P3': 'unanimous', 'P5': 'unanimous_uncertain'}
    assert dict(zip(review['item_id'], review['reason'])) == {'P2': 'niezgoda', 'P4': 'brak kodu'}
    assert stats['pending'] == 2 and stats['unanimous_uncertain'] == 1
    _, review, _ = build_round(make_round(tmp_path / 'r'), 'gold_v1', check_share=0, review_uncertain=True)
    assert 'P5' in set(review['item_id'])


def test_decisions_complete_the_gold(tmp_path):
    base = make_round(tmp_path)
    _, review, _ = build_round(base, 'gold_v1', check_share=0)
    review.loc[review['item_id'] == 'P2', ['hate', 'hate_migrants', 'note']] = ['1', '0', 'pkt 4.5']
    review.loc[review['item_id'] == 'P4', ['hate', 'hate_migrants']] = ['0', '1']  # invalid pair
    write_review(review, base / 'results' / 'adjudication.xlsx')
    gold, _, stats = build_round(base, 'gold_v1', check_share=0)
    g = gold.set_index('item_id')
    assert g.loc['P2', ['hate', 'hate_migrants', 'label_source']].tolist() == ['1', '0', 'adjudicated']
    assert 'P4' not in g.index and stats['pending'] == 1 and len(stats['problems']) == 1
    assert stats['adjudicated_like_majority'] == 0.0   # P2 against majority 1/1

    review.loc[review['item_id'] == 'P4', ['hate', 'hate_migrants']] = ['0', '']   # 0 + empty = 0/0
    write_review(review, base / 'results' / 'adjudication.xlsx')
    gold, _, stats = build_round(base, 'gold_v1', check_share=0)
    assert gold.set_index('item_id').loc['P4', 'hate_migrants'] == '0' and stats['pending'] == 0


def test_check_sample_is_stable_and_labelled(tmp_path):
    base = make_round(tmp_path, uncertain=())
    _, r1, _ = build_round(base, 'gold_v1', check_share=0.5)
    _, r2, _ = build_round(base, 'gold_v1', check_share=0.5)
    checked = r1.loc[r1['reason'] == 'kontrola', 'item_id'].tolist()
    assert len(checked) == 2 and checked == r2.loc[r2['reason'] == 'kontrola', 'item_id'].tolist()
    gold, _, _ = build_round(base, 'gold_v1', check_share=0.5)
    assert set(checked) <= set(gold['item_id'])   # unchecked control items keep the unanimous label


def test_decisions_from_disagreements_csv(tmp_path):
    base = make_round(tmp_path)
    (base / 'results').mkdir()
    pd.DataFrame({'item_id': ['P2', 'P5'], 'decision': ['1/0', '']}).to_csv(base / 'results' / 'disagreements.csv',
                                                                         index=False)
    gold, review, _ = build_round(base, 'gold_v1', check_share=0)
    assert gold.set_index('item_id').loc['P2', ['hate_migrants', 'label_source']].tolist() == ['0', 'adjudicated']
    assert review.set_index('item_id').loc['P2', 'hate'] == '1'   # carried into adjudication.xlsx
