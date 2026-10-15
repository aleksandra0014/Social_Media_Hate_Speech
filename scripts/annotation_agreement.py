"""Inter-annotator agreement on `hate` for one annotation round (docs/ANOTACJA.md).
    python scripts/annotation_agreement.py --name pilot_v1
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_sample import OUT_ROOT

_PL = str.maketrans('ąćęłńóśźżĄĆĘŁŃÓŚŹŻ', 'acelnoszzACELNOSZZ')


def norm(v):
    v = str(v).strip().translate(_PL).lower()
    return {'tak': '1', 'nie': '0', '1.0': '1', '0.0': '0', 'nan': '', 'none': ''}.get(v, v)


def read_sheet(path):
    df = pd.read_excel(path, sheet_name=0, dtype=str) if path.suffix == '.xlsx' else \
        pd.read_csv(path, encoding='utf-8-sig', dtype=str)
    return df.fillna('')


def clean_sheet(df, annotator):
    """Invalid or missing `hate` becomes '' and is reported; uncertain without a note is only reported."""
    df = df.copy()
    for col in ('hate', 'uncertain', 'note'):
        df[col] = df.get(col, pd.Series('', index=df.index)).fillna('')
    df['hate'], df['uncertain'] = df['hate'].map(norm), df['uncertain'].map(norm).replace('0', '')
    problems = [(annotator, iid, 'hate', v, 'missing' if v == '' else 'value not 0/1')
                for iid, v in zip(df['item_id'], df['hate']) if v not in ('0', '1')]
    problems += [(annotator, iid, 'uncertain', v, 'value not 1/empty')
                 for iid, v in zip(df['item_id'], df['uncertain']) if v not in ('', '1')]
    problems += [(annotator, iid, 'note', '', 'uncertain=1 without note')
                 for iid in df.loc[(df['uncertain'] == '1') & (df['note'].str.strip() == ''), 'item_id']]
    df.loc[~df['hate'].isin(['0', '1']), 'hate'] = ''
    df.loc[df['uncertain'] != '1', 'uncertain'] = ''
    return df, problems


def krippendorff_alpha(units):
    """Nominal alpha; units = labels given to the same item by different annotators."""
    units = [u for u in units if len(u) >= 2]
    cats = sorted({v for u in units for v in u})
    if len(cats) < 2:
        return float('nan')
    idx = {c: i for i, c in enumerate(cats)}
    o = np.zeros((len(cats), len(cats)))
    for u in units:
        for a, b in itertools.permutations(range(len(u)), 2):
            o[idx[u[a]], idx[u[b]]] += 1 / (len(u) - 1)
    n_c = o.sum(axis=1)
    n = n_c.sum()
    d_e = (n * n - (n_c ** 2).sum()) / (n * (n - 1))
    return float(1 - ((n - np.trace(o)) / n) / d_e) if d_e > 0 else float('nan')


def alpha_ci(units, n_boot=1000, seed=2026):
    units = [u for u in units if len(u) >= 2]
    rng = np.random.default_rng(seed)
    vals = [krippendorff_alpha([units[i] for i in rng.integers(0, len(units), len(units))])
            for _ in range(n_boot)] if units else []
    vals = [v for v in vals if not np.isnan(v)]
    return [round(float(np.quantile(vals, q)), 3) for q in (.025, .975)] if vals else [None, None]


def cohen_kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    po = (a == b).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in set(a) | set(b))
    return float((po - pe) / (1 - pe)) if pe < 1 else float('nan')


def fleiss_kappa(units):
    """Fleiss' kappa; needs the same number of labels per item -> only complete items count."""
    if not units or len({len(u) for u in units}) != 1 or len(units[0]) < 2:
        return float('nan')
    cats = sorted({v for u in units for v in u})
    counts = np.array([[u.count(c) for c in cats] for u in units], dtype=float)
    n = counts.sum(axis=1)[0]
    p_i = ((counts ** 2).sum(axis=1) - n) / (n * (n - 1))
    p_e = ((counts.sum(axis=0) / counts.sum()) ** 2).sum()
    return float((p_i.mean() - p_e) / (1 - p_e)) if p_e < 1 else float('nan')


