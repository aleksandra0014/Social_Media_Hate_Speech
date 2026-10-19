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
import yaml
import requests

EVENTS_FILE = Path(__file__).with_name('events.json')
OUTPUT_ROOT = Path('data/raw/bluesky')
PARAMS_FILE = Path('params.yaml')
SKIP_DONE = True                   # skip events whose folder already contains report.json

DAYS_BEFORE = 28                   # baseline window
DAYS_AFTER = 28                    # event window
MATERIAL_MAX_AGE = 4               # comment counted when the post is 0..4 days old
TIMEZONE = 'Europe/Warsaw'         # day boundaries in local time

# HOW KEYWORDS WORK
# Bluesky search matches WHOLE WORDS: the query 'ukrain' finds only the word "ukrain",
# never "Ukraina", "Ukrainiec" or "Ukraińców". So every group below lists the inflected
# forms that are actually searched; the group label is what ends up in the 'keywords' column.
#  - Case does not matter.
#  - Forms in "double quotes" are exact phrases (all words, in this order).
#  - A label ending with * is a stem. With USE_WILDCARD = True the script sends the stem
#    itself (e.g. 'ukrain*') plus only those forms that do not start with it (e.g. 'Ukraińca').
#    Turn it on only if `python collect_bluesky.py --check-keywords` shows wildcards work.
#    A wildcard also catches unrelated words (socjal* -> socjalizm), so forms are more precise.
USE_WILDCARD = False

