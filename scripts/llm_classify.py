#!/usr/bin/env python3
"""Step 5: LLM classification (Groq / Gemini) of the topic pre-filtered comments of one event.

Prompt (summary of docs/CODEBOOK.md) and API clients from scripts/llm_gold_test.py.
hate is judged for every comment (codebook); --hate-migration-only restores hate=0 outside migration.
Slur-labelled 1/1 comments get 1/1/1 without the LLM. Results are appended after every batch,
so a rerun (e.g. after hitting the daily limit) continues with the comments not yet classified.

    python scripts/llm_classify.py --platform bluesky --event 2026-09-15_Raport_SG_Statystyki_Deportacje
    python scripts/llm_classify.py --platform bluesky --event <event> --provider groq --batch-size 20
    python scripts/llm_classify.py --platform wykop --event Atak_Zolnierz_Granica --window 0:7
    python scripts/llm_classify.py --platform youtube --event <event> --window -7:-1 0:3 10

--event: full folder name (2024-05-28_Atak_Zolnierz_Granica) or just the name after the date.
--window: day ranges relative to day 0 of the event (relative_day), inclusive, e.g. 0:7, -7:-1, 3.
          Several ranges may be given; without --window all comments of the event are classified.

Reads  data/interim/<platform>/<event>/topic/comments.csv
       data/interim/<platform>/<event>/clean/{posts,comments}.csv   (post / parent context)
Writes data/interim/<platform>/<event>/llm/comments.csv
       (comment_id, event, text, llm_is_about_migration, llm_is_hate_migrants, llm_is_hate_general,
        source, model)
       data/interim/<platform>/<event>/llm/report.json
"""
import argparse
import csv
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.preprocessing.io import INTERIM_ROOT, read_csv, write_json
from llm_gold_test import Gemini, Groq, make_messages, parse_results

ROOT = Path(__file__).resolve().parents[1]
MIG, HATE_MIG, HATE = 'llm_is_about_migration', 'llm_is_hate_migrants', 'llm_is_hate_general'
COLUMNS = ['comment_id', 'event', 'text', MIG, HATE_MIG, HATE, 'source', 'model']
DEFAULT_MODEL = {'groq': 'qwen/qwen3.8-27b', 'gemini': 'gemini-3.5-flash-lite'}


def parse_window(spec):
    """'0:7' -> (0, 7), '3' -> (3, 3); days relative to day 0, inclusive."""
    try:
        lo, _, hi = spec.partition(':')
        lo, hi = int(lo), int(hi or lo)
    except ValueError:
        raise argparse.ArgumentTypeError(f'zły zakres okna: {spec!r} (np. 0:7, -7:-1, 3)')
    if lo > hi:
        raise argparse.ArgumentTypeError(f'zły zakres okna: {spec!r} (początek > koniec)')
    return lo, hi


def format_window(window):
    return ', '.join(f'{lo}..{hi}' for lo, hi in window)


def resolve_event(platform, event):
    """Accepts the full folder name or the event name without the date prefix."""
    base = INTERIM_ROOT / platform
    if (base / event).is_dir():
        return event
    matches = sorted(d.name for d in base.glob(f'*_{event}') if d.is_dir())
    if len(matches) == 1:
        return matches[0]
    sys.exit(f'Brak wydarzenia {event!r} dla {platform}' if not matches
             else f'Niejednoznaczne wydarzenie {event!r}: {matches}')