def mean_cohen_kappa(wide):
    vals = []
    for a, b in itertools.combinations(wide.columns, 2):
        m = (wide[a] != '') & (wide[b] != '')
        if m.sum() >= 5:
            vals.append(cohen_kappa(wide.loc[m, a], wide.loc[m, b]))
    vals = [v for v in vals if not np.isnan(v)]
    return round(float(np.mean(vals)), 3) if vals else float('nan')


def summary(wide):
    """wide: item x annotator table of `hate` ('' = missing)."""
    units = [[v for v in row if v != ''] for row in wide.values.tolist()]
    units = [u for u in units if len(u) >= 2]
    complete = [u for u in units if len(u) == wide.shape[1]]
    return {'n_items': len(units), 'alpha': round(krippendorff_alpha(units), 3), 'alpha_ci95': alpha_ci(units),
            'fleiss_kappa': round(fleiss_kappa(complete), 3), 'n_items_fleiss': len(complete),
            'mean_cohen_kappa': mean_cohen_kappa(wide),
            'full_agreement': round(float(np.mean([len(set(u)) == 1 for u in units])), 3) if units else None,
            'hate_share': round(float(np.mean([v == '1' for u in units for v in u])), 3) if units else None}


def main():
    ap = argparse.ArgumentParser(description='Agreement on `hate` for one annotation round.')
    ap.add_argument('--name', required=True)
    args = ap.parse_args()

    base = OUT_ROOT / args.name
    manifest = pd.read_csv(base / 'manifest.csv', encoding='utf-8-sig', dtype=str, keep_default_na=False)
    files = sorted(p for p in (base / 'annotated').glob(f'{args.name}_*') if p.suffix in ('.xlsx', '.csv'))
    if len(files) < 2:
        sys.exit(f'Need at least 2 filled sheets in {base / "annotated"} (found {len(files)}).')

    sheets, problems = {}, []
    for f in files:
        a = f.stem[len(args.name) + 1:]
        df, p = clean_sheet(read_sheet(f), a)
        sheets[a] = df.set_index('item_id')
        problems += p
        print(f'{a}: {int((df["hate"] != "").sum())}/{len(df)} items coded')
    annotators = sorted(sheets)
    h = pd.DataFrame({a: s['hate'] for a, s in sheets.items()}).reindex(manifest['item_id']).fillna('')
    unc = pd.DataFrame({a: s['uncertain'] for a, s in sheets.items()}).reindex(h.index).fillna('')
    meta = manifest.set_index('item_id')

    report = {'round': args.name, 'annotators': annotators, 'items': len(h), 'hate': summary(h),
              'hate_without_uncertain_items': summary(h[(unc != '1').all(axis=1)]),
              'by_platform': {k: summary(h.loc[g.index]) for k, g in meta.groupby('platform')},
              'by_pool': {k: summary(h.loc[g.index]) for k, g in meta.groupby('pool')},
              'pairs': {}, 'annotators_detail': {}}
    for a, b in itertools.combinations(annotators, 2):
        m = (h[a] != '') & (h[b] != '')
        if m.sum() >= 5:
            report['pairs'][f'{a}-{b}'] = {'kappa': round(cohen_kappa(h.loc[m, a], h.loc[m, b]), 3),
                                           'agreement': round(float((h.loc[m, a] == h.loc[m, b]).mean()), 3),
                                           'n': int(m.sum())}
    for a in annotators:
        share = h.drop(columns=a).apply(lambda r: (r[r != ''] == '1').mean() if (r != '').any() else np.nan, axis=1)
        m = (h[a] != '') & share.notna() & (share != 0.5)  # ties among the others are skipped
        report['annotators_detail'][a] = {
            'agreement_with_majority': round(float((h.loc[m, a] == np.where(share[m] > .5, '1', '0')).mean()), 3)
            if m.any() else None,
            'hate_share': round(float((h[a] == '1').sum() / max((h[a] != '').sum(), 1)), 3),
            'uncertain_share': round(float((unc[a] == '1').mean()), 3)}

    dis_ids = h.index[h.apply(lambda r: len({v for v in r if v != ''}) > 1, axis=1)]
    dis = meta.loc[dis_ids, ['platform', 'pool', 'context_post', 'context_parent', 'context_quote',
                          'text']].copy()
    for a in annotators:
        s = sheets[a].reindex(dis_ids)
        dis[a] = s['hate'] + s['uncertain'].map({'1': ' [?]'}).fillna('') + \
            (' - ' + s['note']).where(s['note'].fillna('') != '', '')
    dis['hate_yes'] = h.loc[dis_ids].apply(lambda r: f"{(r == '1').sum()}/{(r != '').sum()}", axis=1)
    dis['decision'], dis['codebook_change'] = '', ''

    res = base / 'results'
    res.mkdir(exist_ok=True)
    dis.sort_values(['hate_yes', 'platform']).reset_index().to_csv(res / 'disagreements.csv', index=False,
                                                                      encoding='utf-8-sig')
    pd.DataFrame(problems, columns=['annotator', 'item_id', 'column', 'value', 'problem']) \
        .to_csv(res / 'problems.csv', index=False, encoding='utf-8-sig')
    (res / 'agreement.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    md = render(report, len(dis), len(problems))
    (res / 'report.md').write_text(md, encoding='utf-8')
    print('\n' + md)


def verdict(a):
    if a is None or np.isnan(a):
        return 'brak danych'
    return 'dobra (>= 0,80)' if a >= .8 else ('wstępna (0,667–0,80)' if a >= .667 else 'za niska (< 0,667)')


def render(r, n_dis, n_prob):
    row = lambda name, s: (f"| {name} | {s['n_items']} | {s['alpha']} | [{s['alpha_ci95'][0]}, {s['alpha_ci95'][1]}] "
                           f"| {s['fleiss_kappa']} (n={s['n_items_fleiss']}) | {s['mean_cohen_kappa']} "
                           f"| {s['full_agreement']} | {s['hate_share']} | {verdict(s['alpha'])} |")
    lines = [f"# Zgodność kodowania `hate`: {r['round']}", '',
             f"Kodujący: {', '.join(r['annotators'])} · komentarzy: {r['items']}", '',
             '| Zakres | n | α Krippendorffa | 95% CI α | κ Fleissa | średnia κ Cohena | pełna zgodność '
             '| udział hate=1 | ocena (wg α) |',
             '|---|---|---|---|---|---|---|---|---|',
             row('wszystkie', r['hate']), row('bez komentarzy z `uncertain`', r['hate_without_uncertain_items'])]
    lines += [row(f'platforma: {k}', s) for k, s in r['by_platform'].items()]
    lines += [row(f'pula: {k}', s) for k, s in r['by_pool'].items()]
    lines += ['', '| Para | κ Cohena | zgodność | n |', '|---|---|---|---|']
    lines += [f"| {p} | {s['kappa']} | {s['agreement']} | {s['n']} |" for p, s in r['pairs'].items()]
    lines += ['', '| Osoba | zgodność z większością pozostałych | udział hate=1 | udział uncertain |', '|---|---|---|---|']
    lines += [f"| {a} | {s['agreement_with_majority']} | {s['hate_share']} | {s['uncertain_share']} |"
              for a, s in r['annotators_detail'].items()]
    lines += ['', f'Rozbieżności: **{n_dis}** (`results/disagreements.csv`).', f'Problemy w arkuszach: **{n_prob}** (`results/problems.csv`).']
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    main()