KEYWORD_GROUPS = {
    # --- migration ---
    'migrant*': ['migrant', 'migranta', 'migrantowi', 'migrantem', 'migrancie', 'migranci',
                 'migrantów', 'migrantom', 'migrantami', 'migrantach',
                 'migrantka', 'migrantki', 'migrantce', 'migrantkę', 'migrantką',
                 'migrantek', 'migrantkom', 'migrantkami', 'migrantkach'],
    'migracj*': ['migracja', 'migracji', 'migrację', 'migracją', 'migracje', 'migracjom',
                 'migracjami', 'migracjach',
                 'migracyjny', 'migracyjna', 'migracyjne', 'migracyjnej', 'migracyjnego',
                 'migracyjnych', 'migracyjnym', 'migracyjnymi', 'migracyjną'],
    'imigrant*': ['imigrant', 'imigranta', 'imigrantowi', 'imigrantem', 'imigrancie', 'imigranci',
                  'imigrantów', 'imigrantom', 'imigrantami', 'imigrantach',
                  'imigrantka', 'imigrantki', 'imigrantce', 'imigrantkę', 'imigrantką',
                  'imigrantek', 'imigrantkom', 'imigrantkami', 'imigrantkach'],
    'imigracj*': ['imigracja', 'imigracji', 'imigrację', 'imigracją', 'imigracje',
                  'imigracyjny', 'imigracyjna', 'imigracyjne', 'imigracyjnej', 'imigracyjnego',
                  'imigracyjnych', 'imigracyjnym', 'imigracyjną'],
    'nielegalna migracja': ['"nielegalna migracja"', '"nielegalnej migracji"',
                            '"nielegalną migrację"', '"nielegalną migracją"',
                            '"nielegalni migranci"', '"nielegalnych migrantów"',
                            '"nielegalnym migrantom"', '"nielegalnymi migrantami"'],
    'uchodźc*': ['uchodźca', 'uchodźcy', 'uchodźcę', 'uchodźcą', 'uchodźco', 'uchodźców',
                 'uchodźcom', 'uchodźcami', 'uchodźcach',
                 'uchodźczyni', 'uchodźczynie', 'uchodźczyń', 'uchodźczyniom',
                 'uchodźczy', 'uchodźcza', 'uchodźcze', 'uchodźczej', 'uchodźczego',
                 'uchodźczych', 'uchodźczym', 'uchodźczymi', 'uchodźczą'],
    'uchodźstw*': ['uchodźstwo', 'uchodźstwa', 'uchodźstwie', 'uchodźstwem', 'uchodźstwu'],
    'nachodźc*': ['nachodźca', 'nachodźcy', 'nachodźcę', 'nachodźcą', 'nachodźców',
                  'nachodźcom', 'nachodźcami', 'nachodźcach'],
    'azyl*': ['azyl', 'azylu', 'azylem', 'azylowi', 'azyle', 'azylów',
              'azylowy', 'azylowa', 'azylowe', 'azylowej', 'azylowego', 'azylowych',
              'azylowym', 'azylową',
              'azylant', 'azylanta', 'azylanci', 'azylantów', 'azylantom', 'azylantami',
              'azylantach', 'azylantka', 'azylantki'],
    'relokacj*': ['relokacja', 'relokacji', 'relokację', 'relokacją', 'relokacje',
                  'relokacyjny', 'relokacyjna', 'relokacyjne', 'relokacyjnej',
                  'relokacyjnego', 'relokacyjnych'],
    'deportacj*': ['deportacja', 'deportacji', 'deportację', 'deportacją', 'deportacje',
                   'deportacjom', 'deportacjami', 'deportacjach',
                   'deportować', 'deportuje', 'deportują', 'deportował', 'deportowała',
                   'deportowali', 'deportowano', 'deportowany', 'deportowana',
                   'deportowani', 'deportowanych'],
    'cudzoziem*': ['cudzoziemiec', 'cudzoziemca', 'cudzoziemcowi', 'cudzoziemcem',
                   'cudzoziemcu', 'cudzoziemcy', 'cudzoziemców', 'cudzoziemcom',
                   'cudzoziemcami', 'cudzoziemcach',
                   'cudzoziemka', 'cudzoziemki', 'cudzoziemce', 'cudzoziemkę',
                   'cudzoziemką', 'cudzoziemek', 'cudzoziemkom', 'cudzoziemkami'],
    'obcokrajow*': ['obcokrajowiec', 'obcokrajowca', 'obcokrajowcowi', 'obcokrajowcem',
                    'obcokrajowcu', 'obcokrajowcy', 'obcokrajowców', 'obcokrajowcom',
                    'obcokrajowcami', 'obcokrajowcach'],
    'przybysz*': ['przybysz', 'przybysza', 'przybyszowi', 'przybyszem', 'przybyszu',
                  'przybysze', 'przybyszów', 'przybyszom', 'przybyszami', 'przybyszach'],
    'inżynier*': ['inżynier', 'inżyniera', 'inżynierowi', 'inżynierem', 'inżynierze',
                  'inżynierowie', 'inżynierów', 'inżynierom', 'inżynierami', 'inżynierach'],
    'socjal*': ['socjal', 'socjalu', 'socjalem', 'socjalowi', 'socjale'],

    # --- border ---
    'granic*': ['granica', 'granicy', 'granicę', 'granicą', 'granico', 'granice', 'granic',
                'granicom', 'granicami', 'granicach',
                'graniczny', 'graniczna', 'graniczne', 'granicznej', 'granicznego',
                'granicznych', 'granicznym', 'granicznymi', 'graniczną'],
    'granica z Białorusią': ['"granica z Białorusią"', '"granicy z Białorusią"',
                             '"granicę z Białorusią"', '"granicą z Białorusią"',
                             '"granica polsko-białoruska"', '"granicy polsko-białoruskiej"',
                             '"granicę polsko-białoruską"', '"granicą polsko-białoruską"',
                             '"białoruska granica"', '"białoruskiej granicy"',
                             '"białoruską granicę"', '"białoruską granicą"'],
    'Straż Graniczna': ['"Straż Graniczna"', '"Straży Granicznej"', '"Straż Graniczną"',
                        '"Strażą Graniczną"', '"strażnik graniczny"', '"strażnicy graniczni"',
                        '"strażników granicznych"', '"strażnikom granicznym"'],

    # --- Ukraine ---
    'ukrain*': ['Ukraina', 'Ukrainy', 'Ukrainie', 'Ukrainę', 'Ukrainą', 'Ukraino',
                'Ukrainiec', 'Ukraińca', 'Ukraińcowi', 'Ukraińcem', 'Ukraińcu', 'Ukraińcy',
                'Ukraińców', 'Ukraińcom', 'Ukraińcami', 'Ukraińcach',
                'Ukrainka', 'Ukrainki', 'Ukraince', 'Ukrainkę', 'Ukrainką', 'Ukrainek',
                'Ukrainkom', 'Ukrainkami', 'Ukrainkach'],
    'ukraiń*': ['ukraiński', 'ukraińska', 'ukraińskie', 'ukraińskiego', 'ukraińskiej',
                'ukraińskiemu', 'ukraińskim', 'ukraińskich', 'ukraińskimi', 'ukraińską',
                'ukraińscy', 'ukraińsku'],
    'ukrajin*': ['Ukrajina', 'Ukrajiny', 'Ukrajini', 'Ukrajinu', 'Ukrajinoju'],
    'kijow*': ['Kijów', 'Kijowa', 'Kijowie', 'Kijowem', 'Kijowowi',
               'kijowski', 'kijowska', 'kijowskie', 'kijowskiej', 'kijowskiego',
               'kijowskich', 'kijowskim', 'Kyiv', 'Kijiw'],
    'zełeńsk*': ['Zełeński', 'Zełeńskiego', 'Zełeńskiemu', 'Zełeńskim',
                 'Zełenski', 'Zełenskiego', 'Zełenskiemu', 'Zełenskim',
                 'Zełenskyj', 'Zelensky', 'Zelenskyy'],

    # --- war, Russia ---
    'wojn*': ['wojna', 'wojny', 'wojnie', 'wojnę', 'wojną', 'wojno',
              'wojnom', 'wojnami', 'wojnach'],
    'wojen*': ['wojen', 'wojenny', 'wojenna', 'wojenne', 'wojennej', 'wojennego',
               'wojennych', 'wojennym', 'wojennymi', 'wojenną', 'wojenni'],
    'putin*': ['Putin', 'Putina', 'Putinowi', 'Putinem', 'Putinie',
               'putinowski', 'putinowska', 'putinowskie', 'putinowskiej', 'putinowskiego',
               'putinowskich', 'putinizm', 'putinizmu'],
    'rosj*': ['Rosja', 'Rosji', 'Rosję', 'Rosją', 'Rosjo',
              'Rosjanin', 'Rosjanina', 'Rosjaninowi', 'Rosjaninem', 'Rosjaninie',
              'Rosjanie', 'Rosjan', 'Rosjanom', 'Rosjanami', 'Rosjanach',
              'Rosjanka', 'Rosjanki', 'Rosjankę', 'Rosjanek'],
    'rosyj*': ['rosyjski', 'rosyjska', 'rosyjskie', 'rosyjskiego', 'rosyjskiej',
               'rosyjskiemu', 'rosyjskim', 'rosyjskich', 'rosyjskimi', 'rosyjską',
               'rosyjscy', 'rosyjsku'],
    'kreml*': ['Kreml', 'Kremla', 'Kremlowi', 'Kremlem', 'Kremlu',
               'kremlowski', 'kremlowska', 'kremlowskie', 'kremlowskiej', 'kremlowskiego',
               'kremlowskich', 'kremlowskim'],

    # --- NATO, EU ---
    # No * on NATO: the wildcard 'nato*' would also match the very common word "natomiast".
    'NATO': ['NATO', 'natowski', 'natowska', 'natowskie', 'natowskiej', 'natowskiego',
             'natowskich', 'natowskim', 'natowskimi', 'natowską', 'natowscy'],
    'UE': ['UE', '"Unia Europejska"', '"Unii Europejskiej"', '"Unię Europejską"',
           '"Unią Europejską"'],
    'unijn*': ['unijny', 'unijna', 'unijne', 'unijnej', 'unijnego', 'unijnemu',
               'unijnych', 'unijnym', 'unijnymi', 'unijną', 'unijni'],
    'bruksel*': ['Bruksela', 'Brukseli', 'Brukselę', 'Brukselą',
                 'brukselski', 'brukselska', 'brukselskie', 'brukselskiej',
                 'brukselskiego', 'brukselskich'],

    # --- Poland, Poles (very frequent - these dominate search time) ---
    'polsk*': ['Polska', 'Polski', 'Polsce', 'Polskę', 'Polską', 'Polsko',
               'polskie', 'polskiego', 'polskiej', 'polskiemu', 'polskim', 'polskich',
               'polskimi', 'polscy', 'polsku'],
    'polak*': ['Polak', 'Polaka', 'Polakowi', 'Polakiem', 'Polaku',
               'Polacy', 'Polaków', 'Polakom', 'Polakami', 'Polakach',
               'Polka', 'Polki', 'Polce', 'Polkę', 'Polką', 'Polek', 'Polkom',
               'Polkami', 'Polkach'],

    # --- LOADED / PEJORATIVE TERMS ---
    # They contradict the rule at the top (no slurs in the denominator) and will push the
    # hate rate up regardless of the event. Kept because they were on the original list;
    # consider moving them to a separate analysis or removing them.
    'pontoniar*': ['pontoniarz', 'pontoniarza', 'pontoniarzowi', 'pontoniarzem',
                   'pontoniarze', 'pontoniarzy', 'pontoniarzom', 'pontoniarzami',
                   'pontoniarzach'],
    'putler*': ['Putler', 'Putlera', 'Putlerowi', 'Putlerem', 'Putlerze'],
    'rusk*': ['ruski', 'ruska', 'ruskie', 'ruskiego', 'ruskiej', 'ruskiemu', 'ruskim',
              'ruskich', 'ruskimi', 'ruską', 'ruscy'],
    'eurokra*': ['eurokrata', 'eurokraty', 'eurokracie', 'eurokratę', 'eurokratą',
                 'eurokraci', 'eurokratów', 'eurokratom', 'eurokratami', 'eurokratach',
                 'eurokracja', 'eurokracji', 'eurokrację', 'eurokracją',
                 'eurokratyczny', 'eurokratyczna', 'eurokratyczne', 'eurokratycznej',
                 'eurokratycznego', 'eurokratycznych'],
}