def main():
    ap = argparse.ArgumentParser()
    # pozwala podać ujemne zakresy bez '=', np. --window -7:-1 0:7
    ap._negative_number_matcher = re.compile(r'^-\d+(:-?\d+)?$')
    ap.add_argument('--platform', required=True)
    ap.add_argument('--event', required=True)
    ap.add_argument('--window', nargs='+', type=parse_window, default=None, metavar='A:B',
                    help='Zakresy dni względem dnia 0 (włącznie), np. 0:7 -7:-1; brak = całe okno')
    ap.add_argument('--provider', choices=['groq', 'gemini'], default='gemini')
    ap.add_argument('--model', default=None)
    ap.add_argument('--batch-size', type=int, default=50)
    ap.add_argument('--rpm', type=int, default=10, help='Gemini: limit zapytań/min')
    ap.add_argument('--hate-migration-only', dest='hate_all', action='store_false',
                    help='Oceniaj hate tylko w komentarzach o migracji (domyślnie: we wszystkich)')
    args = ap.parse_args()

    load_dotenv(ROOT / '.env.local')
    load_dotenv(ROOT / '.env')
    key_name = 'GROQ_API_KEY' if args.provider == 'groq' else 'GOOGLE_API_KEY'
    api_key = os.environ.get(key_name) or sys.exit(f'Brak {key_name} w .env.local / środowisku')
    model = args.model or DEFAULT_MODEL[args.provider]
    max_tokens = max(2048, 80 * args.batch_size)
    client = (Groq(api_key, model, max_tokens) if args.provider == 'groq'
              else Gemini(api_key, model, max_tokens, args.rpm))

    args.event = resolve_event(args.platform, args.event)
    root = INTERIM_ROOT / args.platform / args.event
    topic = read_csv(root / 'topic' / 'comments.csv')
    clean = read_csv(root / 'clean' / 'comments.csv').set_index('comment_id')
    if args.window:
        day = topic['comment_id'].map(clean['relative_day']).astype(int)
        in_window = sum((day >= lo) & (day <= hi) for lo, hi in args.window) > 0
        print(f'Okno {format_window(args.window)}: {int(in_window.sum())}/{len(topic)} komentarzy z topic')
        topic = topic[in_window]
    posts = read_csv(root / 'clean' / 'posts.csv').set_index('post_id')
    by_id = clean['text'].to_dict()

    def post_context(post_id):
        if post_id not in posts.index:
            return ''
        p = posts.loc[post_id]
        return (p.get('title') or p.get('text') or '').strip().replace('\n', ' ')[:300]

    out_path = root / 'llm' / 'comments.csv'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = set(read_csv(out_path)['comment_id']) if out_path.exists() else set()
    new_file = not out_path.exists()
    if not new_file and list(read_csv(out_path).columns) != COLUMNS:
        sys.exit(f'{out_path} ma stary układ kolumn - usuń go i uruchom ponownie')
    f = open(out_path, 'a', encoding='utf-8-sig' if new_file else 'utf-8', newline='')
    writer = csv.DictWriter(f, fieldnames=COLUMNS)
    if new_file:
        writer.writeheader()

    todo = []
    for r in topic.to_dict('records'):
        if r['comment_id'] in done:
            continue
        if r['hate_auto'] == '1' and r['hate_migrants_auto'] == '1':
            writer.writerow({**{k: r[k] for k in ['comment_id', 'event', 'text']},
                             MIG: '1', HATE_MIG: '1', HATE: '1',
                             'source': 'slur', 'model': ''})
            continue
        c = clean.loc[r['comment_id']] if r['comment_id'] in clean.index else {}
        todo.append({**r,
                     'post_context': post_context(c.get('post_id', '')),
                     'parent_context': (by_id.get(c.get('reply_to', '')) or '').strip().replace('\n', ' ')[:300]})
    f.flush()
    print(f'{args.platform} {args.event}: {len(topic)} w topic, już zrobione {len(done)}, '
          f'do LLM {len(todo)} | {args.provider} {model}, batch {args.batch_size}')

    errors, t0 = 0, time.time()
    est_tokens = None
    try:
        for start in range(0, len(todo), args.batch_size):
            chunk = todo[start:start + args.batch_size]
            batch = [{'index': i, 'post_context': it['post_context'],
                      'parent_context': it['parent_context'], 'text': it['text']}
                     for i, it in enumerate(chunk, start=1)]
            messages = make_messages(batch, args.hate_all)
            if est_tokens is None:
                est_tokens = sum(len(m['content']) for m in messages) // 3 + 400
            try:
                labels = parse_results(client.chat(messages, est_tokens), len(batch))
            except RuntimeError as e:
                print(f'STOP: {e}\nUruchom ponownie później - skrypt dokończy pozostałe komentarze.')
                break
            except Exception as e:
                print(f'  błąd API w paczce od {start + 1}: {str(e)[:200]}')
                labels = [None] * len(batch)
            if client.usage['requests']:
                est_tokens = int(client.usage['total_tokens'] / client.usage['requests'] * 1.1)

            for it, lab in zip(chunk, labels):
                if lab is None:
                    errors += 1
                    continue
                writer.writerow({'comment_id': it['comment_id'], 'event': it['event'], 'text': it['text'],
                                 MIG: lab[0], HATE_MIG: lab[2], HATE: lab[1],
                                 'source': 'llm', 'model': model})
            f.flush()
            print(f'{min(start + len(chunk), len(todo))}/{len(todo)} | błędy {errors} | '
                  f'{time.time() - t0:.0f}s | tokeny {client.usage["total_tokens"]}', flush=True)
    except KeyboardInterrupt:
        print('\nPrzerwano - wyniki do tej pory są zapisane.')
    finally:
        f.close()

    res = read_csv(out_path)
    res = res[res['comment_id'].isin(set(topic['comment_id']))]
    report = {
        'platform': args.platform, 'event': args.event,
        'provider': args.provider, 'model': model, 'batch_size': args.batch_size, 'hate_all': args.hate_all,
        'window': [list(w) for w in args.window] if args.window else 'all',
        'topic_comments': len(topic),
        'classified': len(res),
        'remaining': len(topic) - len(res),
        'errors_last_run': errors,
        'by_source': dict(Counter(res['source'])),
        MIG: dict(Counter(res[MIG])),
        HATE_MIG: dict(Counter(res[HATE_MIG])),
        HATE: dict(Counter(res[HATE])),
        'last_run_seconds': round(time.time() - t0, 1),
        'last_run_tokens': client.usage['total_tokens'],
    }
    write_json(report, root / 'llm' / 'report.json')
    print(f'\nSklasyfikowano {len(res)}/{len(topic)} (pozostało {report["remaining"]}), błędy {errors}')
    print(f'{MIG} {report[MIG]} | {HATE_MIG} {report[HATE_MIG]} | {HATE} {report[HATE]}')
    print(f'Zapisano: {out_path}')


if __name__ == '__main__':
    main()
