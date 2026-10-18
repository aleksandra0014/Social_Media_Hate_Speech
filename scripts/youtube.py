"""Collect YouTube videos and comments around events - same layout and window rules as bluesky.py / wykop.py.

    python scripts/youtube.py events.json --out data/raw/youtube
    python scripts/youtube.py events.json --channels tvp_info,TVN24

API keys go to .env.local (next to this script):  YT_API_KEY=...  and optionally YT_API_KEY_2=..., YT_API_KEY_3=...
(or one line YT_API_KEYS=key1,key2,key3). When a key's daily quota runs out, the next one is used.

Materials = videos published on the channels listed in CHANNELS (no keyword search: the channel is the
selection). Comments = top-level comments AND replies under those videos. Quota: the script uses the
channel "uploads" playlist (1 unit/page) instead of search.list (100 units/call), commentThreads.list
and comments.list cost 1 unit per page. The default daily quota is 10 000 units; when it runs out the
script stops and a re-run continues with the events that have no report.json yet.
"""
import argparse
import csv
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yaml

try:
    from lingua import LanguageDetectorBuilder
    DETECTOR = LanguageDetectorBuilder.from_all_languages().build()   # models load lazily on first use
except ImportError:
    DETECTOR = None

OUTPUT_ROOT = Path('data/raw/youtube')
PARAMS_FILE = Path('params.yaml')
EVENTS_FILE = Path(__file__).with_name('events.json')
SKIP_DONE = True                   # skip events whose folder already contains report.json

DAYS_BEFORE = 28                   # baseline window
DAYS_AFTER = 28                    # event window
MATERIAL_MAX_AGE = 4               # comment counted when the video is 0..4 days old
TIMEZONE = 'Europe/Warsaw'         # day boundaries in local time

# name -> channel id (UC...). Comment/uncomment to choose; --channels filters by name.
CHANNELS = {
    'Onet': 'UC_vMDcmkuEvw0N-gaP35wTA',
    'Kanal_Zero': 'UClhEl4bMD8_escGCCTmRAYg',
    'TVN24': 'UCIPUn4-CnMxCkrjyimHCmCw',
    'Orb': 'UC_FMh6Rv1ooISal3xM98Ixw',
    'Telewizja_Republika': 'UCc282c_TN8xIba_Z6GaDnQw',
    'polsatnews.pl': 'UCkNOjcTcgLaNL0-XNoe4gtw',
    'tvp_info': 'UCzQZbOb86WvhOPoR7jgAfsA',
    'Praktycznieopieniadzach': 'UCFBH3Bdhgh3_cCToEQsUp6Q',
    'SlawomirMentzen': 'UCkH8DpG5uKx0YsGCFWmOQcA',
    'Razem': 'UCtDlwTjFZkoKaSocrmtVv2A',
}

POLISH_COMMENTS_ONLY = True        # needs lingua-language-detector; texts shorter than MIN_LANG_CHARS are kept (lang unknown)
MIN_LANG_CHARS = 25
INCLUDE_LINKS = False              # True adds a link to each comment (reveals the author) - testing only
# ====================================================

BASE = 'https://www.googleapis.com/youtube/v3'
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'YouTubeResearchPilot/1.0'})
TZ = ZoneInfo(TIMEZONE)
API_KEYS = []                      # filled by load_key(); the script moves to the next one when a quota runs out
KEY_INDEX = 0
COMMENT_CACHE = {}                 # video_id -> flat list of comments (a video can fall into two events)


class QuotaExceeded(Exception):
    pass


class CommentsDisabled(Exception):
    pass


# ---------- events and time windows ----------

@dataclass(frozen=True)
class Event:
    name: str
    date: date
    output_dir: Path
    day_zero: datetime
    analysis_start: datetime
    analysis_end: datetime         # exclusive
    material_start: datetime

    @property
    def last_day(self):
        return (self.analysis_end - timedelta(days=1)).date()