LANGUAGE = 'pl'
POLISH_COMMENTS_ONLY = True        # drop comments without 'pl' in langs
# Every query is first run once over the whole material window. Only when it has more than
# WINDOW_PAGES pages (~WINDOW_PAGES x 100 posts) is it re-run day by day, so the page cap can
# never silently cut off the oldest (baseline) days. Rare forms cost 1 request instead of 61.
# Day-by-day: at most MAX_PAGES_PER_KEYWORD_DAY pages (x 100 posts) per query per day;
# every (query, day) that still hits the cap is listed in report.json.
WINDOW_PAGES = 10
MAX_PAGES_PER_KEYWORD_DAY = 50
RESULTS_PER_PAGE = 100
THREAD_DEPTH = 100                 # how many levels of reply-to-reply to fetch
INCLUDE_LINKS = True              # True reveals author accounts - testing only
# ====================================================

BASE = 'https://bsky.social/xrpc'
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'BlueskyResearchPilot/1.0'})
TZ = ZoneInfo(TIMEZONE)


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
    """Builds the analysis and material fetch windows for one event (local time)."""
    day_zero = datetime(day.year, day.month, day.day, tzinfo=TZ)
    analysis_start = day_zero - timedelta(days=DAYS_BEFORE)
    analysis_end = day_zero + timedelta(days=DAYS_AFTER + 1)
    slug = re.sub(r'[^\w-]+', '_', name).strip('_') or 'event'
    return Event(
        name=name,
        date=day,
        output_dir=OUTPUT_ROOT / f'{day.isoformat()}_{slug}',
        day_zero=day_zero,
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        material_start=analysis_start - timedelta(days=MATERIAL_MAX_AGE),
    )


