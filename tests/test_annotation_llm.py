import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from annotation_llm import annotate, backoff, load_env, normalize, read_done, user_message  # noqa: E402

ITEM = {'item_id': 'P0001', 'context_post': 'Wpis o migrantach', 'context_parent': '', 'context_quote': '',
        'text': 'ukry to akurat spoko ludzie', 'slurs': 'ukry'}


def test_user_message_skips_empty_context_and_adds_prefill():
    m = user_message(ITEM)
    assert 'context_post:\nWpis o migrantach' in m and 'context_parent' not in m
    assert 'hate_migrants = 1' in m
    assert 'hate_migrants = 1' not in user_message({**ITEM, 'slurs': 'bandera (?)'})   # context term: no prefill
    assert 'hate_migrants = 1' not in user_message({k: v for k, v in ITEM.items() if k != 'slurs'})  # old rounds


def test_normalize_rejects_bad_pair():
    assert normalize({'hate': '1', 'hate_migrants': '1', 'uncertain': False, 'note': 'x'}) == \
        {'hate': '1', 'hate_migrants': '1', 'uncertain': '', 'note': 'x'}
    r = normalize({'hate': '0', 'hate_migrants': '1', 'uncertain': True, 'note': 'x'})
    assert r['hate_migrants'] == '' and r['uncertain'] == '1' and 'niedozwolona' in r['note']


def test_annotate_retries_bad_json_then_reports_error():
    calls = []

    def flaky(system, message):
        calls.append(1)
        return ('not json' if len(calls) == 1 else json.dumps(
            {'hate': '1', 'hate_migrants': '1', 'uncertain': False, 'note': 'pkt 4.12'})), 'm'
    assert annotate(flaky, 'S', ITEM, tries=2)['hate_migrants'] == '1'
    assert 'error' in annotate(lambda s, m: ('nope', 'm'), 'S', ITEM, tries=1)


def test_backoff_uses_requested_delay():
    assert backoff(Exception('429 RESOURCE_EXHAUSTED ... Please retry in 19.96s.'), 0) > 20
    assert backoff(Exception('429 RESOURCE_EXHAUSTED'), 0) == 30
    assert backoff(ValueError('bad json'), 2) == 4


def test_read_done_skips_errors_for_resume(tmp_path):
    log = tmp_path / 'claude.jsonl'
    log.write_text('{"item_id": "P1", "hate": "0"}\n{"item_id": "P2", "error": "x"}\n', encoding='utf-8')
    assert list(read_done(log)) == ['P1']


def test_load_env_does_not_override_shell(tmp_path, monkeypatch):
    env = tmp_path / '.env'
    env.write_text('# c\nAMC_TEST_A=from_file\nAMC_TEST_B="q"\nAMC_TEST_EMPTY=\n', encoding='utf-8')
    monkeypatch.setenv('AMC_TEST_A', 'shell')
    monkeypatch.delenv('AMC_TEST_B', raising=False)
    load_env(env)
    assert os.environ['AMC_TEST_A'] == 'shell' and os.environ['AMC_TEST_B'] == 'q' and 'AMC_TEST_EMPTY' not in os.environ
