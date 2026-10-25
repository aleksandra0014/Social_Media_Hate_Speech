"""Gold standard labels from coded rounds (LLMs and/or people) plus human adjudication.
    python scripts/gold_build.py --names gold_v1 gold_v2
Unanimous items keep their label (also when a model marked uncertain, unless --review-uncertain).
Disagreements, missing codes and a random check of
unanimous items go to <round>/results/adjudication.xlsx: fill hate / hate_migrants there and rerun.
Writes data/annotation/gold/gold.csv and report.md.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_agreement import clean_sheet, norm, read_sheet  # noqa: E402
from annotation_sample import OUT_ROOT  # noqa: E402

GOLD_DIR = OUT_ROOT / 'gold'
REASONS = ['niezgoda', 'uncertain', 'brak kodu', 'kontrola', 'rozstrzygnięte wcześniej']
CONTEXT = ['context_post', 'context_parent', 'context_quote', 'text']
VALID = {'0/0', '1/0', '1/1'}


def pair(hate, hm):
    """'1/0' etc.; hate=0 with empty hate_migrants counts as 0/0, anything else invalid is ''."""
    hate, hm = norm(hate), norm(hm)
    if hate == '0' and hm == '':
        hm = '0'
    p = f'{hate}/{hm}'
    return p if p in VALID else ''


def load_votes(base, name):
    """item x annotator tables: label pair, uncertain flag, note."""
    pairs, unc, notes = {}, {}, {}
    for f in sorted(p for p in (base / 'annotated').glob(f'{name}_*') if p.suffix in ('.xlsx', '.csv')):
        a = f.stem[len(name) + 1:]
        df = clean_sheet(read_sheet(f), a)[0].set_index('item_id')
        pairs[a] = pd.Series([pair(h, m) for h, m in zip(df['hate'], df['hate_migrants'])], index=df.index)
        unc[a], notes[a] = df['uncertain'], df['note']
    return pd.DataFrame(pairs), pd.DataFrame(unc), pd.DataFrame(notes)


def majority(row):
    votes = pd.Series([v for v in row if v])
    if votes.empty:
        return ''
    top = votes.value_counts()
    return top.index[0] if top.iloc[0] > len(votes) / 2 else ''


def triage(pairs, unc, check_share, seed, review_uncertain=False):
    """Why each item needs a person ('' = unanimous and sure)."""
    complete = (pairs != '').all(axis=1)
    same = pairs.nunique(axis=1) == 1
    uncertain = (unc == '1').any(axis=1)
    reason = pd.Series('', index=pairs.index)
    reason[~complete] = 'brak kodu'
    reason[complete & ~same] = 'niezgoda'
    if review_uncertain:
        reason[complete & same & uncertain] = 'uncertain'
    unanimous = pairs.index[reason == '']
    n = round(len(unanimous) * check_share)
    if n:
        reason[pd.Series(unanimous).sample(n=n, random_state=seed)] = 'kontrola'   # are unanimous models right?
    return reason


def read_decisions(path):
    """{item_id: (pair, note)} from a filled sheet (xlsx or csv; hate + hate_migrants columns or one 'decision'
    column like '1/1'); invalid entries are returned as problems."""
    if not path.exists():
        return {}, []
    df = read_sheet(path)
    if 'hate' not in df and 'decision' in df:
        split = df['decision'].str.replace('-', '/').str.split('/', n=1, expand=True).reindex(columns=[0, 1])
        df['hate'], df['hate_migrants'] = split[0].fillna(''), split[1].fillna('')
    decisions, problems = {}, []
    for _, r in df.iterrows():
        h, hm = str(r.get('hate', '')), str(r.get('hate_migrants', ''))
        if not (h.strip() or hm.strip()):
            continue
        p = pair(h, hm)
        if p:
            decisions[r['item_id']] = (p, r.get('note', ''))
        else:
            problems.append(f'{path.parent.parent.name} {r["item_id"]} ({path.name}): {h}/{hm} '
                            'nie jest dozwoloną parą (0/0, 1/0, 1/1)')
    return decisions, problems


def all_decisions(results):
    """Decisions from disagreements.csv / .xlsx, overridden by adjudication.xlsx (the sheet gold_build writes)."""
    decisions, problems = {}, []
    for f in ('disagreements.csv', 'disagreements.xlsx', 'adjudication.xlsx'):
        d, p = read_decisions(results / f)
        decisions.update(d)
        problems += p
    return decisions, problems


def build_round(base, name, check_share=0.1, seed=2026, review_uncertain=False):
    manifest = pd.read_csv(base / 'manifest.csv', encoding='utf-8-sig', dtype=str, keep_default_na=False)
    ids = manifest['item_id']
    pairs, unc, notes = (t.reindex(ids).fillna('') for t in load_votes(base, name))
    if pairs.shape[1] < 2:
        sys.exit(f'{name}: need at least 2 coded sheets in {base / "annotated"}')
    reason = triage(pairs, unc, check_share, seed, review_uncertain)
    unsure = (unc == '1').any(axis=1)
    decisions, problems = all_decisions(base / 'results')
    reason[(reason == '') & ids.set_axis(ids).isin(decisions)] = 'rozstrzygnięte wcześniej'

    meta = manifest.set_index('item_id')
    votes = pairs.apply(lambda r: '; '.join(f'{a}={v or "-"}' for a, v in r.items()), axis=1)
    maj = pairs.apply(majority, axis=1)
    rows = []
    for iid in ids:
        if iid in decisions:
            label, note = decisions[iid]
            source = 'checked' if reason[iid] == 'kontrola' else 'adjudicated'
        elif reason[iid] in ('', 'kontrola'):
            label, note = pairs.loc[iid].iloc[0], ''
            source = 'unanimous_uncertain' if unsure[iid] else 'unanimous'
        else:
            continue   # waits for a decision
        rows.append({'round': name, 'item_id': iid, **meta.loc[iid, ['platform', 'event_folder', 'comment_id',
                     'post_id', 'pool', 'text']].to_dict(), 'hate': label[0], 'hate_migrants': label[2],
                     'label_source': source, 'majority': maj[iid], 'votes': votes[iid], 'adjudication_note': note})
    gold = pd.DataFrame(rows)

    review = meta.loc[reason[reason != ''].index, ['platform'] + CONTEXT].copy()
    review.insert(0, 'reason', reason[review.index])
    for a in pairs.columns:
        review[a] = pairs.loc[review.index, a] + unc.loc[review.index, a].map({'1': ' [?]'}).fillna('') + \
            (' - ' + notes.loc[review.index, a]).where(notes.loc[review.index, a] != '', '')
    review['majority'] = maj[review.index]
    review['hate'] = [decisions.get(i, ('', ''))[0][:1] for i in review.index]
    review['hate_migrants'] = [decisions.get(i, ('', ''))[0][2:] for i in review.index]
    review['note'] = [decisions.get(i, ('', ''))[1] for i in review.index]
    review = review.rename_axis('item_id').assign(_o=review['reason'].map(REASONS.index))
    review = review.sort_values(['_o', 'item_id']).drop(columns='_o').reset_index()

    stats = {'items': len(ids), 'unanimous': int((reason.isin(['', 'kontrola'])).sum()),
             **{r: int((reason == r).sum()) for r in REASONS}, 'decided': len(decisions),
             'pending': len(ids) - len(gold), 'problems': problems}
    adj = gold[(gold['label_source'] == 'adjudicated') & (gold['majority'] != '')] if len(gold) else gold   # ties: no majority
    stats['adjudicated_like_majority'] = round(float((adj['hate'] + '/' + adj['hate_migrants'] ==
                                                      adj['majority']).mean()), 3) if len(adj) else None
    chk = gold[gold['label_source'] == 'checked']
    stats['unanimous_uncertain'] = int((gold['label_source'] == 'unanimous_uncertain').sum()) if len(gold) else 0
    stats['checked'] = len(chk)
    stats['checked_changed'] = int((chk['hate'] + '/' + chk['hate_migrants'] != chk['majority']).sum())
    return gold, review, stats


def write_review(review, path):
    """Adjudication sheet: model votes read-only, hate / hate_migrants / note to fill (dropdowns)."""
    wb = Workbook()
    ws = wb.active
    ws.title = 'rozstrzyganie'
    ws.append(list(review.columns))
    for row in review.itertuples(index=False):
        ws.append([str(v) for v in row])
    n = len(review) + 1
    for i, col in enumerate(review.columns, start=1):
        cell = ws.cell(row=1, column=i)
        cell.font = Font(bold=True)
        ws.column_dimensions[cell.column_letter].width = {'text': 70, 'context_post': 35, 'context_parent': 30,
                                                          'context_quote': 30, 'note': 35,
                                                          'codebook_change': 35}.get(col, 18)
        if col in ('hate', 'hate_migrants'):
            cell.fill = PatternFill('solid', fgColor='FFF2CC')
            dv = DataValidation(type='list', formula1='"1,0"', allow_blank=True)
            ws.add_data_validation(dv)
            dv.add(f'{cell.column_letter}2:{cell.column_letter}{n}')
        for r in range(2, n + 1):
            ws.cell(row=r, column=i).alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'C2'
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        wb.save(path)
    except PermissionError:
        sys.exit(f'{path} is open in Excel - save and close it, then rerun.')


def render(per_round, gold):
    lines = ['# Gold standard', '', '| Runda | komentarzy | jednogłośne (w tym z uncertain) | niezgoda | uncertain do rozstrzygnięcia | brak kodu | '
             'kontrola (sprawdzone / zmienione) | rozstrzygnięte | czeka | decyzja = większość |',
             '|---|---|---|---|---|---|---|---|---|---|']
    for name, s in per_round.items():
        lines.append(f"| {name} | {s['items']} | {s['unanimous']} ({s['unanimous_uncertain']}) | {s['niezgoda']} | {s['uncertain']} | "
                     f"{s['brak kodu']} | {s['kontrola']} ({s['checked']} / {s['checked_changed']}) | "
                     f"{s['decided']} | {s['pending']} | {s['adjudicated_like_majority']} |")
    if len(gold):
        lines += ['', '| Platforma | n | hate=1 | hate_migrants=1 |', '|---|---|---|---|']
        for p, g in gold.groupby('platform'):
            lines.append(f"| {p} | {len(g)} | {(g['hate'] == '1').mean():.1%} | "
                         f"{(g['hate_migrants'] == '1').mean():.1%} |")
    problems = [p for s in per_round.values() for p in s['problems']]
    if problems:
        lines += ['', 'Problemy w arkuszach rozstrzygania:'] + [f'- {p}' for p in problems]
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser(description='Build gold labels from coded rounds and human decisions.')
    ap.add_argument('--names', nargs='+', required=True, help='rounds, e.g. gold_v1 gold_v2')
    ap.add_argument('--check-share', type=float, default=0.1, help='share of unanimous items a person checks')
    ap.add_argument('--seed', type=int, default=2026)
    ap.add_argument('--review-uncertain', action='store_true',
                    help='send unanimous items a model marked uncertain to adjudication too')
    args = ap.parse_args()

    golds, per_round = [], {}
    for name in args.names:
        base = OUT_ROOT / name
        gold, review, stats = build_round(base, name, args.check_share, args.seed, args.review_uncertain)
        write_review(review, base / 'results' / 'adjudication.xlsx')
        golds.append(gold)
        per_round[name] = stats
        print(f"{name}: {len(gold)}/{stats['items']} labelled, {stats['pending']} wait in "
              f"{base / 'results' / 'adjudication.xlsx'}")

    gold = pd.concat(golds, ignore_index=True)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    gold.to_csv(GOLD_DIR / 'gold.csv', index=False, encoding='utf-8-sig')
    md = render(per_round, gold)
    (GOLD_DIR / 'report.md').write_text(md, encoding='utf-8')
    print('\n' + md)


if __name__ == '__main__':
    main()
