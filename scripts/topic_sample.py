#!/usr/bin/env python3
"""Automated, large-scale annotation script for social media comments via Ollama.

Optimizations included:
   1. Fast Python Regex filter (pre-filters non-migration noise in <1s for the entire dataset).
   2. Auto-joins pre-labeled 1/1 CSV (`--prelabeled-csv`), bypassing LLM inference.
   3. Uses embedded SHORT_CODEBOOK (~250 tokens) for maximum prefill speed.
   4. Processes remaining candidates in optimized JSON batches.

Usage:
    python scripts/topic_sample.py data/interim/bluesky/2024-05-28_Atak_Zolnierz_Granica/clean \
        --prelabeled-csv data/prelabeled.csv \
        --batch-size 15
"""

import argparse
import csv
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

import requests

# === SKRÓCONY CODEBOOK ZASZYTY W KODZIE ===
SHORT_CODEBOOK = """1. is_about_migration ("1"/"0"):
- "1": dotyczy migrantów, uchodźców (w tym z Ukrainy), granicy, deportacji, relokacji, paktu migracyjnego, nielegalnej imigracji.
- "0": inne tematy (polityka krajowa, wojna w Rosji/Ukrainie bez wątku uchodźców, gospodarka, wybory).

2. hate ("1"/"0"):
- "1": obelga ("idioto", "lewaki"), dehumanizacja ("bydło", "dzicz"), stereotyp, wykluczenie ("wywieźć wszystkich"), przemoc ("strzelać do nich").
- "0": wulgaryzm bez adresata ("kurwa upał"), ostra krytyka polityki/ustawy/rządu ("ten minister kłamie").

3. hate_migrants ("1"/"0"):
- "1": hate=1 ORAZ atak dotyczy migrantów/Ukraińców/uchodźców/osób z Afryki/Azji ze względu na pochodzenie/status. Obelga etniczna ("ukry", "ciapaci", "nachodźcy") to ZAWSZE hate=1, hate_migrants=1!
- "0": hate dotyczy polityka, rozmówcy, Rosjan ("kacapy"), Polaków za granicą lub instytucji (rząd Ukrainy).

PRZYKŁADY:
- "Zamknąć granice!" -> is_about_migration:1, hate:0, hate_migrants:0
- "Ukry na socjalu" -> is_about_migration:1, hate:1, hate_migrants:1
- "Jebane kacapy" -> is_about_migration:0, hate:1, hate_migrants:0
- "Rząd to złodzieje" -> is_about_migration:0, hate:1, hate_migrants:0"""

# Fast Regex pre-filter for Polish migration & slur stems
MIGRATION_REGEX = re.compile(
    r'\b('
    # Pojęcia ogólne i polityczne
    r'migra|uchodź|azyl|reloka|deport|pakt|frontex|wiz[ay]|imigra|emigra|'
    r'granic|straż\s+granic|zapora|murem|pas\s+przygranicz|'
    # Grupy i narodowości w kontekście migracyjnym
    r'ukra|ukrop|bander|muzułm|arab|afryk|syryj|gruzin|czarnoskór|śniad|'
    r'cudzoziem|obcokraj|obcy|przybysze|'
    # Slang, obelgi i określenia ironiczne z codebooka
    r'ciapat|brudas|kozojeb|nachodź|ubogac|inżynier|lekarz'
    r')',
    re.IGNORECASE
)

BATCH_SCHEMA = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'index': {'type': 'integer'},
            'is_about_migration': {'type': ['string', 'integer', 'boolean']},
            'hate': {'type': ['string', 'integer', 'boolean']},
            'hate_migrants': {'type': ['string', 'integer', 'boolean']},
        },
        'required': ['index', 'is_about_migration', 'hate', 'hate_migrants'],
    },
}


def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def is_potential_migration(text: str, post_context: str = "", parent_context: str = "") -> bool:
    """Błyskawiczny filtr słownikowy w Pythonie (<0.0001s/item).
    Sprawdza, czy komentarz, wpis lub komentarz nadrzędny zawiera rdzenie słów migracyjnych.
    """
    full_text = f"{post_context} {parent_context} {text}"
    return bool(MIGRATION_REGEX.search(full_text))


