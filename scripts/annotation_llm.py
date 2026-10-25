"""LLM as one more annotator: codes a round's manifest by docs/CODEBOOK.md (docs/ANOTACJA.md, sekcja 5).
    python scripts/annotation_llm.py --name pilot_v2 --model claude
Writes data/annotation/<name>/annotated/<name>_<model>.xlsx (read by annotation_agreement.py)
and every raw answer to data/annotation/<name>/llm/<model>.jsonl (rerun = resume).
"""
import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_sample import OUT_ROOT, ROOT, prefilled  # noqa: E402

MODELS = {'claude': ('ANTHROPIC_MODEL', 'claude-opus-5-5'), 'gemini': ('GEMINI_MODEL', None),
          'gpt': ('OPENAI_MODEL', None)}
SCHEMA = {
    'type': 'object',
    'properties': {
        'hate': {'type': 'string', 'enum': ['0', '1']},
        'hate_migrants': {'type': 'string', 'enum': ['0', '1']},
        'uncertain': {'type': 'boolean'},
        'note': {'type': 'string'},
    },
    'required': ['hate', 'hate_migrants', 'uncertain', 'note'],
    'additionalProperties': False,
}
SYSTEM = """Jesteś osobą kodującą w projekcie badawczym o mowie nienawiści wobec migrantów w polskich mediach \
społecznościowych. Kodujesz komentarze dokładnie według poniższego codebooka, tak jak pozostałe osoby kodujące.

Zwróć JSON:
- hate: "1" albo "0" (pkt 3.1),
- hate_migrants: "1" albo "0" (pkt 3.2; "1" tylko gdy hate = "1"),
- uncertain: true, gdy przypadek jest graniczny (pkt 4.11),
- note: jedno krótkie zdanie po polsku w przypadku jeśli uncertain=1: która zasada lub przypadek graniczny przesądził.

<codebook>
{codebook}
</codebook>"""


def load_env(path=ROOT / '.env'):
    """KEY=value lines from .env; variables already set in the shell win."""
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            key, sep, value = line.partition('=')
            if sep and not key.strip().startswith('#') and value.strip():
                os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def user_message(item):
    parts = [f'{k}:\n{item[k]}' for k in ('context_post', 'context_parent', 'context_quote') if item.get(k)]
    parts.append(f'text (komentarz do zakodowania):\n{item["text"]}')
    if prefilled(item.get('slurs', ''), 'strict'):    # same pre-coding the human sheets get (pkt 4.12)
        parts.append('Arkusz ma wpisane hate = 1, hate_migrants = 1 (obelga ze słownika, pkt 4.12). '
                     'Zmień tylko przy fałszywym trafieniu.')
    return '\n\n'.join(parts)


def normalize(answer):
    """Labels as the sheets hold them; hate_migrants=1 without hate=1 is flagged, not kept."""
    hate, hm = str(answer.get('hate', '')), str(answer.get('hate_migrants', ''))
    note = str(answer.get('note', '')).strip()
    if hm == '1' and hate != '1':
        hm, note = '', f'[niedozwolona para 0/1] {note}'
    return {'hate': hate if hate in ('0', '1') else '', 'hate_migrants': hm if hm in ('0', '1') else '',
            'uncertain': '1' if answer.get('uncertain') else '', 'note': note}


class Claude:
    def __init__(self, model):
        import anthropic
        self.anthropic, self.client, self.model = anthropic, anthropic.Anthropic(), model

    def __call__(self, system, message):
        r = self.client.beta.messages.create(
            model=self.model, max_tokens=16000,
            system=[{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}],  # codebook cached
            messages=[{'role': 'user', 'content': message}],
            output_config={'effort': 'medium', 'format': {'type': 'json_schema', 'schema': SCHEMA}},
            betas=['server-side-fallback-2026-07-01'], fallbacks='default',
        )
        if r.stop_reason == 'refusal':
            raise RuntimeError(f'refusal ({getattr(r.stop_details, "category", None)})')
        return next(b.text for b in r.content if b.type == 'text'), r.model


class Gemini:
    def __init__(self, model):
        from google import genai
        self.genai, self.client, self.model = genai, genai.Client(), model

    def __call__(self, system, message):
        config = self.genai.types.GenerateContentConfig(
            system_instruction=system, response_mime_type='application/json', response_json_schema=SCHEMA)
        r = self.client.models.generate_content(model=self.model, contents=message, config=config)
        return r.text, self.model


class GPT:
    def __init__(self, model):
        from openai import OpenAI
        self.client, self.model = OpenAI(), model

    def __call__(self, system, message):
        r = self.client.responses.create(
            model=self.model, instructions=system, input=message,
            text={'format': {'type': 'json_schema', 'name': 'annotation', 'schema': SCHEMA, 'strict': True}})
        return r.output_text, r.model


