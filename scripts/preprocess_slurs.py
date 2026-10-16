"""Step 3: find slurs from src/lexicon/slurs.py in the cleaned text
    python scripts/preprocess_slurs.py --platform wykop --event 2024-04-10_Pakt_Azyl_PE
Reads  data/interim/<platform>/<event>/clean/{posts,comments}.csv
Writes data/interim/<platform>/<event>/slurs/{posts,comments}.csv + report.json
       (id, slurs, slur_categories, slur_needs_context, hate_auto, hate_migrants_auto)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.lexicon.slurs import slur_columns
from src.preprocessing.io import INTERIM_ROOT, SOURCES, read_csv, write_csv, write_json

ID_COLUMN = {'posts': 'post_id', 'comments': 'comment_id'}


def flag_frame(df, id_col):
    out = pd.DataFrame({id_col: df[id_col]})
    cols = df['text'].map(slur_columns)
    out['slurs'], out['slur_categories'], out['slur_needs_context'] = zip(*cols) if len(df) else ([], [], [])
    # codebook pkt 4.12: slur = 1/1; terms that depend on context are listed but not pre-labelled
    out['hate_auto'] = ((out['slurs'] != '') & (out['slur_needs_context'] == '0')).astype(int)
    out['hate_migrants_auto'] = out['hate_auto']
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--platform', required=True)
    ap.add_argument('--event', required=True)
    args = ap.parse_args()

    root = INTERIM_ROOT / args.platform / args.event
    report = {'platform': args.platform, 'event': args.event}
    for name in SOURCES:
        out = flag_frame(read_csv(root / 'clean' / f'{name}.csv'), ID_COLUMN[name])
        write_csv(out, root / 'slurs' / f'{name}.csv')
        terms = out['slurs'][out['slurs'] != ''].str.split('; ').explode().value_counts()
        report[name] = {'rows': len(out), 'with_slur': int((out['slurs'] != '').sum()),
                        'prelabelled_1_1': int(out['hate_auto'].sum()),
                        'only_context_terms': int((out['slur_needs_context'] == '1').sum()),
                        'terms': {k: int(v) for k, v in terms.items()}}
        print(f'{args.event} {name}: {report[name]["with_slur"]}/{len(out)} with a slur')
    write_json(report, root / 'slurs' / 'report.json')


if __name__ == '__main__':
    main()
