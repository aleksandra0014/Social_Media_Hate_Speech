"""Step 4: topic pre-filter (no LLM) - keep comments that are slur-labelled 1/1 or pass the migration regex
    python scripts/topic_filter.py --platform wykop --event 2024-04-10_Pakt_Azyl_PE
Reads  data/interim/<platform>/<event>/{clean,slurs}/{posts,comments}.csv
Writes data/interim/<platform>/<event>/topic/comments.csv           (comment_id, event, text, hate_auto, hate_migrants_auto)
       data/interim/<platform>/<event>/topic/excluded_comments.csv  (same columns, rejected by the regex)
       data/interim/<platform>/<event>/topic/report.json
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.preprocessing.io import INTERIM_ROOT, read_csv, write_csv, write_json
from topic_sample import is_potential_migration

COLUMNS = ['comment_id', 'event', 'text', 'hate_auto', 'hate_migrants_auto']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--platform', required=True)
    ap.add_argument('--event', required=True)
    args = ap.parse_args()

    root = INTERIM_ROOT / args.platform / args.event
    comments = read_csv(root / 'clean' / 'comments.csv')
    posts = read_csv(root / 'clean' / 'posts.csv').set_index('post_id')
    slurs = read_csv(root / 'slurs' / 'comments.csv')[['comment_id', 'hate_auto', 'hate_migrants_auto']]
    df = comments.merge(slurs, how='left', on='comment_id')
    df[['hate_auto', 'hate_migrants_auto']] = df[['hate_auto', 'hate_migrants_auto']].replace('', '0')
    df = df[df['text'].str.strip() != '']

    def post_context(post_id):
        if post_id not in posts.index:
            return ''
        p = posts.loc[post_id]
        return (p.get('title') or p.get('text') or '').strip().replace('\n', ' ')[:300]

    is_slur = (df['hate_auto'] == '1') & (df['hate_migrants_auto'] == '1')
    passes_regex = [is_potential_migration(t, post_context(p)) for t, p in zip(df['text'], df['post_id'])]
    keep = is_slur | pd.Series(passes_regex, index=df.index, dtype=bool)

    write_csv(df.loc[keep, COLUMNS], root / 'topic' / 'comments.csv')
    write_csv(df.loc[~keep, COLUMNS], root / 'topic' / 'excluded_comments.csv')

    total = len(df)
    report = {
        'platform': args.platform, 'event': args.event,
        'total_comments': total,
        'kept': int(keep.sum()),
        'kept_slur_1_1': int(is_slur.sum()),
        'kept_regex_only': int((keep & ~is_slur).sum()),
        'rejected_by_regex': int((~keep).sum()),
        'rejected_share': round(float((~keep).sum()) / max(total, 1), 4),
    }
    write_json(report, root / 'topic' / 'report.json')
    print(f'{args.platform} {args.event}: kept {report["kept"]}/{total} '
          f'(slur 1/1 {report["kept_slur_1_1"]}, regex {report["kept_regex_only"]}), '
          f'rejected {report["rejected_by_regex"]}')



if __name__ == '__main__':
    main()