def make_event(name, day):
    day_zero = datetime(day.year, day.month, day.day, tzinfo=TZ)
    analysis_start = day_zero - timedelta(days=DAYS_BEFORE)
    analysis_end = day_zero + timedelta(days=DAYS_AFTER + 1)
    slug = re.sub(r'[^\w-]+', '_', name).strip('_') or 'event'
    return Event(name=name, date=day, output_dir=OUTPUT_ROOT / f'{day.isoformat()}_{slug}',
                 day_zero=day_zero, analysis_start=analysis_start, analysis_end=analysis_end,
                 material_start=analysis_start - timedelta(days=MATERIAL_MAX_AGE))


def load_events(path=None):
    path = Path(path) if path else EVENTS_FILE
    if not path.exists():
        raise SystemExit(f'Events file not found: {path}\nCreate it, e.g.: {{"test_event": "2026-07-31"}}')
    try:
        raw = json.loads(path.read_text(encoding='utf-8-sig'))
    except json.JSONDecodeError as e:
        raise SystemExit(f'{path} is not valid JSON: {e}')
    if not isinstance(raw, dict) or not raw:
        raise SystemExit(f'{path} must be a non-empty object: {{"name": "YYYY-MM-DD", ...}}')
    events, folders = [], set()
    for name, value in raw.items():
        name = str(name).strip()
        try:
            day = date.fromisoformat(str(value).strip())
        except ValueError:
            raise SystemExit(f'Event {name!r}: bad date {value!r} (expected YYYY-MM-DD)')
        ev = make_event(name, day)
        if ev.output_dir in folders:
            raise SystemExit(f'Two events map to the same folder: {ev.output_dir}')
        folders.add(ev.output_dir)
        events.append(ev)
    return sorted(events, key=lambda e: e.date)


def parse_date(text):
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def local_day(dt):
    return dt.astimezone(TZ).date()


# ---------- auth and API ----------

def load_env(path=Path(__file__).with_name('.env.local')):
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def load_key():
    """Keys from .env.local: YT_API_KEYS=key1,key2,... and/or YT_API_KEY, YT_API_KEY_2, YT_API_KEY_3, ..."""
    global API_KEYS
    load_env()
    keys = [k.strip() for k in os.environ.get('YT_API_KEYS', '').split(',')]
    keys.append(os.environ.get('YT_API_KEY', ''))
    keys += [os.environ.get(f'YT_API_KEY_{n}', '') for n in range(2, 21)]
    API_KEYS = list(dict.fromkeys(k.strip() for k in keys if k.strip()))   # unique, order kept
    if not API_KEYS:
        raise SystemExit('Set YT_API_KEY (or YT_API_KEYS=key1,key2 / YT_API_KEY_2...) in .env.local '
                         '(never put keys in the source code).')
    print(f'API keys loaded: {len(API_KEYS)}')


def error_reason(r):
    try:
        return r.json()['error']['errors'][0]['reason']
    except (ValueError, KeyError, IndexError, TypeError):
        return ''


def api_get(method, params):
    """GET with retries. When the current key's daily quota is used up, switches to the next key
    and repeats the same request; raises QuotaExceeded only when every key is exhausted."""
    global KEY_INDEX
    attempt = 0
    while True:
        time.sleep(0.1)
        try:
            r = SESSION.get(f'{BASE}/{method}', params={**params, 'key': API_KEYS[KEY_INDEX]}, timeout=30)
        except (requests.ConnectionError, requests.Timeout):
            attempt += 1
            if attempt >= 4:
                raise
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 200:
            return r.json()
        reason = error_reason(r)
        if r.status_code == 403 and reason in ('quotaExceeded', 'dailyLimitExceeded'):
            if KEY_INDEX + 1 < len(API_KEYS):
                KEY_INDEX += 1
                print(f'  Quota of key {KEY_INDEX} exhausted - switching to key {KEY_INDEX + 1}/{len(API_KEYS)}',
                      flush=True)
                continue                      # same request, next key
            raise QuotaExceeded(f'{reason} (all {len(API_KEYS)} keys used up)')
        if reason == 'commentsDisabled':
            raise CommentsDisabled(reason)
        if r.status_code == 429 or reason == 'rateLimitExceeded' or 500 <= r.status_code < 600:
            attempt += 1
            if attempt >= 4:
                r.raise_for_status()
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()


