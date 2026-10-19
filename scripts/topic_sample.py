#!/usr/bin/env python3
"""Trial run: label a RANDOM SAMPLE of comments in BATCHES with a local Ollama model:
   (1) is the comment about MIGRATION?   (2) is it HATE SPEECH?

    python scripts/topic_sample.py data/interim/bluesky/2024-05-28_Atak_Zolnierz_Granica/clean --n 100 --batch-size 10

Reads  <folder>/comments.csv and <folder>/posts.csv (the post text is given to the model as context).
Writes topic_sample.csv: model_migracja, model_hate and EMPTY columns human_migracja, human_hate
for manual labelling. Thinking mode is OFF ("think": false); the model returns labels only.
Prints timing, so you can estimate how long the whole dataset will take.
"""
import argparse
import csv
import json
import random
import time
from collections import Counter
from pathlib import Path

import requests

MIGR_LABELS = ['migracja', 'nie_migracja', 'niejasne']
HATE_LABELS = ['hate', 'nie_hate', 'niejasne']

# >>> EDIT: the operational definitions agreed in the team <<<
DEFINITION_MIGR = """MIGRACJA: komentarz dotyczy migrantów, uchodźców lub osób ubiegających się o azyl \
(w tym uchodźców z Ukrainy), polityki migracyjnej, ochrony granic w kontekście przekraczania ich przez migrantów \
(np. granica polsko-białoruska), deportacji, relokacji, integracji lub nielegalnej imigracji.
NIE MIGRACJA: komentarz dotyczy innych tematów (np. wojny samej w sobie, gospodarki, wyborów), \
nawet jeśli pada pod wpisem o migracji, a sam go nie dotyka.
NIEJASNE: z treści komentarza i wpisu nie da się rozstrzygnąć."""

DEFINITION_HATE = """HATE: komentarz atakuje, poniża, dehumanizuje, stygmatyzuje lub nawołuje do przemocy, wrogości \
albo dyskryminacji wobec osoby lub grupy ze względu na narodowość, pochodzenie, rasę, religię, status migranta \
lub uchodźcy albo inną cechę grupową (także w formie ironii, obelg i wulgaryzmów skierowanych w grupę).
NIE HATE: krytyka polityki, rządu, prawa lub zjawiska bez ataku na grupę ludzi jako takich, także ostra i emocjonalna; \
wulgaryzm niekierowany w grupę; wypowiedź neutralna.
NIEJASNE: nie da się rozstrzygnąć bez dodatkowego kontekstu.
Oceniaj samą treść komentarza (wpis służy tylko do zrozumienia kontekstu)."""

# Przykłady wplecione w kontekst systemowy dla klasyfikacji w paczkach
EXAMPLES_PROMPT = """Przykłady poprawnej klasyfikacji:
Wpis: Straż Graniczna: kolejna próba forsowania granicy | Komentarz: Trzeba zamknąć granicę i koniec.
-> {"migracja": "migracja", "hate": "nie_hate"}

Wpis: Nowy pakt migracyjny UE | Komentarz: Ci ludzie to zwierzęta, nie powinno ich tu być.
-> {"migracja": "migracja", "hate": "hate"}

Wpis: Wyniki sondażu partyjnego | Komentarz: Ten sondaż to ściema.
-> {"migracja": "nie_migracja", "hate": "nie_hate"}
"""

BATCH_SCHEMA = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'index': {'type': 'integer'},
            'migracja': {'enum': MIGR_LABELS},
            'hate': {'enum': HATE_LABELS}
        },
        'required': ['index', 'migracja', 'hate']
    }
}


def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def build_batch_messages(batch):
    system = (
        'Jesteś asystentem badawczym. Oceniasz listę komentarzy z mediów społecznościowych w dwóch '
        'niezależnych wymiarach.\n\n'
        f'{DEFINITION_MIGR}\n\n{DEFINITION_HATE}\n\n'
        f'{EXAMPLES_PROMPT}\n'
        'Dla każdego numerowanego elementu z listy zwróć wynik jako obiekt w tablicy JSON '
        'w DOKŁADNIE tej samej kolejności:\n'
        f'[{{"index": 1, "migracja": jedna z {MIGR_LABELS}, "hate": jedna z {HATE_LABELS}}}]'
    )
    
    items_text = []
    for item in batch:
        items_text.append(
            f"--- ELEMENT {item['index']} ---\n"
            f"Wpis: {item['post_context']}\n"
            f"Komentarz: {item['text'][:1500]}"
        )
    
    user_content = "Oceń poniższą listę komentarzy:\n\n" + "\n\n".join(items_text)
    
    return [
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': user_content}
    ]


THINK_OFF_SUPPORTED = True
THINKING_SEEN = 0