PROVIDERS = {'claude': Claude, 'gemini': Gemini, 'gpt': GPT}


class Throttle:
    """At most rpm requests per minute across all workers (free tiers, e.g. Gemini: 15)."""
    def __init__(self, rpm=None):
        self.gap, self.next, self.lock = 60 / rpm if rpm else 0, 0.0, threading.Lock()

    def wait(self):
        with self.lock:
            now = time.monotonic()
            start = max(now, self.next)
            self.next = start + self.gap
        time.sleep(start - now)


def backoff(error, attempt):
    """Seconds to wait: the delay a rate-limit error asks for, else exponential."""
    text = str(error)
    m = re.search(r'retry (?:in|after) ([\d.]+) ?s', text, re.I)
    if m:
        return float(m.group(1)) + 1
    return 30 if re.search(r'429|rate.?limit|RESOURCE_EXHAUSTED', text, re.I) else 2 ** attempt


def annotate(call, system, item, tries=6, throttle=None):
    for attempt in range(tries):
        try:
            if throttle:
                throttle.wait()
            text, served_by = call(system, user_message(item))
            return {'item_id': item['item_id'], 'model': served_by, **normalize(json.loads(text))}
        except Exception as e:   # bad JSON, rate limits the SDK gave up on, the rest
            if attempt == tries - 1:
                return {'item_id': item['item_id'], 'error': f'{type(e).__name__}: {str(e)[:300]}'}
            time.sleep(backoff(e, attempt))


def read_done(path):
    if not path.exists():
        return {}
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    return {r['item_id']: r for r in rows if 'error' not in r}


def write_sheet(manifest, done, path):
    out = manifest[['item_id', 'context_post', 'context_parent', 'context_quote', 'text']].copy()   # as human sheets
    for col in ('hate', 'hate_migrants', 'uncertain', 'note'):
        out[col] = out['item_id'].map(lambda i: done.get(i, {}).get(col, ''))
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_excel(path, index=False)


def main():
    ap = argparse.ArgumentParser(description='Code an annotation round with an LLM.')
    ap.add_argument('--name', required=True, help='annotation round, e.g. pilot_v2')
    ap.add_argument('--model', required=True, choices=sorted(PROVIDERS))
    ap.add_argument('--model-id', help='overrides ANTHROPIC_MODEL / GEMINI_MODEL / OPENAI_MODEL from .env')
    ap.add_argument('--limit', type=int, help='only the first N items (test run)')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--rpm', type=float, help='max requests per minute, e.g. 14 for the Gemini free tier')
    args = ap.parse_args()

    load_env()
    env_var, default = MODELS[args.model]
    model_id = args.model_id or os.environ.get(env_var) or default
    if not model_id:
        sys.exit(f'Set {env_var} in .env or pass --model-id.')

    base = OUT_ROOT / args.name
    manifest = pd.read_csv(base / 'manifest.csv', encoding='utf-8-sig', dtype=str, keep_default_na=False)
    if args.limit:
        manifest = manifest.head(args.limit)
    log = base / 'llm' / f'{args.model}.jsonl'
    done = read_done(log)
    todo = [r for r in manifest.to_dict('records') if r['item_id'] not in done]
    print(f'{args.model} ({model_id}): {len(done)} already coded, {len(todo)} to go')

    system = SYSTEM.format(codebook=(ROOT / 'docs/CODEBOOK.md').read_text(encoding='utf-8'))
    call = PROVIDERS[args.model](model_id)
    log.parent.mkdir(parents=True, exist_ok=True)
    errors, throttle = 0, Throttle(args.rpm)
    with ThreadPoolExecutor(args.workers) as pool, log.open('a', encoding='utf-8') as f:
        for i, fut in enumerate(as_completed(pool.submit(annotate, call, system, r, throttle=throttle) for r in todo), start=1):
            row = {**fut.result(), 'requested_model': model_id, 'at': datetime.now(timezone.utc).isoformat()}
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
            f.flush()
            if 'error' in row:
                errors += 1
                print(f'  {row["item_id"]}: {row["error"]}')
            else:
                done[row['item_id']] = row
            if i % 25 == 0:
                print(f'  {i}/{len(todo)}')

    if not done:
        sys.exit(f'Nothing coded, {errors} errors - check the API key and model in .env.')
    sheet = base / 'annotated' / f'{args.name}_{args.model}.xlsx'
    write_sheet(manifest, done, sheet)
    print(f'{len(done)}/{len(manifest)} coded, {errors} errors (rerun to retry) -> {sheet}')


if __name__ == '__main__':
    main()