# ---------- pseudonymisation ----------

class Pseudonyms:
    """Maps YouTube identifiers to sequential ids: P00001, K000001, A00001."""

    def __init__(self):
        self.mapping = {}
        self.counters = {}

    def _id(self, key, prefix, digits):
        if key not in self.mapping:
            self.counters[prefix] = self.counters.get(prefix, 0) + 1
            self.mapping[key] = f'{prefix}{self.counters[prefix]:0{digits}d}'
        return self.mapping[key]

    def post(self, video_id):
        return self._id(('v', video_id), 'P', 5)

    def comment(self, comment_id):
        return self._id(('c', comment_id), 'K', 6)

    def author(self, channel_id):
        return self._id(('a', channel_id), 'A', 5) if channel_id else ''


MASKS = [
    (re.compile(r'https?://\S+|www\.\S+'), '[link]'),
    (re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+'), '[email]'),
    (re.compile(r'(?<![\w@])@[A-Za-z0-9](?:[\w-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[\w-]*[A-Za-z0-9])?)*'),
     '@[user]'),
    (re.compile(r'(?<!\d)\+?\d[\d \-]{7,}\d(?!\d)'), '[phone]'),
]


def mask_text(text):
    for pattern, replacement in MASKS:
        text = pattern.sub(replacement, text)
    return text


def detect_lang(text):
    clean = re.sub(r'\[(?:link|email|phone)\]|@\[user\]', '', text).strip()
    if DETECTOR is None or len(clean) < MIN_LANG_CHARS:
        return ''
    lang = DETECTOR.detect_language_of(clean)          # None when lingua cannot decide
    return lang.iso_code_639_1.name.lower() if lang else ''


# ---------- fetching ----------

def channel_uploads(channel_name, channel_id, oldest):
    """All uploads of a channel newer than `oldest`, via the uploads playlist (UC... -> UU...)."""
    playlist = 'UU' + channel_id[2:]
    videos, token = [], None
    while True:
        params = {'part': 'contentDetails', 'playlistId': playlist, 'maxResults': 50}
        if token:
            params['pageToken'] = token
        data = api_get('playlistItems', params)
        page_dates = []
        for it in data.get('items', []):
            published = parse_date(it['contentDetails'].get('videoPublishedAt'))
            if not published:
                continue
            page_dates.append(published)
            videos.append({'video_id': it['contentDetails']['videoId'], 'published': published,
                           'channel_name': channel_name, 'channel_id': channel_id})
        token = data.get('nextPageToken')
        # the playlist is newest-first; stop once a whole page is older than the earliest window
        if not token or (page_dates and max(page_dates) < oldest - timedelta(days=2)):
            break
    return videos


def video_details(video_ids):
    """snippet + statistics for up to many videos (50 per request)."""
    out = {}
    ids = list(video_ids)
    for i in range(0, len(ids), 50):
        data = api_get('videos', {'part': 'snippet,statistics', 'id': ','.join(ids[i:i + 50])})
        for item in data.get('items', []):
            out[item['id']] = item
    return out


def flat_comment(c, parent_id, depth, reply_count=0):
    s = c['snippet']
    return {'id': c['id'], 'parent': parent_id, 'depth': depth,
            'author': s.get('authorChannelId', {}).get('value', ''),
            'text': s.get('textDisplay', ''), 'created': s.get('publishedAt', ''),
            'likes': s.get('likeCount', 0), 'replies': reply_count}


def fetch_replies(parent_id):
    out, token = [], None
    while True:
        params = {'part': 'snippet', 'parentId': parent_id, 'maxResults': 100, 'textFormat': 'plainText'}
        if token:
            params['pageToken'] = token
        data = api_get('comments', params)
        out.extend(data.get('items', []))
        token = data.get('nextPageToken')
        if not token:
            return out


def fetch_comments(video_id):
    """Top-level comments plus all replies under one video, flattened (depth 1 / 2)."""
    if video_id in COMMENT_CACHE:
        return COMMENT_CACHE[video_id]
    out, token = [], None
    while True:
        params = {'part': 'snippet,replies', 'videoId': video_id, 'maxResults': 100,
                  'textFormat': 'plainText', 'order': 'time'}
        if token:
            params['pageToken'] = token
        data = api_get('commentThreads', params)
        for thread in data.get('items', []):
            top = thread['snippet']['topLevelComment']
            total = thread['snippet'].get('totalReplyCount', 0)
            out.append(flat_comment(top, '', 1, total))
            inline = thread.get('replies', {}).get('comments', [])
            replies = inline if len(inline) >= total else fetch_replies(top['id'])
            out.extend(flat_comment(r, top['id'], 2) for r in replies)
        token = data.get('nextPageToken')
        if not token:
            break
    COMMENT_CACHE[video_id] = out
    return out


# ---------- sampling rule ----------

def evaluate_comment(created, material_created, lang, ev):
    """Returns (in_rule, exclusion_reason, material_age_days, relative_day)."""
    if created is None or material_created is None:
        return False, 'missing_date', '', ''
    age = (created - material_created).total_seconds() / 86400
    relative_day = (local_day(created) - ev.date).days
    if age < 0:
        return False, 'comment_before_material', round(age, 3), relative_day
    if age > MATERIAL_MAX_AGE:
        return False, 'material_too_old', round(age, 3), relative_day
    if not (ev.analysis_start <= created < ev.analysis_end):
        return False, 'outside_analysis_window', round(age, 3), relative_day
    if POLISH_COMMENTS_ONLY and lang not in ('', 'pl'):
        return False, 'other_language', round(age, 3), relative_day
    return True, '', round(age, 3), relative_day


# ---------- writing output ----------

COMMENT_FIELDS = [
    'comment_id', 'platform', 'event', 'relative_day', 'created_date', 'created_at',
    'material_age_days', 'thread_id', 'post_id', 'reply_to', 'depth',
    'author_id', 'is_material_author', 'text', 'langs',
    'likes', 'replies', 'reposts', 'quotes',
    'material_created_at', 'material_created_date', 'material_keywords', 'link',
]
EXCLUDED_FIELDS = ['exclusion_reason'] + COMMENT_FIELDS
POST_FIELDS = [
    'post_id', 'platform', 'event', 'relative_day', 'created_date', 'created_at',
    'keywords', 'text_keywords', 'search_queries', 'is_reply', 'author_id', 'text', 'langs',
    'likes', 'replies', 'reposts', 'quotes',
    'comments_in_thread', 'comments_in_rule', 'link',
    'item_type', 'title', 'channel_name', 'tags',
]
DAILY_FIELDS = ['event', 'relative_day', 'date', 'phase',
                'materials_published', 'comments', 'unique_authors', 'median_likes']


def write_csv(folder, name, fields, rows):
    with (folder / name).open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def median(values):
    if not values:
        return ''
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def daily_aggregate(ev, posts, comments):
    rows = []
    for d in range(-DAYS_BEFORE, DAYS_AFTER + 1):
        day = (ev.day_zero + timedelta(days=d)).date()
        day_comments = [c for c in comments if c['relative_day'] == d]
        rows.append({
            'event': ev.name, 'relative_day': d, 'date': day.isoformat(),
            'phase': 'before' if d < 0 else ('day_0' if d == 0 else 'after'),
            'materials_published': sum(p['created_date'] == day.isoformat() for p in posts),
            'comments': len(day_comments),
            'unique_authors': len({c['author_id'] for c in day_comments}),
            'median_likes': median([c['likes'] for c in day_comments]),
        })
    return rows


def write_all(ev, posts, comments, excluded):
    write_csv(ev.output_dir, 'comments.csv', COMMENT_FIELDS, comments)
    write_csv(ev.output_dir, 'posts.csv', POST_FIELDS, posts)
    write_csv(ev.output_dir, 'excluded.csv', EXCLUDED_FIELDS, excluded)
    write_csv(ev.output_dir, 'daily.csv', DAILY_FIELDS, daily_aggregate(ev, posts, comments))


# ---------- one event ----------

def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def run_event(ev, uploads):
    window_complete = ev.analysis_end <= datetime.now(timezone.utc)
    print(f'Event: {ev.name} (day 0 = {ev.date})')
    print(f'Output folder: {ev.output_dir.resolve()}')
    print(f'Comment analysis window: {ev.analysis_start.date()} .. {ev.last_day}')
    print(f'Material fetch window:   {ev.material_start.date()} .. {ev.last_day} '
          f'({MATERIAL_MAX_AGE}-day run-up)')
    print(f'Rule: a comment counts when its video is 0..{MATERIAL_MAX_AGE} days old')
    if not window_complete:
        print('WARNING: the analysis window has not ended yet - data will be incomplete.')
    print()

    ev.output_dir.mkdir(parents=True, exist_ok=True)
    ps = Pseudonyms()
    errors = []

    # 1. Materials = videos in the material window
    candidates = [v for v in uploads if ev.material_start <= v['published'] < ev.analysis_end]
    details = video_details([v['video_id'] for v in candidates])
    posts, video_by_post = [], {}
    for v in candidates:
        item = details.get(v['video_id'])
        if not item:
            errors.append({'stage': 'video', 'video_id': v['video_id'], 'error': 'no details (private/deleted)'})
            continue
        sn, st = item['snippet'], item.get('statistics', {})
        title = mask_text(sn.get('title', ''))
        description = mask_text(sn.get('description', ''))
        post_id = ps.post(v['video_id'])
        video_by_post[post_id] = v
        posts.append({
            'post_id': post_id, 'platform': 'youtube', 'event': ev.name,
            'relative_day': (local_day(v['published']) - ev.date).days,
            'created_date': local_day(v['published']).isoformat(),
            'created_at': sn.get('publishedAt', ''),
            'keywords': v['channel_name'], 'text_keywords': '', 'search_queries': 'channel_uploads',
            'is_reply': False, 'author_id': ps.author(v['channel_id']),
            'text': f'{title}\n\n{description}' if description else title,
            'langs': sn.get('defaultAudioLanguage') or sn.get('defaultLanguage') or '',
            'likes': to_int(st.get('likeCount')), 'replies': to_int(st.get('commentCount')),
            'reposts': '', 'quotes': '',
            'comments_in_thread': 0, 'comments_in_rule': 0,
            'link': f'https://www.youtube.com/watch?v={v["video_id"]}',
            'item_type': 'video', 'title': title, 'channel_name': v['channel_name'],
            'tags': '|'.join(sn.get('tags', [])),
            '_created': v['published'],
        })
    posts.sort(key=lambda p: p['_created'])
    print(f'Found {len(posts)} videos.', flush=True)

    # 2. Comments under the videos, filtered by the sampling rule
    comments, excluded, threads = [], [], []
    to_fetch = [p for p in posts if p['replies'] > 0]
    print(f'Videos with comments: {len(to_fetch)}\n', flush=True)
    for i, p in enumerate(to_fetch, 1):
        if i % 10 == 0 or i == 1:
            print(f'Videos {i}/{len(to_fetch)}', flush=True)
        try:
            raw = fetch_comments(video_by_post[p['post_id']]['video_id'])
        except CommentsDisabled:
            threads.append({'post_id': p['post_id'], 'status': 'comments_disabled'})
            continue
        except requests.RequestException as e:
            errors.append({'stage': 'comments', 'post_id': p['post_id'], 'error': str(e)})
            continue
        ids = {c['id']: ps.comment(c['id']) for c in raw}
        n_in = 0
        for c in raw:
            created = parse_date(c['created'])
            text = mask_text(c['text'])
            lang = detect_lang(text)
            in_rule, reason, age, relative_day = evaluate_comment(created, p['_created'], lang, ev)
            author = ps.author(c['author'])
            row = {
                'comment_id': ids[c['id']], 'platform': 'youtube', 'event': ev.name,
                'relative_day': relative_day,
                'created_date': local_day(created).isoformat() if created else '',
                'created_at': c['created'], 'material_age_days': age,
                'thread_id': p['post_id'], 'post_id': p['post_id'],
                'reply_to': ids.get(c['parent'], p['post_id']) if c['parent'] else p['post_id'],
                'depth': c['depth'], 'author_id': author,
                'is_material_author': bool(author) and author == p['author_id'],
                'text': text, 'langs': lang,
                'likes': c['likes'], 'replies': c['replies'], 'reposts': '', 'quotes': '',
                'material_created_at': p['created_at'], 'material_created_date': p['created_date'],
                'material_keywords': p['keywords'],
                'link': (f'{p["link"]}&lc={c["id"]}' if INCLUDE_LINKS else ''),
                '_created': created,
            }
            if in_rule:
                comments.append(row)
                n_in += 1
            else:
                excluded.append({**row, 'exclusion_reason': reason})
        p['comments_in_thread'] = len(raw)
        p['comments_in_rule'] = n_in
        threads.append({'post_id': p['post_id'], 'reported_comments': p['replies'],
                        'fetched_comments': len(raw), 'in_rule': n_in})
        if i % 25 == 0:
            write_all(ev, posts, comments, excluded)  # partial save
    comments.sort(key=lambda c: c['_created'])

    # 3. Write output and report
    write_all(ev, posts, comments, excluded)
    daily = daily_aggregate(ev, posts, comments)
    per_day = [row['comments'] for row in daily]
    reasons = {}
    for c in excluded:
        reasons[c['exclusion_reason']] = reasons.get(c['exclusion_reason'], 0) + 1

    report = {
        'collected_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'event': ev.name, 'event_date': ev.date.isoformat(), 'output_folder': str(ev.output_dir),
        'window_complete': window_complete, 'timezone': TIMEZONE,
        'analysis_window': [ev.analysis_start.date().isoformat(), ev.last_day.isoformat()],
        'material_window': [ev.material_start.date().isoformat(), ev.last_day.isoformat()],
        'material_max_age_days': MATERIAL_MAX_AGE, 'days_before': DAYS_BEFORE, 'days_after': DAYS_AFTER,
        'channels': {n: i for n, i in CHANNELS.items()},
        'language': 'pl', 'polish_comments_only': POLISH_COMMENTS_ONLY,
        'language_detection': 'lingua' if DETECTOR else 'unavailable (no language filter applied)',
        'links_included': INCLUDE_LINKS,
        'materials': len(posts),
        'materials_per_channel': {n: sum(p['channel_name'] == n for p in posts) for n in CHANNELS},
        'comments_in_rule': len(comments), 'comments_excluded': len(excluded),
        'exclusion_reasons': reasons,
        'authors': ps.counters.get('A', 0),
        'comments_per_day': {'min': min(per_day), 'median': median(per_day), 'max': max(per_day),
                             'days_below_50': sum(n < 50 for n in per_day)},
        'threads': threads, 'errors': errors,
        'notes': [
            'Pseudonyms are assigned afresh for every event and every run - data from two '
            'events or two runs cannot be joined on author_id.',
            'The sampling rule is identical for every day of the window, baseline days included.',
            'Materials are all public uploads of the listed channels (no keyword search); '
            'keywords = channel name. Live streams and premieres appear with their start date.',
            'Comments = top-level comments and replies (depth 1 / 2). YouTube hides held-for-review '
            'and deleted comments, so fetched_comments can be below reported_comments.',
            'YouTube gives no language field: Polish filtering uses lingua on texts of at '
            f'least {MIN_LANG_CHARS} characters; shorter texts have an empty langs and are kept.',
            'Comments disabled under a video are listed in threads with status comments_disabled.',
        ],
    }
    # report.json is written last, so its presence marks the event as finished.
    (ev.output_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                               encoding='utf-8')
    print(f'\nDone. Videos: {len(posts)}, comments in rule: {len(comments)}, excluded: {len(excluded)}')
    print(f'Comments per day - median: {median(per_day)}, min: {min(per_day)}, '
          f'max: {max(per_day)}, days below 50: {sum(n < 50 for n in per_day)}/{len(per_day)}')
    if errors:
        print(f'Errors: {len(errors)} - see report.json')


# ---------- main ----------

def main():
    global OUTPUT_ROOT, DAYS_BEFORE, DAYS_AFTER, MATERIAL_MAX_AGE, CHANNELS

    parser = argparse.ArgumentParser(description='Collect YouTube videos and comments around events.')
    parser.add_argument('events', nargs='?', help='JSON file {"name": "YYYY-MM-DD", ...} '
                                                  f'(default: {EVENTS_FILE.name})')
    parser.add_argument('--out', default=str(OUTPUT_ROOT), help=f'output folder (default: {OUTPUT_ROOT})')
    parser.add_argument('--channels', help='comma-separated channel names from CHANNELS (default: all)')
    args = parser.parse_args()

    OUTPUT_ROOT = Path(args.out)
    if PARAMS_FILE.exists():
        params = (yaml.safe_load(PARAMS_FILE.read_text(encoding='utf-8')) or {}).get('youtube', {})
        DAYS_BEFORE = params.get('days_before', DAYS_BEFORE)
        DAYS_AFTER = params.get('days_after', DAYS_AFTER)
        MATERIAL_MAX_AGE = params.get('material_max_age', MATERIAL_MAX_AGE)

    if args.channels:
        wanted = [c.strip() for c in args.channels.split(',') if c.strip()]
        unknown = [c for c in wanted if c not in CHANNELS]
        if unknown:
            raise SystemExit(f'Unknown channels: {unknown}. Available: {list(CHANNELS)}')
        CHANNELS = {c: CHANNELS[c] for c in wanted}
    if not CHANNELS:
        raise SystemExit('CHANNELS is empty - uncomment at least one channel.')
    if POLISH_COMMENTS_ONLY and DETECTOR is None:
        print('WARNING: lingua is not installed (pip install lingua-language-detector) - '
              'no language filter will be applied.')

    events = load_events(args.events)
    print(f'Events to process: {len(events)}; channels: {", ".join(CHANNELS)}')
    for ev in events:
        print(f'  {ev.date}  {ev.name}  ->  {ev.output_dir}')

    load_key()
    todo = [ev for ev in events if not (SKIP_DONE and (ev.output_dir / 'report.json').exists())]
    failed, skipped = [], [ev.name for ev in events if ev not in todo]
    try:
        if todo:
            oldest = min(ev.material_start for ev in todo)
            uploads = []
            for name, channel_id in CHANNELS.items():
                found = channel_uploads(name, channel_id, oldest)
                print(f'Channel {name}: {len(found)} uploads since {oldest.date()}', flush=True)
                uploads.extend(found)
        for i, ev in enumerate(events, 1):
            print(f'\n===== [{i}/{len(events)}] {ev.name} ({ev.date}) =====')
            if ev.name in skipped:
                print('Already collected (report.json exists) - skipping.')
                continue
            try:
                run_event(ev, uploads)
            except QuotaExceeded:
                raise
            except Exception as e:  # one broken event should not stop the others
                print(f'FAILED: {e!r}')
                failed.append(ev.name)
    except QuotaExceeded as e:
        print(f'\nSTOPPED: YouTube API quota exhausted ({e}). Re-run tomorrow - finished events are skipped.')
        return

    print(f'\nAll done. Processed: {len(events) - len(failed) - len(skipped)}, '
          f'skipped: {len(skipped)}, failed: {len(failed)}')
    if failed:
        print('Failed events (re-run the script to retry them): ' + ', '.join(failed))


if __name__ == '__main__':
    main()
