#!/usr/bin/env python3
"""Liczy komentarze z wykopu (event) na kolejnych etapach selekcji z topic_sample.py.

Etapy (jak w topic_sample):
  1. komentarze ze slurs z hate_auto=1 i hate_migrants_auto=1 (łączenie po comment_id) -> bez LLM
  2. pozostałe: filtr słownikowy (regex) na komentarzu + kontekście posta
  3. to, co przejdzie regex, trafiłoby do LLM

Usage:
    python scripts/count_topic_filter.py
    python scripts/count_topic_filter.py --out pakt_to_llm.csv
"""

import argparse
import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from topic_sample import is_potential_migration, load_prelabeled_ids, read_csv  # noqa: E402

EVENT_DIR = 'data/interim/wykop/2024-04-10_Pakt_Azyl_PE'
event = {
"Pakt_Azyl_PE": "2024-04-10",
"Smierc_Zolnierza": "2024-06-06",
"Bojka_Srem": "2024-09-08",
"Strategia_Migracyjna": "2024-10-12",
"Dezinformacja_Krakow": "2025-10-15",
"Ceuta_Masowe_Przekroczenie": "2026-07-30",
"Atak_Kamienna_Gora": "2026-08-15", 
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--folder', default=f'{EVENT_DIR}/clean', help='Folder z comments.csv i posts.csv')
    ap.add_argument('--slurs-csv', default=f'{EVENT_DIR}/slurs/comments.csv',
                    help='Plik slurs (comment_id, hate_auto, hate_migrants_auto)')
    ap.add_argument('--out', default=None, help='Opcjonalnie: zapis komentarzy, które trafiłyby do LLM')
    ap.add_argument('--show', type=int, default=30, help='Ile odrzuconych komentarzy wypisać (domyślnie: 30)')
    ap.add_argument('--seed', type=int, default=42, help='Seed losowania próbki odrzuconych')
    args = ap.parse_args()

    folder = Path(args.folder)
    posts = {p['post_id']: p for p in read_csv(folder / 'posts.csv')}
    comments = [c for c in read_csv(folder / 'comments.csv') if (c.get('text') or '').strip()]

    # comment_id z slurs, gdzie hate=1 i hate_migrants=1
    slur_ids = load_prelabeled_ids(args.slurs_csv)
    slurs_rows = len(read_csv(args.slurs_csv))

    slur_11, rejected, to_llm = 0, [], []
    for c in comments:
        cid = str(c.get('comment_id', '')).strip()
        if cid in slur_ids:
            slur_11 += 1
            continue

        p = posts.get(c['post_id'], {})
        post_ctx = (p.get('title') or p.get('text') or '').strip().replace('\n', ' ')[:300]
        if is_potential_migration(c['text'], post_ctx):
            to_llm.append(c)
        else:
            rejected.append(c)

    regex_rejected = len(rejected)
    total = len(comments)
    pct = lambda n: f'{n / max(total, 1):.1%}'  # noqa: E731
    print(f'Folder: {folder}')
    print(f'Slurs:  {args.slurs_csv} ({slurs_rows} wierszy)')
    print()
    print(f'Wszystkie komentarze (niepuste):                 {total}')
    print(f'  slurs hate=1 & hate_migrants=1 (bez LLM):      {slur_11} ({pct(slur_11)})')
    print(f'  odrzucone filtrem regex:                       {regex_rejected} ({pct(regex_rejected)})')
    print(f'  trafiłyby do LLM:                              {len(to_llm)} ({pct(len(to_llm))})')
    print(f'Po filtrowaniu łącznie (slurs 1/1 + do LLM):     {slur_11 + len(to_llm)} ({pct(slur_11 + len(to_llm))})')

    # losowa próbka odrzuconych komentarzy do ręcznego przejrzenia
    sample = random.Random(args.seed).sample(rejected, min(args.show, len(rejected)))
    print(f'\n--- {len(sample)} losowych komentarzy odrzuconych przez regex ---')
    for i, c in enumerate(sample, 1):
        text = ' '.join(c['text'].split())
        print(f'{i:>2}. [{c.get("comment_id", "")}] {text[:300]}')

    if args.out and to_llm:
        with open(args.out, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(to_llm[0]))
            w.writeheader()
            w.writerows(to_llm)
        print(f'\nZapisano: {args.out}')


if __name__ == '__main__':
    main()
