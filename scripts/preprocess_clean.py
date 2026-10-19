"""Step 2: remove emoji, links and mentions from the texts kept by step 1.

    python scripts/preprocess_clean.py --platform bluesky --event 2024-04-10_Pakt_Azyl_PE

Reads  data/interim/<platform>/<event>/filtered/{posts,comments}.csv
Writes data/interim/<platform>/<event>/clean/{posts,comments}.csv  (text = cleaned, text_raw = original)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.preprocessing.cleaning import clean_frame
from src.preprocessing.io import INTERIM_ROOT, SOURCES, read_csv, write_csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--platform', required=True)
    ap.add_argument('--event', required=True)
    args = ap.parse_args()

    root = INTERIM_ROOT / args.platform / args.event
    for name in SOURCES:
        df = clean_frame(read_csv(root / 'filtered' / f'{name}.csv'))
        write_csv(df, root / 'clean' / f'{name}.csv')
        print(f'{args.event} {name}: {len(df)} cleaned')


if __name__ == '__main__':
    main()