def load_events(path=None):
    """Reads {"name": "YYYY-MM-DD", ...} and returns events sorted by date."""
    path = Path(path) if path else EVENTS_FILE
    if not path.exists():
        raise SystemExit(f'Events file not found: {path}\n'
                         'Create it, e.g.: {"test_event": "2026-07-31"}')
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


def day_slices(ev):
    """Local-time days from the material start to the analysis end, as (start, end) pairs."""
    start = ev.material_start
    while start < ev.analysis_end:
        end = min(start + timedelta(days=1), ev.analysis_end)
        yield start, end
        start = end


def utc_iso(dt):
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_date(text):
    """Bluesky ISO 8601 -> timezone-aware datetime; None if unparseable."""
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


def log_in():
    load_env()
    handle = os.environ.get('BSKY_HANDLE')
    password = os.environ.get('BSKY_APP_PASSWORD')
    if not handle or not password:
        raise SystemExit('Set BSKY_HANDLE and BSKY_APP_PASSWORD (app password) in .env.local.')
    r = SESSION.post(f'{BASE}/com.atproto.server.createSession',
                     json={'identifier': handle, 'password': password}, timeout=30)
    r.raise_for_status()
    SESSION.headers['Authorization'] = f"Bearer {r.json()['accessJwt']}"


def api_get(method, params):
    for attempt in range(4):
        time.sleep(0.5)
        try:
            r = SESSION.get(f'{BASE}/{method}', params=params, timeout=30)
            if r.status_code in (400, 401) and 'ExpiredToken' in r.text:
                log_in()  # the token expires after about 2 h
                continue
            if r.status_code == 429 or 500 <= r.status_code < 600:
                if attempt == 3:
                    r.raise_for_status()
                retry_after = r.headers.get('Retry-After', '')
                time.sleep(min(60, float(retry_after)) if retry_after.isdigit()
                           else 2 ** (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))
    # A RequestException (not RuntimeError) so callers' error handling catches it.
    raise requests.RequestException(f'Could not fetch data from {method}')


# ---------- pseudonymisation ----------

class Pseudonyms:
    """Maps Bluesky identifiers to sequential ids: P00001, K000001, A00001."""

    def __init__(self):
        self.mapping = {}
        self.counters = {}

    def _id(self, key, prefix, digits):
        if key not in self.mapping:
            self.counters[prefix] = self.counters.get(prefix, 0) + 1
            self.mapping[key] = f'{prefix}{self.counters[prefix]:0{digits}d}'
        return self.mapping[key]

    def post(self, uri):
        return self._id(uri, 'P', 5)

    def comment(self, uri):
        # A comment that was itself a search hit keeps its P id.
        return self.mapping.get(uri) or self._id(uri, 'K', 6)

    def author(self, did):
        return self._id(did, 'A', 5)


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


