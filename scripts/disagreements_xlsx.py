"""results/disagreements.csv -> results/disagreements.xlsx for resolving disagreements in Excel.
    python scripts/disagreements_xlsx.py --name pilot_v2
hate / hate_migrants are dropdowns (no '1/1' turning into a date); rerunning keeps what is already filled.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_sample import OUT_ROOT  # noqa: E402
from gold_build import pair, write_review  # noqa: E402

FILLED = ['hate', 'hate_migrants', 'note', 'codebook_change']


def to_sheet(dis, previous=None):
    """Disagreements with decision columns, prefilled from the csv 'decision' and an earlier xlsx."""
    df = dis.copy()
    decided = df.pop('decision') if 'decision' in df else pd.Series('', index=df.index)
    p = decided.map(lambda d: pair(*(str(d).replace('-', '/').split('/') + [''])[:2]) if str(d).strip() else '')
    df['hate'], df['hate_migrants'] = p.str[:1], p.str[2:]
    df['note'] = ''
    df['codebook_change'] = df.pop('codebook_change') if 'codebook_change' in df else ''
    if previous is not None:
        prev = previous.set_index('item_id')
        for col in FILLED:
            if col in prev:
                old = df['item_id'].map(prev[col]).fillna('')
                df[col] = old.where(old != '', df[col])
    return df.fillna('')


def main():
    ap = argparse.ArgumentParser(description='Disagreements of a round as an Excel sheet for adjudication.')
    ap.add_argument('--name', required=True, help='annotation round, e.g. pilot_v2')
    args = ap.parse_args()

    res = OUT_ROOT / args.name / 'results'
    src, out = res / 'disagreements.csv', res / 'disagreements.xlsx'
    if not src.exists():
        sys.exit(f'{src} not found - run: python scripts/annotation_agreement.py --name {args.name}')
    dis = pd.read_csv(src, encoding='utf-8-sig', dtype=str, keep_default_na=False)
    previous = pd.read_excel(out, dtype=str).fillna('') if out.exists() else None
    sheet = to_sheet(dis, previous)
    write_review(sheet, out)
    done = (sheet['hate'] != '').sum()
    print(f'{len(sheet)} disagreements ({done} already decided) -> {out}')


if __name__ == '__main__':
    main()
