"""Hate speech predictions with ready-made / fine-tuned classifiers (notebooks/models/04, 05, 07).

The same rules as in the earlier project (AMC_Hate_Speech, notebooks 04-07), applied to the comment set the team uses:

1. Comment set = the team's topic pre-filter (scripts/topic_filter.py), computed here in memory, nothing is written
   to topic/: a comment is kept when the slur lexicon labels it 1/1 OR scripts/topic_sample.is_potential_migration
   matches the post context + comment text.
2. Slur lexicon first (src/lexicon/slurs.py, the same rule as scripts/preprocess_slurs.py, codebook 4.12):
   hate_auto = 1 -> hate, the model is not asked.
3. The model scores only the remaining comments. Texts longer than MAX_LENGTH tokens are split into overlapping
   windows; prob_hate_max = maximum over windows (hate anywhere in the text).
4. hate_final = 1 if hate_auto else hate_pred_max; label_source = 'slownik' | '<model folder>'.

Output: data/interim/<platform>/<event>/<OUT_DIRNAME>/comments.csv + meta.json, written in chunks (resumable).
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / 'scripts'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from preprocess_slurs import flag_frame          # noqa: E402  (team code, scripts/preprocess_slurs.py)
from topic_sample import is_potential_migration  # noqa: E402  (team code, scripts/topic_sample.py)

INTERIM = ROOT / 'data' / 'interim'
PLATFORMS = ('wykop', 'bluesky', 'youtube')
SLUR_COLS = ['slurs', 'slur_categories', 'slur_needs_context', 'hate_auto', 'hate_migrants_auto']
OUT_COLS = ['comment_id', 'in_topic', 'hate_auto', 'hate_migrants_auto', 'slurs', 'slur_categories',
            'slur_needs_context', 'prob_hate', 'prob_hate_max', 'hate_pred_max', 'n_tokens', 'n_windows',
            'hate_final', 'label_source']


def read_csv(path, **kw):
    return pd.read_csv(path, encoding='utf-8-sig', dtype=str, keep_default_na=False, **kw)


def event_dirs(platforms=PLATFORMS, events=None):
    """{(platform, folder): path} for every event folder that has clean/comments.csv."""
    out = {}
    for platform in platforms:
        for d in sorted((INTERIM / platform).glob('*/')):
            if (d / 'clean' / 'comments.csv').exists() and (events is None or d.name in events or d.name[11:] in events):
                out[(platform, d.name)] = d
    return out


def slur_frame(event_dir, comments):
    """slurs/comments.csv when the DVC stage exists (wykop, bluesky); otherwise the same function on the fly."""
    p = event_dir / 'slurs' / 'comments.csv'
    if p.exists():
        s = read_csv(p)
        s = s[['comment_id'] + [c for c in SLUR_COLS if c in s.columns]]
        if 'hate_migrants_auto' not in s:
            s['hate_migrants_auto'] = s['hate_auto']
        return s.drop_duplicates('comment_id'), 'slurs/ (DVC)'
    return flag_frame(comments, 'comment_id').astype(str), 'src/lexicon (policzone)'


def topic_frame(event_dir):
    """Clean comments + slur columns + in_topic flag exactly like scripts/topic_filter.py."""
    comments = read_csv(event_dir / 'clean' / 'comments.csv').drop_duplicates('comment_id')
    comments = comments[comments['text'].str.strip() != '']
    slurs, origin = slur_frame(event_dir, comments)
    df = comments.merge(slurs, on='comment_id', how='left')
    for c in SLUR_COLS:
        df[c] = df[c].fillna('').replace('', '0' if c in ('hate_auto', 'hate_migrants_auto', 'slur_needs_context') else '')
    posts_p = event_dir / 'clean' / 'posts.csv'
    posts = read_csv(posts_p).drop_duplicates('post_id').set_index('post_id') if posts_p.exists() else pd.DataFrame()

    ctx_cache = {}

    def post_context(post_id):
        if post_id not in ctx_cache:
            if post_id not in posts.index:
                ctx_cache[post_id] = ''
            else:
                p = posts.loc[post_id]
                ctx_cache[post_id] = ((p.get('title') or p.get('text') or '').strip().replace('\n', ' ')[:300])
        return ctx_cache[post_id]

    is_slur = (df['hate_auto'] == '1') & (df['hate_migrants_auto'] == '1')
    regex = np.fromiter((is_potential_migration(t, post_context(p)) for t, p in zip(df['text'], df['post_id'])),
                        dtype=bool, count=len(df))
    df['in_topic'] = (is_slur.values | regex).astype(int)
    return df, origin


class Predictor:
    """Tokenizer + model + (optional) text preparation; batching by token budget, windows for long texts."""

    def __init__(self, model_id, device, prep=None, max_length=512, tokens_per_batch=8192, max_batch_size=128,
                 window_overlap=128, hate_label_index=1, token=None, use_fp16=True):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        from transformers.utils import logging as hf_logging
        hf_logging.set_verbosity_error()
        self.torch = torch
        self.device = device
        self.prep = prep or (lambda t: t)
        self.max_length, self.tokens_per_batch, self.max_batch_size = max_length, tokens_per_batch, max_batch_size
        self.overlap, self.idx = window_overlap, hate_label_index
        kw = {'token': token} if token else {}
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, **kw)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id, **kw).eval().to(device)
        self.special = self.tokenizer('', add_special_tokens=True)['input_ids']   # [CLS]/<s> ... [SEP]/</s>
        self.precision = 'float32'
        if use_fp16 and device.type in ('cuda', 'mps'):
            self._try_fp16()

    def _forward(self, batch_ids):
        torch = self.torch
        with torch.inference_mode():
            enc = self.tokenizer.pad({'input_ids': batch_ids}, return_tensors='pt')
            enc = {k: v.to(self.device) for k, v in enc.items()}
            logits = self.model(**enc).logits.float()
            return torch.softmax(logits, dim=-1)[:, self.idx].cpu().numpy()

    def _try_fp16(self):
        probe = ['Dzień dobry, jutro ma padać deszcz.', 'Imigranci to robactwo, które trzeba wytępić.',
                 'Ty pierdolony debilu, zdychaj.']
        p32 = self.predict(probe)[0]
        self.model.half()
        p16 = self.predict(probe)[0]
        if not np.isfinite(p16).all() or float(np.abs(p16 - p32).max()) > 0.02:
            self.model.float()
        else:
            self.precision = 'float16'

    def windows(self, ids):
        w = self.max_length - 2
        if len(ids) <= w:
            return [self.special[:1] + ids + self.special[1:]]
        step = max(w - min(self.overlap, w // 2), 1)
        out, start = [], 0
        while True:
            out.append(self.special[:1] + ids[start:start + w] + self.special[1:])
            if start + w >= len(ids):
                return out
            start += step

    def predict(self, texts, pbar=None):
        """-> (prob first window, prob max over windows, n_tokens, n_windows), in input order."""
        ids = self.tokenizer([self.prep(t) for t in texts], add_special_tokens=False)['input_ids']
        owners, inputs = [], []
        for i, x in enumerate(ids):
            ws = self.windows(x)
            owners += [i] * len(ws)
            inputs += ws
        lens = np.array([len(x) for x in inputs])
        order = np.argsort(-lens, kind='stable')
        probs = np.empty(len(inputs), dtype=np.float32)
        i = 0
        while i < len(order):
            bs = max(1, min(self.max_batch_size, self.tokens_per_batch // max(lens[order[i]], 1)))
            sel = order[i:i + bs]
            probs[sel] = self._forward([inputs[j] for j in sel])
            i += bs
        if pbar is not None:
            pbar.update(len(texts))
        owners = np.array(owners)
        first = np.full(len(texts), np.nan, dtype=np.float32)
        mx = np.full(len(texts), -1.0, dtype=np.float32)
        nwin = np.zeros(len(texts), dtype=int)
        for k in range(len(inputs) - 1, -1, -1):    # reverse -> 'first' ends on the first window
            o = owners[k]
            first[o] = probs[k]
            mx[o] = max(mx[o], probs[k])
            nwin[o] += 1
        return first, mx, np.array([len(x) + 2 for x in ids]), nwin


def _atomic_csv(df, path):
    tmp = path.with_suffix(path.suffix + '.tmp')
    df.to_csv(tmp, index=False, encoding='utf-8-sig')
    os.replace(tmp, path)


def _ensure_gitignore(event_dir, name):
    gi = event_dir / '.gitignore'
    lines = gi.read_text(encoding='utf-8').splitlines() if gi.exists() else []
    if f'/{name}' not in lines:
        gi.write_text('\n'.join(lines + [f'/{name}']) + '\n', encoding='utf-8')


def run_event(predictor, event_dir, out_dirname, signature, threshold=0.5, chunk_size=2000, force=False,
              total_bar=None, tqdm=None):
    """Predict one event folder; resumable via <out>/_parts. Returns a summary dict."""
    out_dir = event_dir / out_dirname
    out_p, meta_p, parts = out_dir / 'comments.csv', out_dir / 'meta.json', out_dir / '_parts'
    if not force and out_p.exists() and meta_p.exists():
        meta = json.loads(meta_p.read_text(encoding='utf-8'))
        if all(meta.get(k) == v for k, v in signature.items()):
            return {**meta['summary'], 'status': 'gotowe – pominięte'}
    if force and out_dir.exists():
        import shutil
        shutil.rmtree(out_dir)
    parts.mkdir(parents=True, exist_ok=True)
    _ensure_gitignore(event_dir, out_dirname)

    t0 = time.time()
    df, origin = topic_frame(event_dir)
    topic = df[df['in_topic'] == 1]
    todo = topic[topic['hate_auto'] != '1']
    files = sorted(parts.glob('part_*.csv'))
    done = pd.concat([pd.read_csv(f, dtype={'comment_id': str}) for f in files]) if files else pd.DataFrame()
    if len(done):
        todo = todo[~todo['comment_id'].isin(set(done['comment_id']))]
    bar = tqdm(total=len(todo), desc=f'{event_dir.parent.name}/{event_dir.name}', unit='txt', leave=False) if tqdm else None
    n_files = len(files)
    for k in range(0, len(todo), chunk_size):
        chunk = todo.iloc[k:k + chunk_size]
        first, mx, ntok, nwin = predictor.predict(chunk['text'].tolist(), pbar=bar)
        n_files += 1
        _atomic_csv(pd.DataFrame({'comment_id': chunk['comment_id'].values, 'prob_hate': first.round(5),
                                  'prob_hate_max': mx.round(5), 'n_tokens': ntok, 'n_windows': nwin}),
                    parts / f'part_{n_files:05d}.csv')
        if total_bar is not None:
            total_bar.update(len(chunk))
    if bar is not None:
        bar.close()

    files = sorted(parts.glob('part_*.csv'))
    scored = pd.concat([pd.read_csv(f, dtype={'comment_id': str}) for f in files]).drop_duplicates('comment_id', keep='last') \
        if files else pd.DataFrame(columns=['comment_id', 'prob_hate', 'prob_hate_max', 'n_tokens', 'n_windows'])
    out = topic[['comment_id', 'in_topic'] + SLUR_COLS].merge(scored, on='comment_id', how='left')
    out['hate_auto'] = out['hate_auto'].astype(int)
    out['hate_migrants_auto'] = out['hate_migrants_auto'].astype(int)
    out['hate_pred_max'] = (out['prob_hate_max'] >= threshold).astype('Int64').where(out['prob_hate_max'].notna())
    out['hate_final'] = np.where(out['hate_auto'] == 1, 1, out['hate_pred_max'].fillna(0)).astype(int)
    out['label_source'] = np.where(out['hate_auto'] == 1, 'slownik', out_dirname)
    for c in ('n_tokens', 'n_windows'):
        out[c] = out[c].astype('Int64')
    _atomic_csv(out[OUT_COLS], out_p)

    summary = {'platform': event_dir.parent.name, 'event': event_dir.name, 'clean': int(len(df)),
               'topic': int(len(topic)), 'slownik_1_1': int((out['hate_auto'] == 1).sum()),
               'model_scored': int(out['prob_hate_max'].notna().sum()),
               'model_hate': int(out['hate_pred_max'].fillna(0).sum()), 'hate_final': int(out['hate_final'].sum()),
               'share_hate_final': round(float(out['hate_final'].mean()), 4) if len(out) else None,
               'windowed': int((out['n_windows'].fillna(1) > 1).sum()), 'lexicon_from': origin}
    meta = {**signature, 'threshold': threshold, 'device': str(predictor.device), 'precision': predictor.precision,
            'seconds': round(time.time() - t0, 1), 'finished_at': datetime.now().isoformat(timespec='seconds'),
            'summary': summary}
    tmp = meta_p.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, meta_p)
    for f in parts.glob('part_*.csv'):
        f.unlink()
    parts.rmdir()
    return {**summary, 'status': 'policzone'}


def count_todo(dirs, out_dirname, signature, force=False):
    """Topic sizes and how many comments the model still has to score (for ETA)."""
    rows = []
    for (platform, ev), d in dirs.items():
        meta_p = d / out_dirname / 'meta.json'
        if not force and meta_p.exists():
            meta = json.loads(meta_p.read_text(encoding='utf-8'))
            if all(meta.get(k) == v for k, v in signature.items()):
                s = meta['summary']
                rows.append({'platform': platform, 'event': ev, 'clean': s['clean'], 'topic': s['topic'],
                             'slownik_1_1': s['slownik_1_1'], 'do_modelu': 0})
                continue
        df, _ = topic_frame(d)
        t = df[df['in_topic'] == 1]
        rows.append({'platform': platform, 'event': ev, 'clean': len(df), 'topic': len(t),
                     'slownik_1_1': int((t['hate_auto'] == '1').sum()), 'do_modelu': int((t['hate_auto'] != '1').sum())})
    return pd.DataFrame(rows)
