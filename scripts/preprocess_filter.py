"""Step 1: drop emoji-only, link-only, too short, non-Polish and duplicate texts for one event.

    python scripts/preprocess_filter.py --platform bluesky --event 2024-04-10_Pakt_Azyl_PE

Reads  data/raw/<platform>/<event>/{posts,comments}.csv
Writes data/interim/<platform>/<event>/filtered/{posts,comments,excluded_posts,excluded_comments}.csv
       + filter_report.json
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.preprocessing.filters import split_frame
from src.preprocessing.io import INTERIM_ROOT, RAW_ROOT, SOURCES, load_params, read_csv, write_csv, write_json
from src.preprocessing.lang import build_detector


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--platform', required=True)
    ap.add_argument('--event', required=True)
    args = ap.parse_args()

    cfg = load_params('preprocess')['filter']
    src = RAW_ROOT / args.platform / args.event
    out = INTERIM_ROOT / args.platform / args.event / 'filtered'
    detector = build_detector(cfg['languages'])

    report = {'event': args.event, 'platform': args.platform, 'params': cfg}
    for name in SOURCES:
        df = read_csv(src / f'{name}.csv')
        kept, excluded = split_frame(df, cfg, detector)
        write_csv(kept, out / f'{name}.csv')
        write_csv(excluded, out / f'excluded_{name}.csv')
        report[name] = {
            'input': len(df),
            'kept': len(kept),
            'dropped': excluded['drop_reason'].value_counts().to_dict(),
        }
        print(f'{args.event} {name}: {len(kept)}/{len(df)} kept', report[name]['dropped'])

    write_json(report, out / 'filter_report.json')


if __name__ == '__main__':
    main()