def classify_batch(host, model, batch):
    """Classifies a list of items and returns a list of (migracja, hate) tuples."""
    global THINK_OFF_SUPPORTED, THINKING_SEEN
    body = {
        'model': model,
        'stream': False,
        'format': BATCH_SCHEMA,
        'messages': build_batch_messages(batch),
        'options': {'temperature': 0, 'seed': 1}
    }
    if THINK_OFF_SUPPORTED:
        body['think'] = False

    r = requests.post(f'{host}/api/chat', timeout=300, json=body)
    if r.status_code == 400 and 'think' in r.text.lower() and THINK_OFF_SUPPORTED:
        THINK_OFF_SUPPORTED = False
        body.pop('think')
        r = requests.post(f'{host}/api/chat', timeout=300, json=body)

    r.raise_for_status()
    msg = r.json()['message']
    if (msg.get('thinking') or '').strip():
        THINKING_SEEN += 1

    content = msg.get('content', '')
    parsed = json.loads(content)

    # Rozpakuj jeśli model opakował tablicę w obiekt
    if isinstance(parsed, dict):
        for v in parsed.values():
            if isinstance(v, list):
                parsed = v
                break

    results = []
    for i in range(len(batch)):
        res_item = parsed[i] if (isinstance(parsed, list) and i < len(parsed) and isinstance(parsed[i], dict)) else {}
        
        migr = res_item.get('migracja')
        hate = res_item.get('hate')
        
        if migr not in MIGR_LABELS or hate not in HATE_LABELS:
            migr, hate = 'BLAD', 'BLAD'
            
        results.append((migr, hate))

    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', help='folder with comments.csv and posts.csv (e.g. .../clean)')
    ap.add_argument('--n', type=int, default=100)
    ap.add_argument('--batch-size', type=int, default=10, help='Batch size for parallel comment processing')
    ap.add_argument('--model', default='qwen2.5:7b')
    ap.add_argument('--host', default='http://localhost:11434')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--out', default='topic_sample.csv')
    args = ap.parse_args()

    folder = Path(args.folder)
    posts = {p['post_id']: p for p in read_csv(folder / 'posts.csv')}
    comments = [c for c in read_csv(folder / 'comments.csv') if (c.get('text') or '').strip()]
    random.Random(args.seed).shuffle(comments)
    sample = comments[:args.n]
    print(f'{len(comments)} comments in folder, labelling {len(sample)} with {args.model} (batch size: {args.batch_size})\n')

    rows, errors, t0 = [], 0, time.time()

    for batch_start in range(0, len(sample), args.batch_size):
        batch_comments = sample[batch_start : batch_start + args.batch_size]
        
        prepared_batch = []
        for idx, c in enumerate(batch_comments, start=1):
            p = posts.get(c['post_id'], {})
            post_ctx = (p.get('title') or p.get('text') or '').strip().replace('\n', ' ')[:300]
            prepared_batch.append({
                'index': idx,
                'comment_id': c['comment_id'],
                'post_id': c['post_id'],
                'post_context': post_ctx,
                'text': c['text'],
            })

        t_batch = time.time()
        try:
            labels = classify_batch(args.host, args.model, prepared_batch)
        except Exception as e:
            print(f'  error on batch {batch_start // args.batch_size + 1}: {str(e)[:120]}')
            labels = [('BLAD', 'BLAD') for _ in prepared_batch]
            errors += len(prepared_batch)

        elapsed_batch = round(time.time() - t_batch, 2)
        per_item_batch = round(elapsed_batch / len(prepared_batch), 2)

        for item, (migr, hate) in zip(prepared_batch, labels):
            if migr == 'BLAD':
                errors += 1
            rows.append({
                'comment_id': item['comment_id'],
                'post_id': item['post_id'],
                'post_context': item['post_context'],
                'text': item['text'],
                'model_migracja': migr,
                'model_hate': hate,
                'human_migracja': '',
                'human_hate': '',
                'seconds': per_item_batch
            })

        processed = len(rows)
        print(f'{processed}/{len(sample)} done | batch: {elapsed_batch}s (~{per_item_batch}s/item) | last: {labels[-1][0]} / {labels[-1][1]}', flush=True)

    with open(args.out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    total = time.time() - t0
    per = total / max(len(rows), 1)
    print(f'\nmigracja: {dict(Counter(r["model_migracja"] for r in rows))}')
    print(f'hate:     {dict(Counter(r["model_hate"] for r in rows))}   errors: {errors}')
    if THINKING_SEEN:
        print(f'WARNING: {THINKING_SEEN} answers still contained thinking text - thinking is NOT fully off '
              'for this model (slower). Try another model or tag.')
    print(f'Time: {total:.0f} s total, {per:.2f} s per comment  ->  ~{3600 / per:.0f} comments per hour')
    print(f'Saved {args.out}. Fill human_migracja and human_hate in Excel.')


if __name__ == '__main__':
    main()