def load_prelabeled_ids(prelabeled_csv_path):
    """Odczytuje plik prelabeled.csv i zwraca zbiór comment_id spełniających kryterium 1/1."""
    prelabeled_ids = set()
    if not prelabeled_csv_path:
        return prelabeled_ids

    path = Path(prelabeled_csv_path)
    if not path.exists():
        print(f"Ostrzeżenie: Plik pre-labeli {path} nie istnieje!", file=sys.stderr)
        return prelabeled_ids

    rows = read_csv(path)
    for r in rows:
        cid = str(r.get('comment_id', '')).strip()
        if not cid:
            continue

        h_auto = str(r.get('hate_auto', r.get('hate', ''))).strip().lower()
        hm_auto = str(r.get('hate_migrants_auto', r.get('hate_migrants', ''))).strip().lower()

        if h_auto in ['1', '1.0', 'true', 'yes'] and hm_auto in ['1', '1.0', 'true', 'yes']:
            prelabeled_ids.add(cid)

    return prelabeled_ids


def normalize_val(val):
    """Bezpieczna konwersja różnych formatów (bool, int, str) na "1" lub "0"."""
    if val is None:
        return None
    if isinstance(val, bool):
        return '1' if val else '0'
    s = str(val).strip().lower()
    if s in ['1', 'true', 'yes', 't']:
        return '1'
    if s in ['0', 'false', 'no', 'f']:
        return '0'
    return None


def build_batch_messages(batch, codebook_text=None):
    guidelines = codebook_text if codebook_text else SHORT_CODEBOOK

    system = (
        'Jesteś asystentem badawczym. Twoim pierwszym zadaniem jest odsiew komentarzy niezwiązanych z migracją, '
        'a drugim – ocena mowy nienawiści w komentarzach migracyjnych na podstawie poniższego skróconego codebooka.\n\n'
        '=== ZASADY ANNOTACJI ===\n'
        f'{guidelines}\n'
        '========================\n\n'
        'ZASADY SELEKCJI I OCENY:\n'
        '1. `is_about_migration`: Wpisz "1", jeśli komentarz dotyczy migracji, uchodźców, cudzoziemców, ochrony granic, '
        'deportacji lub polityki migracyjnej (nawet pośrednio). Oceniaj komentarz razem z kontekstem: '
        'jeśli odpowiada na wpis lub komentarz o migracji i odnosi się do jego treści, wpisz "1", '
        'nawet gdy sam nie zawiera słów kluczowych. Jeśli NIE dotyczy tego tematu, wpisz "0".\n'
        '2. Jeśli `is_about_migration` to "0", wpisz automatycznie `hate`: "0" i `hate_migrants`: "0".\n'
        '3. Jeśli `is_about_migration` to "1", dokonaj pełnej oceny `hate` oraz `hate_migrants` zgodnie z codebookiem.\n\n'
        'Dla każdego numerowanego elementu zwróć wynik jako obiekt w tablicy JSON w DOKŁADNIE tej samej kolejności:\n'
        '[{\n'
        '  "index": 1,\n'
        '  "is_about_migration": "1" lub "0",\n'
        '  "hate": "1" lub "0",\n'
        '  "hate_migrants": "1" lub "0"\n'
        '}]'
    )

    items_text = []
    for item in batch:
        items_text.append(
            f"--- ELEMENT {item['index']} ---\n"
            f"Wpis kontekstowy: {item['post_context']}\n"
            f"Komentarz nadrzędny (na który odpowiada): {item['parent_context'] or '(brak - odpowiedź na wpis)'}\n"
            f"Komentarz do oceny: {item['text'][:1000]}"
        )

    user_content = (
        'Oceń powiązanie z migracją i mowę nienawiści w poniższej liście komentarzy:\n\n'
        + '\n\n'.join(items_text)
    )

    return [
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': user_content},
    ]


THINK_OFF_SUPPORTED = True
THINKING_SEEN = 0