def post_link(uri):
    # at://did:plc:xxx/app.bsky.feed.post/KEY -> https://bsky.app/profile/did:plc:xxx/post/KEY
    did, _, key = uri.removeprefix('at://').split('/')
    return f'https://bsky.app/profile/{did}/post/{key}'


def shared_fields(post, ps, ev):
    """Fields common to a material and a comment."""
    record = post.get('record', {})
    created = parse_date(record.get('createdAt'))
    return {
        'platform': 'bluesky',
        'event': ev.name,
        'author_id': ps.author(post.get('author', {}).get('did', '')),
        'text': mask_text(record.get('text', '')),
        'created_at': record.get('createdAt', ''),
        'created_date': local_day(created).isoformat() if created else '',
        'langs': '|'.join(record.get('langs', [])),
        'likes': post.get('likeCount', 0),
        'replies': post.get('replyCount', 0),
        'reposts': post.get('repostCount', 0),
        'quotes': post.get('quoteCount', 0),
        'link': post_link(post['uri']) if INCLUDE_LINKS else '',
        '_created': created,  # helper object, never written to CSV
    }


# ---------- sampling rule ----------

def evaluate_comment(created, material_created, langs, ev):
    """Returns (in_rule, exclusion_reason, material_age_days, relative_day)."""
    if created is None or material_created is None:
        return False, 'missing_date', '', ''
    age = (created - material_created).total_seconds() / 86400
    relative_day = (local_day(created) - ev.date).days
    if age < 0:
        # Comment older than its material - usually a bad client-set timestamp.
        return False, 'comment_before_material', round(age, 3), relative_day
    if age > MATERIAL_MAX_AGE:
        return False, 'material_too_old', round(age, 3), relative_day
    if not (ev.analysis_start <= created < ev.analysis_end):
        return False, 'outside_analysis_window', round(age, 3), relative_day
    if POLISH_COMMENTS_ONLY and 'pl' not in langs.split('|'):
        return False, 'other_language', round(age, 3), relative_day
    return True, '', round(age, 3), relative_day


# ---------- walking a thread ----------

