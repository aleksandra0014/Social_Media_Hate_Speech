"""Split the Wykop export into event folders with the same layout and window rules as bluesky.py.
    python scripts/wykop.py events.json --source data/external/wykop --out data/raw/wykop
"""
import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml

TZ = 'Europe/Warsaw'
PARAMS_FILE = Path('params.yaml')
DAYS_BEFORE, DAYS_AFTER, MATERIAL_MAX_AGE = 28, 28, 4

# same masks as bluesky.py
MASKS = [
    (re.compile(r'https?://\S+|www\.\S+'), '[link]'),
    (re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+'), '[email]'),
    (re.compile(r'(?<![\w@])@[A-Za-z0-9](?:[\w-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[\w-]*[A-Za-z0-9])?)*'),
     '@[user]'),
    (re.compile(r'(?<!\d)\+?\d[\d \-]{7,}\d(?!\d)'), '[phone]'),
]

# bluesky.py columns first, Wykop-only ones at the end
COMMENT_FIELDS = [
    'comment_id', 'platform', 'event', 'relative_day', 'created_date', 'created_at',
    'material_age_days', 'thread_id', 'post_id', 'reply_to', 'depth',
    'author_id', 'is_material_author', 'text', 'langs',
    'likes', 'replies', 'reposts', 'quotes',
    'material_created_at', 'material_created_date', 'material_keywords', 'link',
    'lang_confidence', 'matched_slurs', 'ukraine_related', 'refugee_migrant_related', 'political',
]
EXCLUDED_FIELDS = ['exclusion_reason'] + COMMENT_FIELDS
POST_FIELDS = [
    'post_id', 'platform', 'event', 'relative_day', 'created_date', 'created_at',
    'keywords', 'text_keywords', 'search_queries', 'is_reply', 'author_id', 'text', 'langs',
    'likes', 'replies', 'reposts', 'quotes',
    'comments_in_thread', 'comments_in_rule', 'link',
    'item_type', 'title', 'tags', 'matched_slurs', 'ukraine_related', 'refugee_migrant_related', 'political',
    'comments_status',
]
DAILY_FIELDS = ['event', 'relative_day', 'date', 'phase',
                'materials_published', 'comments', 'unique_authors', 'median_likes']
COMMENTS_STATUS = {'0': 'not_fetched', '1': 'partial', '2': 'partial', '3': 'complete'}


def mask_text(text):
    for pattern, replacement in MASKS:
        text = pattern.sub(replacement, text)
    return text


def read_csv(path, **kw):
    return pd.read_csv(path, encoding='utf-8-sig', dtype=str, keep_default_na=False, **kw)


def write_csv(df, path, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.reindex(columns=fields).to_csv(path, index=False, encoding='utf-8-sig')


def utc(series):
    # the collector stores 'YYYY-MM-DD HH:MM:SS' in UTC
    return pd.to_datetime(series, utc=True, errors='coerce')


def iso(series):
    return series.dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def load_items(source):
    it = read_csv(source / 'items.csv')
    it['_created'] = utc(it['created_at'])
    it['_local_date'] = it['_created'].dt.tz_convert(TZ).dt.date
    it['text'] = (it['title'].where(it['title'] == '', it['title'] + '\n\n') + it['body']).map(mask_text)
    it['title'] = it['title'].map(mask_text)
    it['link'] = it['source_url']
    return it


def load_comments(source, item_ids):
    cols = {'comment_id', 'item_id', 'parent_comment_id', 'created_at', 'body', 'author_hash', 'votes', 'lang',
            'lang_confidence', 'matched_slurs', 'ukraine_related', 'refugee_migrant_related', 'political',
            'reply_count'}
    parts = [c[c['item_id'].isin(item_ids)]
             for c in read_csv(source / 'comments.csv', usecols=lambda c: c in cols, chunksize=200_000)]
    c = pd.concat(parts, ignore_index=True)
    c['_created'] = utc(c['created_at'])
    c['text'] = c['body'].map(mask_text)
    return c


def build_event(name, day, items, comments, out_root, data_until):
    day_zero = pd.Timestamp(day).tz_localize(TZ)
    analysis_start = day_zero - timedelta(days=DAYS_BEFORE)
    analysis_end = day_zero + timedelta(days=DAYS_AFTER + 1)          # exclusive
    material_start = analysis_start - timedelta(days=MATERIAL_MAX_AGE)
    slug = re.sub(r'[^\w-]+', '_', name).strip('_') or 'event'
    out = out_root / f'{day}_{slug}'

    posts = items[(items['_created'] >= material_start) & (items['_created'] < analysis_end)].copy()
    posts['post_id'] = posts['item_id']
    posts['platform'], posts['event'] = 'wykop', name
    posts['relative_day'] = (pd.to_datetime(posts['_local_date']) - pd.Timestamp(day)).dt.days
    posts['created_date'] = posts['_local_date'].astype(str)
    posts['created_at'] = iso(posts['_created'])
    posts['keywords'] = posts['qualified_by']
    posts['text_keywords'] = posts['matched_keywords']
    posts['search_queries'] = posts['first_source']
    posts['is_reply'] = False
    posts['author_id'] = posts['author_hash']
    posts['langs'] = 'pl'
    posts['likes'], posts['replies'] = posts['votes'], posts['comment_count']
    posts['reposts'] = posts['quotes'] = ''

    c = comments[comments['item_id'].isin(posts['item_id'])].merge(
        posts[['item_id', '_created', 'created_at', 'created_date', 'keywords', 'author_hash']]
        .rename(columns={'_created': '_m_created', 'created_at': 'material_created_at',
                         'created_date': 'material_created_date', 'keywords': 'material_keywords',
                         'author_hash': '_m_author'}),
        on='item_id')
    age = (c['_created'] - c['_m_created']).dt.total_seconds() / 86400
    local_date = c['_created'].dt.tz_convert(TZ).dt.date
    c['relative_day'] = (pd.to_datetime(local_date) - pd.Timestamp(day)).dt.days
    c['created_date'] = local_date.astype(str)
    c['material_age_days'] = age.round(3)
    c['platform'], c['event'] = 'wykop', name
    c['thread_id'] = c['post_id'] = c['item_id']
    c['reply_to'] = c['parent_comment_id'].where(c['parent_comment_id'] != '', c['item_id'])
    c['depth'] = (c['parent_comment_id'] != '').map({True: 2, False: 1})
    c['author_id'] = c['author_hash']
    c['is_material_author'] = c['author_hash'] == c['_m_author']
    c['langs'] = c['lang']
    c['likes'], c['replies'] = c['votes'], c['reply_count']
    c['reposts'] = c['quotes'] = c['link'] = ''

    # same order of checks as bluesky.evaluate_comment
    reason = pd.Series('', index=c.index)
    reason[(c['lang'] != '') & (c['lang'] != 'pl')] = 'other_language'
    reason[~((c['_created'] >= analysis_start) & (c['_created'] < analysis_end))] = 'outside_analysis_window'
    reason[age > MATERIAL_MAX_AGE] = 'material_too_old'
    reason[age < 0] = 'comment_before_material'
    reason[c['_created'].isna() | c['_m_created'].isna()] = 'missing_date'
    c['exclusion_reason'] = reason
    included, excluded = c[reason == ''].copy(), c[reason != ''].copy()
    included = included.sort_values('_created', kind='stable')

    per_post = c.groupby('item_id').size()
    per_post_rule = included.groupby('item_id').size()
    posts['comments_in_thread'] = posts['item_id'].map(per_post).fillna(0).astype(int)
    posts['comments_in_rule'] = posts['item_id'].map(per_post_rule).fillna(0).astype(int)
    posts = posts.sort_values('_created', kind='stable')

    daily = []
    for d in range(-DAYS_BEFORE, DAYS_AFTER + 1):
        date_s = (pd.Timestamp(day) + timedelta(days=d)).date().isoformat()
        dc = included[included['relative_day'] == d]
        likes = pd.to_numeric(dc['likes'], errors='coerce').dropna()
        daily.append({'event': name, 'relative_day': d, 'date': date_s,
                      'phase': 'before' if d < 0 else ('day_0' if d == 0 else 'after'),
                      'materials_published': int((posts['created_date'] == date_s).sum()),
                      'comments': len(dc), 'unique_authors': dc['author_id'].nunique(),
                      'median_likes': likes.median() if len(likes) else ''})
    daily = pd.DataFrame(daily)

    write_csv(posts, out / 'posts.csv', POST_FIELDS)
    write_csv(included, out / 'comments.csv', COMMENT_FIELDS)
    write_csv(excluded, out / 'excluded.csv', EXCLUDED_FIELDS)
    write_csv(daily, out / 'daily.csv', DAILY_FIELDS)

    status = posts['comments_status'].map(COMMENTS_STATUS).value_counts().to_dict()
    report = {
        'built_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'event': name, 'event_date': str(day), 'output_folder': str(out),
        'window_complete': bool(analysis_end <= data_until), 'data_until': data_until.isoformat(),
        'timezone': TZ,
        'analysis_window': [analysis_start.date().isoformat(), (analysis_end - timedelta(days=1)).date().isoformat()],
        'material_window': [material_start.date().isoformat(), (analysis_end - timedelta(days=1)).date().isoformat()],
        'material_max_age_days': MATERIAL_MAX_AGE, 'days_before': DAYS_BEFORE, 'days_after': DAYS_AFTER,
        'language': 'pl', 'polish_comments_only': True,
        'materials': len(posts),
        'materials_by_type': posts['item_type'].value_counts().to_dict(),
        'materials_by_qualification': posts['qualified_by'].value_counts().to_dict(),
        'materials_comments_status': status,
        'comments_in_rule': len(included), 'comments_excluded': len(excluded),
        'exclusion_reasons': excluded['exclusion_reason'].value_counts().to_dict(),
        'authors': int(included['author_id'].nunique()),
        'comments_per_day': {'min': int(daily['comments'].min()), 'median': float(daily['comments'].median()),
                             'max': int(daily['comments'].max()),
                             'days_below_50': int((daily['comments'] < 50).sum())},
    }
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{out.name}: {len(posts)} materials, {len(included)} comments in rule, {len(excluded)} excluded '
          f'{report["exclusion_reasons"]}{"" if report["window_complete"] else "  (window not complete)"}')


def main():
    global DAYS_BEFORE, DAYS_AFTER, MATERIAL_MAX_AGE
    ap = argparse.ArgumentParser(description='Build per-event Wykop folders from the collector export.')
    ap.add_argument('events', help='JSON file {"name": "YYYY-MM-DD", ...}')
    ap.add_argument('--source', default='data/external/wykop', help='folder with items.csv and comments.csv')
    ap.add_argument('--out', default='data/raw/wykop')
    args = ap.parse_args()

    if PARAMS_FILE.exists():
        params = (yaml.safe_load(PARAMS_FILE.read_text(encoding='utf-8')) or {}).get('wykop', {})
        DAYS_BEFORE = params.get('days_before', DAYS_BEFORE)
        DAYS_AFTER = params.get('days_after', DAYS_AFTER)
        MATERIAL_MAX_AGE = params.get('material_max_age', MATERIAL_MAX_AGE)

    events = json.loads(Path(args.events).read_text(encoding='utf-8-sig'))
    events = sorted(((n, pd.Timestamp(d).date()) for n, d in events.items()), key=lambda e: e[1])
    source, out_root = Path(args.source), Path(args.out)

    items = load_items(source)
    comments = load_comments(source, set(items['item_id']))
    data_until = comments['_created'].max()
    print(f'Source: {len(items):,} items, {len(comments):,} comments, data until {data_until:%Y-%m-%d %H:%M} UTC')
    for name, day in events:
        build_event(name, day, items, comments, out_root, data_until)


if __name__ == '__main__':
    main()