def classify_batch(host, model, batch, codebook_text=None, num_ctx=4096):
    """Classifies items and returns a list of (is_about_migration, hate, hate_migrants) tuples."""
    global THINK_OFF_SUPPORTED, THINKING_SEEN
    body = {
        'model': model,
        'stream': False,
        'format': BATCH_SCHEMA,
        'messages': build_batch_messages(batch, codebook_text),
        'options': {'temperature': 0, 'seed': 1, 'num_ctx': num_ctx},
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

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    parsed = v
                    break
    except Exception:
        parsed = []

    results = []
    for i in range(len(batch)):
        res_item = (
            parsed[i]
            if (
                isinstance(parsed, list)
                and i < len(parsed)
                and isinstance(parsed[i], dict)
            )
            else {}
        )

        is_migr = normalize_val(res_item.get('is_about_migration'))
        hate = normalize_val(res_item.get('hate'))
        hate_migrants = normalize_val(res_item.get('hate_migrants'))

        if is_migr is None or hate is None or hate_migrants is None:
            is_migr, hate, hate_migrants = 'BLAD', 'BLAD', 'BLAD'

        results.append((is_migr, hate, hate_migrants))

    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', help='Folder z plikami comments.csv i posts.csv')
    ap.add_argument('--prelabeled-csv', default=None, help='Ścieżka do pliku z pre-labelami (comment_id, hate_auto, hate_migrants_auto)')
    ap.add_argument('--n', type=int, default=0, help='Liczba komentarzy do przetworzenia (0 = WSZYSTKIE)')
    ap.add_argument('--batch-size', type=int, default=15, help='Rozmiar paczki zapytań (domyślnie: 15)')
    ap.add_argument('--codebook', default=None, help='Opcjonalna ścieżka do pliku codebooka (nadpisuje wbudowany skrócony)')
    ap.add_argument('--num-ctx', type=int, default=4096, help='Rozmiar okna kontekstu Ollamy (domyślnie: 4096)')
    ap.add_argument('--model', default='qwen2.5:7b')
    ap.add_argument('--host', default='http://localhost:11434')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--out', default='topic_sample.csv')
    args = ap.parse_args()

    codebook_text = None
    if args.codebook:
        cb_path = Path(args.codebook)
        if cb_path.exists():
            codebook_text = cb_path.read_text(encoding='utf-8')
            print(f"Wczytano zewnętrzny codebook z: {cb_path}")
        else:
            print(f"Ostrzeżenie: Plik {cb_path} nie istnieje. Używam wbudowanego skróconego codebooka.")
    else:
        print("Używam wbudowanego, skróconego codebooka (optymalizacja prędkości).")

    # Wczytanie identyfikatorów z pliku pre-labeli
    prelabeled_ids = load_prelabeled_ids(args.prelabeled_csv) if args.prelabeled_csv else set()
    if args.prelabeled_csv:
        print(f"Znaleziono {len(prelabeled_ids)} komentarzy oznaczonych jako 1/1 w pliku {args.prelabeled_csv}")

    folder = Path(args.folder)
    posts = {p['post_id']: p for p in read_csv(folder / 'posts.csv')}
    comments = [c for c in read_csv(folder / 'comments.csv') if (c.get('text') or '').strip()]
    by_id = {c.get('comment_id', ''): c.get('text', '') for c in comments}

    def parent_ctx(c, limit=300):
        return (by_id.get(c.get('reply_to') or '', '')).strip().replace('\n', ' ')[:limit]

    if args.n > 0:
        random.Random(args.seed).shuffle(comments)
        sample = comments[:args.n]
        print(f'{len(comments)} komentarzy w folderze, pobrano próbkę n={len(sample)}')
    else:
        sample = comments
        print(f'Przetwarzanie WSZYSTKICH {len(sample)} komentarzy z folderu...')

    rows = []
    to_classify_sample = []
    prelabeled_count = 0
    quick_skipped_count = 0

    # KROK 1: Pre-selekcja w Pythonie (Pre-labele 1/1 + szybki filtr Regex)
    for c in sample:
        cid = str(c.get('comment_id', '')).strip()
        p = posts.get(c['post_id'], {})
        post_ctx = (p.get('title') or p.get('text') or '').strip().replace('\n', ' ')[:300]
        text = c.get('text', '')
        par_ctx = parent_ctx(c)

        # A. Przypisanie 1/1 z pre-labeli
        if cid in prelabeled_ids:
            rows.append({
                'comment_id': cid,
                'post_id': c['post_id'],
                'post_context': post_ctx,
                'parent_context': par_ctx,
                'text': text,
                'model_hate': '1',
                'model_hate_migrants': '1',
                'human_hate': '',
                'human_hate_migrants': '',
                'seconds': 0.0,
            })
            prelabeled_count += 1
            continue

        # B. Odsiew w Pythonie (komentarze niemające nic wspólnego z migracją)
        # regex działa na pełnych tekstach (tanio); obcięcie 300 znaków dotyczy tylko promptu LLM
        post_full = (p.get('title') or p.get('text') or '').strip().replace('\n', ' ')
        if not is_potential_migration(text, post_full, parent_ctx(c, None)):
            quick_skipped_count += 1
            continue

        # C. Komentarze przechodzące do oceny przez LLM
        to_classify_sample.append(c)

    print(f'-> Automatycznie przypisano 1/1 (prelabeled): {prelabeled_count}')
    print(f'-> Błyskawicznie odrzucono filtrem słownikowym w Pythonie: {quick_skipped_count}')
    print(f'-> Do przetworzenia przez LLM pozostało: {len(to_classify_sample)} z {len(sample)} komentarzy!\n')

    llm_skipped_count, errors, t0 = 0, 0, time.time()

    # KROK 2: Przetwarzanie pozostałych komentarzy w paczkach przez Ollamę
    for batch_start in range(0, len(to_classify_sample), args.batch_size):
        batch_comments = to_classify_sample[batch_start : batch_start + args.batch_size]

        prepared_batch = []
        for idx, c in enumerate(batch_comments, start=1):
            p = posts.get(c['post_id'], {})
            post_ctx = (p.get('title') or p.get('text') or '').strip().replace('\n', ' ')[:300]
            prepared_batch.append({
                'index': idx,
                'comment_id': c['comment_id'],
                'post_id': c['post_id'],
                'post_context': post_ctx,
                'parent_context': parent_ctx(c),
                'text': c['text'],
            })

        t_batch = time.time()
        try:
            labels = classify_batch(args.host, args.model, prepared_batch, codebook_text, args.num_ctx)
        except Exception as e:
            print(f'  błąd połączenia/api w paczce od {batch_start + 1}: {str(e)[:120]}')
            labels = [('BLAD', 'BLAD', 'BLAD') for _ in prepared_batch]

        elapsed_batch = round(time.time() - t_batch, 2)
        per_item_batch = round(elapsed_batch / len(prepared_batch), 2)

        for item, (is_migr, hate, hate_migrants) in zip(prepared_batch, labels):
            if is_migr == 'BLAD':
                errors += 1
                continue

            # Odsiewanie komentarzy uznanych przez LLM za nie-migracyjne
            if is_migr == '0':
                llm_skipped_count += 1
                continue

            rows.append({
                'comment_id': item['comment_id'],
                'post_id': item['post_id'],
                'post_context': item['post_context'],
                'parent_context': item['parent_context'],
                'text': item['text'],
                'model_hate': hate,
                'model_hate_migrants': hate_migrants,
                'human_hate': '',
                'human_hate_migrants': '',
                'seconds': per_item_batch,
            })

        processed_so_far = len(rows) - prelabeled_count + llm_skipped_count + errors
        print(
            f'{processed_so_far}/{len(to_classify_sample)} przeanalizowane przez LLM | '
            f'zapisano łączną liczbę (z prelabeled): {len(rows)} | '
            f'odrzucono przez LLM: {llm_skipped_count} | '
            f'błędy: {errors} | '
            f'paczka: {elapsed_batch}s (~{per_item_batch}s/item)',
            flush=True
        )

    if not rows:
        print("\nNie znaleziono żadnych komentarzy spełniających kryteria do zapisu.")
        return

    with open(args.out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    total = time.time() - t0
    total_processed_all = len(sample)
    total_skipped = quick_skipped_count + llm_skipped_count
    per = total / max(len(to_classify_sample), 1)

    print(f'\n--- PODSUMOWANIE ---')
    print(f'Łącznie w zbiorze: {total_processed_all} komentarzy')
    print(f'Automatycznie zapisane (1/1 z pre-labeli): {prelabeled_count}')
    print(f'Odrzucono filtrem słownikowym w Pythonie: {quick_skipped_count}')
    print(f'Przeanalizowane przez Ollamę: {len(to_classify_sample)}')
    print(f'Odrzucono przez LLM (brak związku z migracją): {llm_skipped_count}')
    print(f'Suma odrzuconych (nie-migracyjne): {total_skipped}')
    print(f'Błędy parsowania / Ollamy: {errors}')
    print(f'Zapisano łącznie do pliku {args.out}: {len(rows)}')
    print(f'Rozkład model_hate w zapisanych:          {dict(Counter(r["model_hate"] for r in rows))}')
    print(f'Rozkład model_hate_migrants w zapisanych: {dict(Counter(r["model_hate_migrants"] for r in rows))}')

    if THINKING_SEEN:
        print(f'UWAGA: {THINKING_SEEN} odpowiedzi zawierało sekcję thinking.')

    print(f'Czas Ollamy: {total:.0f} s łącznie, {per:.2f} s / komentarz')
    print(f'Zapisano przefiltrowany plik: {args.out}')


if __name__ == '__main__':
    main()