def walk_thread(node, material, ps, ev, included, excluded, parent_id='', depth=0):
    """Depth-first walk of the reply tree; applies the sampling rule to each comment."""
    post = node.get('post')  # blocked/deleted posts carry no 'post' key
    current_id = parent_id
    if post and depth == 0:
        current_id = material['post_id']
    elif post:
        current_id = ps.comment(post['uri'])
        fields = shared_fields(post, ps, ev)
        in_rule, reason, age, relative_day = evaluate_comment(
            fields['_created'], material['_created'], fields['langs'], ev)
        row = {
            'comment_id': current_id,
            'post_id': material['post_id'],
            'thread_id': material['post_id'],
            'reply_to': parent_id,
            'depth': depth,
            'relative_day': relative_day,
            'material_age_days': age,
            'material_created_at': material['created_at'],
            'material_created_date': material['created_date'],
            'material_keywords': material['keywords'],
            'is_material_author': fields['author_id'] == material['author_id'],
            **fields,
        }
        if in_rule:
            included.append(row)
        else:
            excluded.append({**row, 'exclusion_reason': reason})
    replies = sorted(node.get('replies', []),
                     key=lambda n: n.get('post', {}).get('record', {}).get('createdAt', ''))
    for child in replies:
        walk_thread(child, material, ps, ev, included, excluded, current_id, depth + 1)


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
    """One row per day of the analysis window, including days with no data (zeros)."""
    rows = []
    for d in range(-DAYS_BEFORE, DAYS_AFTER + 1):
        day = (ev.day_zero + timedelta(days=d)).date()
        day_comments = [c for c in comments if c['relative_day'] == d]
        rows.append({
            'event': ev.name,
            'relative_day': d,
            'date': day.isoformat(),
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


# ---------- search ----------

def group_queries(label, forms):
    """What is actually sent to the search for one keyword group."""
    if USE_WILDCARD and label.endswith('*'):
        stem = label[:-1].lower()
        return [label] + [f for f in forms if not f.lower().startswith(stem)]
    return forms


def build_label_patterns():
    """Local regex per group: does the post TEXT contain one of the group's forms?"""
    patterns = {}
    for label, forms in KEYWORD_GROUPS.items():
        alternatives = [re.escape(f.strip('"')) for f in forms]
        if label.endswith('*'):
            alternatives.append(re.escape(label[:-1]) + r'\w*')
        patterns[label] = re.compile(r'(?<!\w)(?:' + '|'.join(alternatives) + r')(?!\w)',
                                     re.IGNORECASE)
    return patterns


LABEL_PATTERNS = build_label_patterns()


def text_labels(text):
    return '|'.join(label for label, p in LABEL_PATTERNS.items() if p.search(text))


def fetch_pages(query, since, until, max_pages):
    """Pages through one search. Returns (posts, complete); complete=False if capped."""
    posts, cursor, seen_cursors = [], None, set()
    for _ in range(max_pages):
        params = {'q': query, 'lang': LANGUAGE, 'sort': 'latest',
                  'since': utc_iso(since), 'until': utc_iso(until),
                  'limit': RESULTS_PER_PAGE}
        if cursor:
            params['cursor'] = cursor
        data = api_get('app.bsky.feed.searchPosts', params)
        batch = data.get('posts', [])
        posts.extend(batch)
        cursor = data.get('cursor')
        if not cursor or cursor in seen_cursors or not batch:
            return posts, True
        seen_cursors.add(cursor)
    return posts, False


def search_posts(ev):
    """Searches materials for every form of every keyword group over the material window."""
    found, post_labels, post_queries = {}, {}, {}
    per_query, errors, truncated = {}, [], []

    def add(batch, label, query, hits):
        for post in batch:
            uri = post['uri']
            found.setdefault(uri, post)
            hits.add(uri)
            if label not in post_labels.setdefault(uri, []):
                post_labels[uri].append(label)
            if query not in post_queries.setdefault(uri, []):
                post_queries[uri].append(query)

    for label, forms in KEYWORD_GROUPS.items():
        group_hits, split = set(), 0
        for query in group_queries(label, forms):
            hits = set()
            # 1. Whole window in one go - enough for rare forms.
            try:
                batch, complete = fetch_pages(query, ev.material_start, ev.analysis_end,
                                              WINDOW_PAGES)
                add(batch, label, query, hits)
            except (requests.RequestException, ValueError) as e:
                errors.append({'stage': 'search', 'query': query, 'day': 'whole window',
                               'error': str(e)})
                complete = False
            # 2. Too many results (or an error): repeat day by day.
            if not complete:
                split += 1
                for since, until in day_slices(ev):
                    day_label = local_day(since).isoformat()
                    try:
                        batch, day_complete = fetch_pages(query, since, until,
                                                          MAX_PAGES_PER_KEYWORD_DAY)
                    except (requests.RequestException, ValueError) as e:
                        errors.append({'stage': 'search', 'query': query, 'day': day_label,
                                       'error': str(e)})
                        continue
                    add(batch, label, query, hits)
                    if not day_complete:
                        truncated.append({'label': label, 'query': query, 'day': day_label})
            per_query[query] = len(hits)
            group_hits |= hits
        queries = len(group_queries(label, forms))
        print(f'  {label}: {queries} queries ({split} split by day), {len(group_hits)} posts, '
              f'{len(found)} unique so far', flush=True)
    return found, post_labels, post_queries, per_query, errors, truncated


def check_keywords():
    """Tests on the last 7 days whether the search supports stem* wildcards."""
    log_in()
    until = datetime.now(timezone.utc)
    since = until - timedelta(days=7)
    print('Wildcard test on the last 7 days (lang=pl, first page only, max 100 per query).\n')
    print(f'{"group":14} {"stem as word":>13} {"stem*":>8} {"stem* posts with the stem in text":>36}')
    for label in KEYWORD_GROUPS:
        if not label.endswith('*'):
            continue
        stem = label[:-1]
        try:
            exact, exact_done = fetch_pages(stem, since, until, 1)
            wild, wild_done = fetch_pages(label, since, until, 1)
        except (requests.RequestException, ValueError) as e:
            print(f'{label:14} error: {e}')
            continue
        pattern = re.compile(rf'(?<!\w){re.escape(stem)}\w*', re.IGNORECASE)
        with_stem = sum(bool(pattern.search(p.get('record', {}).get('text', ''))) for p in wild)
        more = lambda done: ' ' if done else '+'
        print(f'{label:14} {len(exact):>12}{more(exact_done)} {len(wild):>7}{more(wild_done)} '
              f'{with_stem:>29}/{len(wild)}')
    print('\nHow to read it:\n'
          ' - "stem*" much larger than "stem as word" AND most of those posts contain the\n'
          '   stem in their text -> wildcards work; you may set USE_WILDCARD = True.\n'
          ' - "stem*" about the same as "stem as word" (often 0) -> wildcards do not work;\n'
          '   keep USE_WILDCARD = False so the listed forms are searched.')


# ---------- one event ----------

def run_event(ev):
    window_complete = ev.analysis_end <= datetime.now(timezone.utc)
    print(f'Event: {ev.name} (day 0 = {ev.date})')
    print(f'Output folder: {ev.output_dir.resolve()}')
    print(f'Comment analysis window: {ev.analysis_start.date()} .. {ev.last_day}')
    print(f'Material fetch window:   {ev.material_start.date()} .. {ev.last_day} '
          f'({MATERIAL_MAX_AGE}-day run-up)')
    print(f'Rule: a comment counts when its material is 0..{MATERIAL_MAX_AGE} days old')
    if not window_complete:
        print('WARNING: the analysis window has not ended yet - data will be incomplete.')
    print()

    ev.output_dir.mkdir(parents=True, exist_ok=True)
    ps = Pseudonyms()

    # 1. Materials (posts): every form of every keyword group
    n_queries = sum(len(group_queries(l, f)) for l, f in KEYWORD_GROUPS.items())
    print(f'Searching for materials: {len(KEYWORD_GROUPS)} keyword groups, {n_queries} queries'
          f'{" (wildcards on)" if USE_WILDCARD else ""}', flush=True)
    found, post_labels, post_queries, per_query, errors, truncated = search_posts(ev)

    posts, uri_by_id = [], {}
    for uri, post in found.items():
        fields = shared_fields(post, ps, ev)
        post_id = ps.post(uri)
        uri_by_id[post_id] = uri
        posts.append({
            'post_id': post_id,
            'keywords': '|'.join(post_labels[uri]),
            'text_keywords': text_labels(fields['text']),
            'search_queries': '|'.join(post_queries[uri]),
            'is_reply': 'reply' in post.get('record', {}),
            'relative_day': ((local_day(fields['_created']) - ev.date).days
                             if fields['_created'] else ''),
            'comments_in_thread': 0,
            'comments_in_rule': 0,
            **fields,
        })
    print(f'\nFound {len(posts)} unique materials.', flush=True)
    if truncated:
        print(f'Page cap hit for {len(truncated)} (keyword, day) pairs - see report.json.')

    # 2. Comments under the materials, filtered by the sampling rule
    comments, excluded, seen_comments, threads = [], [], set(), []
    to_fetch = [p for p in posts if p['replies'] > 0]
    print(f'Materials with replies: {len(to_fetch)}\n', flush=True)
    for i, p in enumerate(to_fetch, 1):
        if i % 25 == 0 or i == 1:
            print(f'Threads {i}/{len(to_fetch)}', flush=True)
        try:
            data = api_get('app.bsky.feed.getPostThread',
                           {'uri': uri_by_id[p['post_id']], 'depth': THREAD_DEPTH,
                            'parentHeight': 0})
            local_included, local_excluded = [], []
            walk_thread(data['thread'], p, ps, ev, local_included, local_excluded)
            # The same comment can appear in two threads - store it once.
            fresh = [c for c in local_included if c['comment_id'] not in seen_comments]
            seen_comments.update(c['comment_id'] for c in fresh)
            comments.extend(fresh)
            excluded.extend(c for c in local_excluded if c['comment_id'] not in seen_comments)
            p['comments_in_thread'] = len(local_included) + len(local_excluded)
            p['comments_in_rule'] = len(local_included)
            threads.append({'post_id': p['post_id'],
                            'reported_replies': p['replies'],
                            'fetched_comments': p['comments_in_thread'],
                            'in_rule': len(local_included)})
        except (requests.RequestException, ValueError, KeyError) as e:
            errors.append({'stage': 'comments', 'post_id': p['post_id'], 'error': str(e)})
        if i % 50 == 0:
            write_all(ev, posts, comments, excluded)  # partial save

    # 3. Write output and report
    write_all(ev, posts, comments, excluded)
    daily = daily_aggregate(ev, posts, comments)
    per_day = [row['comments'] for row in daily]
    reasons = {}
    for c in excluded:
        reasons[c['exclusion_reason']] = reasons.get(c['exclusion_reason'], 0) + 1

    report = {
        'collected_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'event': ev.name,
        'event_date': ev.date.isoformat(),
        'output_folder': str(ev.output_dir),
        'window_complete': window_complete,
        'timezone': TIMEZONE,
        'analysis_window': [ev.analysis_start.date().isoformat(), ev.last_day.isoformat()],
        'material_window': [ev.material_start.date().isoformat(), ev.last_day.isoformat()],
        'material_max_age_days': MATERIAL_MAX_AGE,
        'days_before': DAYS_BEFORE, 'days_after': DAYS_AFTER,
        'keyword_groups': KEYWORD_GROUPS, 'use_wildcard': USE_WILDCARD,
        'language': LANGUAGE,
        'polish_comments_only': POLISH_COMMENTS_ONLY,
        'links_included': INCLUDE_LINKS,
        'window_pages': WINDOW_PAGES,
        'max_pages_per_keyword_day': MAX_PAGES_PER_KEYWORD_DAY,
        'thread_depth': THREAD_DEPTH,
        'materials': len(posts),
        'materials_per_keyword': {k: sum(k in post_labels[u] for u in found)
                                  for k in KEYWORD_GROUPS},
        'materials_per_query': per_query,
        'materials_without_keyword_in_text': sum(not p['text_keywords'] for p in posts),
        'truncated_keyword_days': truncated,
        'comments_in_rule': len(comments),
        'comments_excluded': len(excluded),
        'exclusion_reasons': reasons,
        'authors': ps.counters.get('A', 0),
        'comments_per_day': {'min': min(per_day), 'median': median(per_day),
                             'max': max(per_day),
                             'days_below_50': sum(n < 50 for n in per_day)},
        'threads': threads,
        'errors': errors,
        'notes': [
            'Pseudonyms are assigned afresh for every event and every run - data from two '
            'events or two runs cannot be joined on author_id.',
            'The sampling rule is identical for every day of the window, baseline days '
            'included.',
            'Bluesky search matches whole words, so every inflected form is searched '
            'separately; keywords = groups whose search found the post, text_keywords = '
            'groups whose forms appear in the post text. An empty text_keywords usually means '
            'the word was in a link, link preview or image alt text.',
            'Each query ran over the whole window and, if it had more than window_pages '
            'pages, again day by day; truncated_keyword_days lists the (query, day) pairs '
            'that still hit the page cap and may be incomplete.',
            'createdAt is set by the client and can be unreliable; comments dated before '
            'their material are excluded (reason: comment_before_material).',
            'Bluesky search does not guarantee complete results and the API may truncate '
            'very large threads - compare reported_replies with fetched_comments.',
            "Bluesky's reach in Poland before late 2024 was small.",
        ],
    }
    # report.json is written last, so its presence marks the event as finished.
    (ev.output_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                               encoding='utf-8')

    print(f'\nDone. Materials: {len(posts)}, comments in rule: {len(comments)}, '
          f'excluded: {len(excluded)}')
    print(f'Comments per day - median: {median(per_day)}, min: {min(per_day)}, '
          f'max: {max(per_day)}, days below 50: {sum(n < 50 for n in per_day)}/{len(per_day)}')
    if errors:
        print(f'Errors: {len(errors)} - see report.json')


# ---------- main ----------

def main():
    global OUTPUT_ROOT, DAYS_BEFORE, DAYS_AFTER, MATERIAL_MAX_AGE

    parser = argparse.ArgumentParser(description='Collect Bluesky posts and comments around events.')
    parser.add_argument('events', nargs='?', help='JSON file {"name": "YYYY-MM-DD", ...} '
                                                  f'(default: {EVENTS_FILE.name})')
    parser.add_argument('--out', default=str(OUTPUT_ROOT),
                        help=f'output folder (default: {OUTPUT_ROOT})')
    parser.add_argument('--check-keywords', action='store_true',
                        help='only test whether stem* wildcards work in Bluesky search')
    args = parser.parse_args()

    # time windows come from params.yaml (tracked by DVC), falling back to the constants above
    OUTPUT_ROOT = Path(args.out)
    if PARAMS_FILE.exists():
        params = (yaml.safe_load(PARAMS_FILE.read_text(encoding='utf-8')) or {}).get('bluesky', {})
        DAYS_BEFORE = params.get('days_before', DAYS_BEFORE)
        DAYS_AFTER = params.get('days_after', DAYS_AFTER)
        MATERIAL_MAX_AGE = params.get('material_max_age', MATERIAL_MAX_AGE)

    if args.check_keywords:
        check_keywords()
        return

    events = load_events(args.events)
    print(f'Events to process: {len(events)}')
    for ev in events:
        print(f'  {ev.date}  {ev.name}  ->  {ev.output_dir}')

    log_in()
    failed, skipped = [], []
    for i, ev in enumerate(events, 1):
        print(f'\n===== [{i}/{len(events)}] {ev.name} ({ev.date}) =====')
        if SKIP_DONE and (ev.output_dir / 'report.json').exists():
            print('Already collected (report.json exists) - skipping.')
            skipped.append(ev.name)
            continue
        try:
            run_event(ev)
        except Exception as e:  # one broken event should not stop the others
            print(f'FAILED: {e!r}')
            failed.append(ev.name)

    print(f'\nAll done. Processed: {len(events) - len(failed) - len(skipped)}, '
          f'skipped: {len(skipped)}, failed: {len(failed)}')
    if failed:
        print('Failed events (re-run the script to retry them): ' + ', '.join(failed))


if __name__ == '__main__':
    main()