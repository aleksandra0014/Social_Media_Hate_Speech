"""Figures for the preprint (English), drawn in the style of the original analysis notebook.

The plotting code is ported from notebooks/4_analizy_llm_hate_migrant/cross_platform_hate_analysis.ipynb
(branch gold_herbert: map of changes, H1 summary, decomposition, daily course, H2 by type, H3 platforms, words,
word cloud, targets, authors, likes), from notebooks/6_wyniki_koncowe/wyniki_koncowe.ipynb (gold standard F1)
and from the hate_analysis notebook (feature profile, feature regression). The numbers come from the Gemini
analysis: run scripts/final_analysis_gemini.py first. This script reads only its outputs (no comment texts):

    reports/final_gemini/results.json, cell_effects.csv, decomposition.csv, daily.csv, cloud_freq.json
    reports/gold_gemini_eval/hate_gemini_vs_models.csv, llm_metrics.csv

Output: reports/final_gemini/preprint/*.png  (the names used in the preprint's main.tex)

    python scripts/final_figures_gemini.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "reports" / "final_gemini"
GOLD = ROOT / "reports" / "gold_gemini_eval"
OUT = SRC / "preprint"
OUT.mkdir(parents=True, exist_ok=True)

R = json.loads((SRC / "results.json").read_text(encoding="utf-8"))
EFF = pd.read_csv(SRC / "cell_effects.csv")
DEC = pd.read_csv(SRC / "decomposition.csv")
DAILY = pd.read_csv(SRC / "daily.csv")
CELLS_INFO = pd.read_csv(SRC / "cells.csv")
SMALL = {f"{r.platform}:{r.event}" for r in CELLS_INFO.itertuples() if not r.in_analysis}

PL = ["wykop", "youtube", "bluesky"]
EVENTS = {  # folder: (English label, type) – same as scripts/final_analysis_gemini.py
    "2022-02-24_Atak_Rosji_Ukraina": ("Russian invasion of Ukraine", "war"),
    "2022-05-08_Zabojstwo_Nowy_Swiat": ("Murder in Warsaw", "disinformation"),
    "2023-09-22_Premiera_Zielona_Granica": ("Film Green Border", "political"),
    "2023-10-15_Referendum_Wybory": ("Election and referendum", "political"),
    "2024-04-10_Pakt_Azyl_PE": ("EU Pact adopted", "political"),
    "2024-05-28_Atak_Zolnierz_Granica": ("Attack on a soldier", "criminal"),
    "2024-06-06_Smierc_Zolnierza": ("Death of the soldier", "criminal"),
    "2024-09-08_Bojka_Srem": ("Brawl in Śrem", "criminal"),
    "2024-10-12_Strategia_Migracyjna": ("Migration strategy", "political"),
    "2024-12-20_Atak_Jarmark_Magdeburg": ("Magdeburg market attack", "criminal"),
    "2025-03-30_Dezinformacja_Wroclaw_Relokacja_Migrantow": ("Wrocław relocation hoax", "disinformation"),
    "2025-06-06_Naloty_ICE_Los_Angeles": ("ICE raids, LA", "political"),
    "2025-07-19_Protesty_Antyimigracyjne_Polska": ("Anti-migration protests", "political"),
    "2025-07-31_Dezinformacja_Swinoujscie_Autokar_Migranci": ("Świnoujście bus hoax", "disinformation"),
    "2025-10-15_Dezinformacja_Krakow": ("Kraków murder", "disinformation"),
    "2026-06-12_Pakt_Migracyjny_Wejscie_w_Zycie": ("EU Pact in force", "political"),
    "2026-07-11_Atak_Ukrainskie_Nastolatki_Bielsko_Biala": ("Bielsko-Biała attack", "criminal"),
    "2026-07-30_Ceuta_Masowe_Przekroczenie": ("Ceuta mass crossing", "border crisis"),
    "2026-08-15_Atak_Kamienna_Gora": ("Kamienna Góra attack", "criminal"),
    "2026-09-15_Atak_Jaroslaw": ("Jarosław attack", "criminal"),
}
EVENT_ORDER = list(EVENTS)
LBL = {e: v[0] for e, v in EVENTS.items()}
WINDOW, POST_FROM_DAY, ROLL_DAYS, MIN_DAILY_N, ALPHA = (-7, 14), 0, 3, 10, 0.05

# measure names in the style of the notebook (numerator/denominator)
MNAME = {"hate": "hate/all", "hate_migrant": "hate_migrant/all", "migrant": "migrant/all"}
SOURCE_NAMES = {"hate": "Gemini: hate", "hate_migrant": "Gemini: hate toward migrants",
                "migrant": "Gemini: comments about migration"}
ROLES = ["total hate", "attention: talk about migration", "tone: how hostile the talk is"]
ROLE_COLORS = ["#0b0b0b", "#0f766e", "#c2410c"]

PLATFORM_COLORS = {"wykop": "#2a78d6", "youtube": "#eb6834", "bluesky": "#1baf7a"}
TYPE_ORDER = ["criminal", "political", "disinformation", "border crisis", "war"]
TYPE_COLORS = dict(zip(TYPE_ORDER, ["#c2410c", "#7c3aed", "#0f766e", "#b45309", "#52514e"]))
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
BLUES = LinearSegmentedColormap.from_list("blues", ["#f2f7fd", "#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#0d366b"])
DIVERGING = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#a9c8ef", "#f2f1ee", "#f0b48f", "#c2410c"])

BASE_RC = {
    "figure.figsize": (13, 4.5), "figure.dpi": 100, "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#e6e5e1", "grid.linewidth": 0.8,
    "axes.axisbelow": True, "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlelocation": "left",
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "lines.linewidth": 2, "legend.frameon": False,
}
plt.rcParams.update(BASE_RC)


def savefig(fig, name, dpi=200):
    fig.savefig(OUT / f"{name}.png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", name)


def platform_legend(fig, platforms=PL, extra=(), top=0.9, **kw):
    handles = [plt.Line2D([], [], marker="o", ls="", ms=9, color=PLATFORM_COLORS[p]) for p in platforms]
    labels = list(platforms)
    for h, l in extra:
        handles.append(h)
        labels.append(l)
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.legend(handles, labels, loc="upper center", ncol=len(labels), bbox_to_anchor=(0.5, 1.0), **kw)


def log_ticks(ax, axis="x"):
    lo, hi = ax.get_xlim() if axis == "x" else ax.get_ylim()
    tk = [t for t in [0.05, 0.1, 0.25, 0.5, 1, 2, 4, 10, 20] if lo <= t <= hi]
    if len(tk) < 3:
        tk = [t for t in [0.05, 0.1, 0.2, 0.33, 0.5, 0.67, 1, 1.5, 2, 3, 5, 10, 20] if lo <= t <= hi]
    a = ax.xaxis if axis == "x" else ax.yaxis
    (ax.set_xticks if axis == "x" else ax.set_yticks)(tk, [f"{t:g}" for t in tk])
    a.set_minor_locator(mticker.NullLocator())


def forest(ax, groups, title="", xlabel="OR after vs before (log scale)", xlim=None):
    """groups = [{"label", "items": [{"label", "OR", "lo", "hi", "color"}], "diamond": {...} | None}]"""
    y, ticks, labels, bold, xs = 0.0, [], [], [], [1.0]
    for g in groups:
        for it in g["items"]:
            if pd.isna(it["OR"]):
                continue
            ax.hlines(y, it["lo"], it["hi"], color=it["color"], lw=1.6)
            ax.scatter(it["OR"], y, s=44, color=it["color"], edgecolor="white", linewidth=1.1, zorder=3)
            ticks.append(y); labels.append(it["label"]); bold.append(False)
            xs += [it["lo"], it["hi"]]
            y -= 1
        m = g.get("diamond")
        if m is not None and not pd.isna(m["OR"]):
            ax.fill([m["lo"], m["OR"], m["hi"], m["OR"]], [y, y + 0.32, y, y - 0.32], color=m.get("color", INK), zorder=3)
            ax.text(m["hi"] if xlim is None else min(m["hi"], xlim[1] / 1.9), y,
                    f"  {m['OR']:.2f} [{m.get('lo_lab', m['lo']):.2f}; {m.get('hi_lab', m['hi']):.2f}]", va="center", fontsize=8, color=INK2)
            ticks.append(y); labels.append(g["label"]); bold.append(True)
            xs += [m["lo"], m["hi"]]
            y -= 1
        y -= 0.6
    ax.axvline(1, color=INK2, ls="--", lw=1)
    ax.set_xscale("log")
    ax.set_xlim(*(xlim or (np.nanmin(xs) * 0.85, np.nanmax(xs) * 1.9)))
    log_ticks(ax, "x")
    ax.set_yticks(ticks, labels, fontsize=8.5)
    for lab, b in zip(ax.get_yticklabels(), bold):
        if b:
            lab.set_fontweight("bold")
    ax.set_ylim(y + 0.4, 0.8)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontsize=11)


def E(measure):
    e = EFF[EFF["measure"] == measure].copy()
    e["cell"] = pd.Categorical(e["cell"], [f"{p}:{ev}" for p in PL for ev in EVENT_ORDER], ordered=True)
    return e.sort_values("cell").assign(cell=lambda x: x["cell"].astype(str))


def ev_pool(measure, ev):
    """pooled OR of one event across platforms (decomposition.csv: DerSimonian–Laird, normal CI)."""
    lab, comp = (measure, "total") if measure != "migrant" else ("hate_migrant", "attention")
    r = DEC[(DEC["event"] == ev) & (DEC["label"] == lab) & (DEC["component"] == comp)]
    return None if r.empty or pd.isna(r["OR"].iloc[0]) else r.iloc[0]


def h1_verdict(measure):
    r = R["H1"][measure]
    if r["all"]["p"] < ALPHA:
        return "confirmed"
    if r["n_sig_up"] + r["n_sig_down"] or r.get("pooled_model", {}).get("p", 1) < ALPHA:
        return "partially"
    return "no evidence"


# ------------------------------------------------------------------ 1. map of changes (fig_heatmap_en)
def fig_heatmap():
    LOR_MAX = np.log(4)
    cmap = DIVERGING.copy()
    cmap.set_bad("#f4f3f0")
    srcs = ["hate", "hate_migrant"]
    sig_rows = set()
    for s in srcs:
        sig_rows |= set(E(s).loc[E(s)["sig"].astype(bool), "event"])
    fig, axes = plt.subplots(1, 2, figsize=(4.6 * 2 + 1.4, 0.45 * len(EVENT_ORDER) + 1.8), squeeze=False)
    fig.subplots_adjust(bottom=0.07)
    for ax, src in zip(axes[0], srcs):
        e = E(src).set_index("cell")
        mat = np.full((len(EVENT_ORDER), len(PL)), np.nan)
        for i, ev in enumerate(EVENT_ORDER):
            for j, p in enumerate(PL):
                c = f"{p}:{ev}"
                if c in SMALL:
                    ax.text(j, i, "·", ha="center", va="center", color=MUTED, fontsize=14)
                    continue
                if c not in e.index:
                    continue
                r = e.loc[c]
                if pd.isna(r["logOR"]):
                    ax.text(j, i, "·", ha="center", va="center", color=MUTED)
                    continue
                mat[i, j] = r["logOR"]
                sig = bool(r["sig"])
                ax.text(j, i, f"{r['OR']:.2f}{'*' if sig else ''}", ha="center", va="center", fontsize=8.5,
                        color="white" if abs(r["logOR"]) > 0.6 * LOR_MAX else INK, fontweight="bold" if sig else "normal")
        im = ax.imshow(np.ma.masked_invalid(np.clip(mat, -LOR_MAX, LOR_MAX)), cmap=cmap, vmin=-LOR_MAX, vmax=LOR_MAX,
                       aspect="auto")
        ax.set_xticks(range(len(PL)), PL)
        if src == srcs[0]:
            ax.set_yticks(range(len(EVENT_ORDER)), [LBL[ev] for ev in EVENT_ORDER])
            for lab, ev in zip(ax.get_yticklabels(), EVENT_ORDER):
                if ev in sig_rows:
                    lab.set_fontweight("bold")
        else:
            ax.set_yticks(range(len(EVENT_ORDER)), [])
        ax.set_xticks(np.arange(-0.5, len(PL)), minor=True)
        ax.set_yticks(np.arange(-0.5, len(EVENT_ORDER)), minor=True)
        ax.grid(which="minor", color="white", linewidth=2)
        ax.grid(which="major", visible=False)
        ax.tick_params(which="both", length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(f"{SOURCE_NAMES[src]}\n{MNAME[src]}", fontsize=11)
    cb = fig.colorbar(im, ax=axes[0].tolist(), fraction=0.03, pad=0.02)
    tk = [0.25, 0.5, 1, 2, 4]
    cb.set_ticks(np.log(tk), labels=[f"{t:g}" for t in tk])
    cb.set_label("OR after vs before (log scale)")
    cb.outline.set_visible(False)
    fig.text(0.01, 0.01, "* = significant after Holm correction;  “·” = too few comments (< 30 in a period);  "
             "empty = no data", fontsize=8.5, color=MUTED)
    savefig(fig, "fig_heatmap_en")


# ------------------------------------------------------------------ 2. H1 all together (fig_pooled_en)
def fig_pooled():
    ms = ["hate", "hate_migrant", "migrant"]
    fig, axes = plt.subplots(len(ms), 1, figsize=(12, 1.75 * len(ms) + 1.2), sharex=True, squeeze=False)
    axes = axes[:, 0]
    rng = np.random.default_rng(0)
    xs = []
    for ax, m in zip(axes, ms):
        e = E(m).dropna(subset=["OR"])
        a, pm = R["H1"][m]["all"], R["H1"][m]["pooled_model"]
        ax.scatter(e["OR"], 2 + rng.uniform(-0.18, 0.18, len(e)), s=34, color=e["platform"].map(PLATFORM_COLORS).tolist(),
                   alpha=0.75, edgecolor="white", linewidth=0.6, zorder=2)
        ax.fill([a["lo"], a["OR"], a["hi"], a["OR"]], [1, 1.28, 1, 0.72], color=INK, zorder=3)
        ax.hlines(0, pm["lo"], pm["hi"], color=INK2, lw=1.8)
        ax.scatter(pm["OR"], 0, marker="s", s=42, color=INK2, zorder=3)
        for y, o, lo, hi, p in [(1, a["OR"], a["lo"], a["hi"], a["p"]), (0, pm["OR"], pm["lo"], pm["hi"], pm["p"])]:
            ax.text(hi, y, f"  {o:.2f} [{lo:.2f}; {hi:.2f}], p = {p:.2g}", va="center", fontsize=8.5, color=INK2)
        ax.axvline(1, color=INK2, ls="--", lw=1)
        ax.set_yticks([2, 1, 0], [f"cells (n = {len(e)})", "pooled (meta-analysis)", "comment-level model"])
        ax.set_ylim(-0.6, 2.6)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", visible=True)
        ax.set_title(f"{SOURCE_NAMES[m]} – {MNAME[m]}: H1 {h1_verdict(m)}", fontsize=10.5)
        xs += [*e["OR"], a["lo"], a["hi"], pm["lo"], pm["hi"]]
    axes[-1].set_xscale("log")
    axes[-1].set_xlim(min(xs) * 0.85, max(xs) * 2.2)
    log_ticks(axes[-1], "x")
    axes[-1].set_xlabel("OR after vs before (log scale; < 1 = decrease, > 1 = increase)")
    platform_legend(fig, top=0.94)
    savefig(fig, "fig_pooled_en")


# ------------------------------------------------------------------ 3. decomposition (fig_decomp_en)
def fig_decomp():
    srcs = ["hate", "hate_migrant"]
    evs = [ev for ev in EVENT_ORDER if ev in set(DEC["event"])]
    fig, axes = plt.subplots(1, 2, figsize=(7.5 * 2, 0.5 * len(evs) + 2.4), squeeze=False)
    for ax, src in zip(axes[0], srcs):
        labels = [LBL[ev] for ev in evs] + ["ALL (random effects)"]
        xs = []
        for k, (comp, col) in enumerate(zip(["total", "attention", "tone"], ROLE_COLORS)):
            off = (k - 1) * 0.24
            for i, ev in enumerate(evs + ["ALL"]):
                r = DEC[(DEC["event"] == ev) & (DEC["label"] == src) & (DEC["component"] == comp)]
                if r.empty or pd.isna(r["OR"].iloc[0]):
                    continue
                r = r.iloc[0]
                if ev == "ALL":
                    ax.hlines(i + off, r["lo"], r["hi"], color=col, lw=2.2)
                    ax.scatter(r["OR"], i + off, s=60, marker="D", color=col, zorder=3)
                else:
                    ax.hlines(i + off, r["lo"], r["hi"], color=col, lw=1.4, alpha=0.8)
                    ax.scatter(r["OR"], i + off, s=38, zorder=3, edgecolor=col, linewidth=1.4,
                               facecolor=col if r["p_holm"] < ALPHA else "white")
                xs += [r["lo"], r["hi"]]
        ax.axvline(1, color=INK2, ls="--", lw=1)
        ax.axhline(len(evs) - 0.5, color=MUTED, lw=0.8)
        ax.set_xscale("log")
        ax.set_xlim(max(min(xs) * 0.85, 0.05), min(max(xs) * 1.2, 20))
        log_ticks(ax, "x")
        ax.set_yticks(range(len(labels)), labels if src == srcs[0] else [], fontsize=9)
        ax.set_ylim(len(labels) - 0.5, -0.5)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", visible=True)
        ax.set_xlabel("pooled OR after vs before (log scale)")
        ax.set_title(f"{SOURCE_NAMES[src]}\ntotal hate = attention × tone", fontsize=11)
    handles = [plt.Line2D([], [], marker="o", ls="-", color=c, ms=7) for c in ROLE_COLORS]
    handles += [plt.Line2D([], [], marker="o", ls="", mfc="white", mec=INK2, ms=7)]
    fig.legend(handles, ROLES + ["empty = not significant (Holm)"], loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    savefig(fig, "fig_decomp_en")


# ------------------------------------------------------------------ 4. daily course (fig_daily_en)
DAYS = range(WINDOW[0], WINDOW[1] + 1)


def daily_cell(p, ev, measure):
    g = (DAILY[(DAILY["platform"] == p) & (DAILY["event"] == ev)].set_index("relative_day")[[measure, "n"]]
         .reindex(DAYS, fill_value=0))
    share = (100 * g[measure] / g["n"]).where(g["n"] >= MIN_DAILY_N)
    pre = g.loc[g.index < POST_FROM_DAY]
    base = 100 * pre[measure].sum() / max(pre["n"].sum(), 1)
    return share, base, g["n"]


def smooth_split(s):
    roll = lambda x: x.rolling(ROLL_DAYS, center=True, min_periods=1).mean()
    return roll(s[s.index < POST_FROM_DAY]), roll(s[s.index >= POST_FROM_DAY])


def top_events(k=3):
    d = DEC[(DEC["label"] == "hate_migrant") & (DEC["component"] == "total") & (DEC["event"] != "ALL") & (DEC["k"] >= 2)]
    d = d.assign(abs_mu=np.abs(np.log(d["OR"])), sig=d["p_holm"] < ALPHA)
    d = pd.concat([d[d.sig].sort_values("abs_mu", ascending=False), d[~d.sig].sort_values("abs_mu", ascending=False)])
    return list(d["event"].head(k))


def fig_daily(events):
    metrics = ["hate_migrant", "migrant"]
    fig, axes = plt.subplots(len(events), len(metrics), figsize=(6 * len(metrics), 3.3 * len(events) + 0.6), squeeze=False)
    for i, ev in enumerate(events):
        for j, m in enumerate(metrics):
            ax = axes[i, j]
            ax2 = ax.twinx()
            bottom = np.zeros(len(DAYS))
            for p in PL:
                if E(m)[(E(m)["cell"] == f"{p}:{ev}")]["logOR"].notna().sum() == 0:
                    continue
                share, base, den = daily_cell(p, ev, m)
                idx = (share / base) if base > 0 else share * np.nan
                for part in smooth_split(idx):
                    ax.plot(part.index, part.values, color=PLATFORM_COLORS[p], lw=2.2)
                ax2.bar(list(DAYS), den.values, bottom=bottom, color=PLATFORM_COLORS[p], alpha=0.13, width=0.8)
                bottom += den.values
            ax2.grid(False)
            ax2.spines["right"].set_visible(True)
            ax2.spines["right"].set_color(MUTED)
            ax2.tick_params(axis="y", colors=MUTED, labelsize=7)
            if j == len(metrics) - 1:
                ax2.set_ylabel("comments / day", color=MUTED, fontsize=8)
            ax.set_zorder(ax2.get_zorder() + 1)
            ax.patch.set_visible(False)
            ax.axhline(1, color=INK2, ls=":", lw=1.2)
            ax.axvline(POST_FROM_DAY - 0.5, color=INK, ls="--", lw=1.1)
            if j == 0:
                ax.set_ylabel("index (OR, before = 1)")
            if i == len(events) - 1:
                ax.set_xlabel("day relative to the event")
            em = ev_pool(m, ev)
            tag = "" if em is None or em["p_holm"] < ALPHA else " (n.s.)"
            head = f"{LBL[ev]}{tag}\n{MNAME[m]}"
            ax.set_title(head if em is None else f"{head}: pooled OR {em['OR']:.2f}", fontsize=10)
    platform_legend(fig, top=0.95)
    savefig(fig, "fig_daily_en")


# ------------------------------------------------------------------ 5. H2 by event type (fig_h2_en)
def fig_h2(measure="hate_migrant"):
    """Events grouped by type: dot = event pooled over its platforms, diamond = type pooled over its cells (H2)."""
    h2 = R["H2"][measure]
    cols = [["criminal", "border crisis", "war"], ["political", "disinformation"]]
    xlim = (0.07, 45)
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.4))
    for ax, types in zip(axes, cols):
        groups = []
        for t in types:
            items = []
            for ev in [e for e in EVENT_ORDER if EVENTS[e][1] == t]:
                r = ev_pool(measure, ev)
                if r is not None:
                    items.append({"label": f"{LBL[ev]} (k={int(r['k'])})", "OR": r["OR"], "lo": r["lo"], "hi": r["hi"],
                                  "color": TYPE_COLORS[t]})
            bt = h2["by_type"][t]
            groups.append({"label": f"{t} – pooled", "items": items,
                           "diamond": {"OR": bt["OR"], "lo": max(bt["lo"], xlim[0]), "hi": min(bt["hi"], xlim[1]),
                                       "lo_lab": bt["lo"], "hi_lab": bt["hi"], "color": TYPE_COLORS[t]}})
        forest(ax, groups, xlim=xlim)
    fig.suptitle(f"{SOURCE_NAMES[measure]} – {MNAME[measure]}: events grouped by type\n"
                 f"meta-regression p = {h2['p_F']:.2f}, permutation p = {h2['p_perm']:.2f}", x=0.01, ha="left",
                 fontweight="bold", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    savefig(fig, "fig_h2_en")


# ------------------------------------------------------------------ 6. H3 platforms (fig_h3_en)
def fig_h3():
    srcs = ["hate", "hate_migrant"]
    fig, axes = plt.subplots(len(srcs), 2, figsize=(16, 5 * len(srcs)), gridspec_kw={"width_ratios": [1, 1.8]},
                             squeeze=False)
    for row, src in zip(axes, srcs):
        h3 = R["H3"][src]
        ax = row[0]
        for i, p in enumerate(PL):
            m = h3["by_platform"][p]
            if not m.get("k"):
                continue
            xo = 1 + (i - 1) * 0.06
            ax.plot([0, xo], [1, m["OR"]], color=PLATFORM_COLORS[p], lw=2.4, marker="o")
            ax.vlines(xo, m["lo"], m["hi"], color=PLATFORM_COLORS[p], lw=1.4)
        ax.axhline(1, color=INK2, ls="--", lw=1)
        ax.set_xticks([0, 1], ["before", "after"])
        ax.set_xlim(-0.2, 1.3)
        ax.set_yscale("log")
        log_ticks(ax, "y")
        ax.set_ylabel("index (OR, before = 1)")
        ax.set_title(f"{SOURCE_NAMES[src]} – {MNAME[src]}\np Q = {h3['p_Q']:.3g}: "
                     + ", ".join(f"{p} {h3['by_platform'][p]['OR']:.2f}" for p in PL), fontsize=10.5)
        ax = row[1]
        e = E(src).dropna(subset=["OR"])
        shared = [ev for ev in EVENT_ORDER if e.loc[e["event"] == ev, "platform"].nunique() >= 2]
        pos = {ev: i for i, ev in enumerate(shared)}
        for off, p in zip(np.linspace(-0.22, 0.22, len(PL)), PL):
            g = e[(e["platform"] == p) & e["event"].isin(shared)]
            xx = g["event"].map(pos) + off
            ax.vlines(xx, g["lo"], g["hi"], color=PLATFORM_COLORS[p], lw=1.6)
            ax.scatter(xx, g["OR"], s=50, color=PLATFORM_COLORS[p], zorder=3, edgecolor="white")
        ax.axhline(1, color=INK2, ls="--", lw=1)
        ax.set_yscale("log")
        log_ticks(ax, "y")
        ax.set_xticks(range(len(shared)), [LBL[ev] for ev in shared], fontsize=8.5, rotation=30, ha="right")
        ax.set_ylabel("OR after vs before")
        ax.set_title(f"The same events side by side\np Q balanced panel ({len(h3['common_events'])} events) = "
                     f"{h3['p_Q_panel']:.3g}; Wald after×platform = {h3['p_wald']:.3g}", fontsize=10.5)
    platform_legend(fig, top=0.94)
    savefig(fig, "fig_h3_en")


# ------------------------------------------------------------------ 7. words, word cloud
def barh(ax, labels, values, color, title, xlabel, notes=None):
    ax.barh(labels[::-1], values[::-1], color=color, height=0.65)
    if notes is not None:
        for yi, (v, n) in enumerate(zip(values[::-1], notes[::-1])):
            ax.text(v, yi, f" {n}", va="center", color=INK2, fontsize=7.5)
    ax.margins(x=0.25)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.tick_params(axis="y", labelsize=8.5)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel(xlabel)


def fig_words(top_n=15):
    fig, axes = plt.subplots(1, len(PL), figsize=(6.5 * len(PL), 0.33 * top_n + 1.4))
    for ax, p in zip(axes, PL):
        lo_ = R["q1a"]["distinctive"][p][:top_n]
        barh(ax, [w for w, *_ in lo_], [z for *_, z in lo_], PLATFORM_COLORS[p], f"{p}: words distinguishing hate",
             "z (log-odds)", notes=[f"{int(a)}/{int(b)}" for _, a, b, _ in lo_])
    plt.tight_layout()
    savefig(fig, "fig_words_en")


HATE_SHADES = ["#7c2d12", "#9a3412", "#c2410c", "#ea580c", "#52514e"]


def fig_cloud():
    from wordcloud import WordCloud
    freq = dict(json.loads((SRC / "cloud_freq.json").read_text(encoding="utf-8")))
    wc = WordCloud(width=1800, height=900, background_color="white", max_words=150, prefer_horizontal=0.95,
                   font_path=font_manager.findfont("DejaVu Sans"), random_state=0, margin=4,
                   color_func=lambda *a, random_state=None, **k: random_state.choice(HATE_SHADES)
                   ).generate_from_frequencies(freq)
    fig, ax = plt.subplots(figsize=(15, 7.5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title(f"Most frequent words in hate toward migrants – all platforms together "
                 f"({R['q1a']['n_hate_migrant']:,} comments, lemmas without stop words)")
    plt.tight_layout()
    savefig(fig, "fig_cloud_en", dpi=110)


# ------------------------------------------------------------------ 8. targets (fig_targets_en)
TARGET_NAMES = {"Ukrainians": "Ukrainians", "Muslims / Arabs": "Muslims / Arabs / Middle East",
                "Africans": "Africans / Black people", "migrants in general": "Migrants / refugees",
                "no group named": "no group named"}


def heat(ax, tab, title):
    vmax = np.nanmax(tab.values)
    ax.imshow(tab.values, cmap=BLUES, aspect="auto", vmin=0, vmax=vmax)
    for (i, j), v in np.ndenumerate(tab.values):
        if not np.isnan(v):
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=8, color="white" if v > 0.55 * vmax else INK)
    ax.set_xticks(range(tab.shape[1]), list(tab.columns), rotation=30, ha="right", fontsize=8.5)
    ax.set_yticks(range(len(tab)), tab.index, fontsize=8.5)
    ax.grid(False)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(title, fontsize=11)


def fig_targets():
    q = R["q1a"]
    cols = list(TARGET_NAMES)
    by_pl = pd.DataFrame(q["targets_by_platform"]).T.reindex(PL)[cols].rename(columns=TARGET_NAMES)
    by_pl.index = [f"{p} (n={q['targets_n']['platform'][p]:,})" for p in PL]
    evs = [ev for ev in EVENT_ORDER if ev in q["targets_by_event"]]
    by_ev = pd.DataFrame(q["targets_by_event"]).T.reindex(evs)[cols].rename(columns=TARGET_NAMES)
    by_ev.index = [f"{LBL[ev]} (n={q['targets_n']['event'][ev]:,})" for ev in evs]
    chg = pd.DataFrame(q["targets_change_pp"]).reindex(cols)
    fig, axes = plt.subplots(1, 3, figsize=(20, 0.36 * len(evs) + 2.2), gridspec_kw={"width_ratios": [0.7, 1, 0.8]})
    heat(axes[0], by_pl, "Who was targeted: per platform")
    heat(axes[1], by_ev, "Who was targeted: per event (platforms together)")
    ax = axes[2]
    yy = np.arange(len(cols))
    for k, p in enumerate(PL):
        ax.barh(yy + (k - 1) * 0.26, chg[p].values, 0.25, color=PLATFORM_COLORS[p], label=p)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(yy, [TARGET_NAMES[c] for c in cols], fontsize=8.5)
    ax.set_ylim(len(cols) - 0.5, -0.5)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_xlabel("change of share after the event [pp]")
    ax.legend(fontsize=8.5, loc="lower right")
    ax.set_title("Before → after: how the target of hate changes", fontsize=11)
    plt.tight_layout()
    savefig(fig, "fig_targets_en")


# ------------------------------------------------------------------ 9. authors (fig_authors_en) and likes (fig_likes_en)
def fig_authors():
    q = R["q1a"]
    ps = [p for p in ["wykop", "bluesky"] if p in q["lorenz"]]
    fig, axes = plt.subplots(1, len(ps), figsize=(6 * len(ps), 4.8), squeeze=False)
    for ax, p in zip(axes[0], ps):
        a = q["authors"][p]
        for key, name, c, gini in [("all", "all comments about migration", MUTED, a["gini_all"]),
                                   ("hate", "hate toward migrants", PLATFORM_COLORS[p], a["gini_hate"])]:
            x, y = q["lorenz"][p][key]
            ax.plot(np.array(x) * 100, np.array(y) * 100, color=c, lw=2.2, label=f"{name} (Gini {gini:.2f})")
        ax.plot([0, 100], [0, 100], color=INK2, ls=":", lw=1)
        ax.set_xlabel("% of authors (most active first)")
        ax.set_ylabel("% of comments")
        ax.grid(axis="x", visible=True)
        ax.legend(loc="lower right")
        ax.set_title(f"Concentration curve: {p}", color=PLATFORM_COLORS[p])
    plt.tight_layout()
    savefig(fig, "fig_authors_en")


def fig_likes():
    likes = pd.DataFrame(R["q1a"]["likes"]).T.reindex(PL)
    fig, axes = plt.subplots(1, 2, figsize=(14, 3.6))
    ax = axes[0]
    y = np.arange(len(PL))
    for yi, p in zip(y, PL):
        r = likes.loc[p]
        ax.hlines(yi, r["lo"], r["hi"], color=PLATFORM_COLORS[p], lw=2)
        ax.scatter(r["ratio"], yi, s=60, color=PLATFORM_COLORS[p], zorder=3)
        ax.text(r["hi"], yi, f"  ×{r['ratio']:.2f}", va="center", fontsize=9, color=INK2)
    ax.axvline(1, color=INK2, ls="--", lw=1)
    ax.set_xscale("log")
    ax.set_xlim(0.5, 2)
    log_ticks(ax, "x")
    ax.set_yticks(y, PL)
    ax.invert_yaxis()
    ax.grid(axis="x", visible=True)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("mean likes: hate / non-hate (NB model)")
    ax.set_title("How many more likes does hate get?")
    ax = axes[1]
    w = 0.36
    ax.bar(y - w / 2, 100 * likes["pct1_other"], width=w, color=[PLATFORM_COLORS[p] for p in PL], alpha=0.4, label="non-hate")
    ax.bar(y + w / 2, 100 * likes["pct1_hate"], width=w, color=[PLATFORM_COLORS[p] for p in PL], label="hate")
    ax.set_xticks(y, PL)
    ax.set_ylabel("% of comments with ≥ 1 like")
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color="#2a78d6", alpha=0.4), plt.Rectangle((0, 0), 1, 1, color="#2a78d6")],
              labels=["non-hate", "hate"], fontsize=8, loc="upper left")
    ax.set_title("Non-hate (light) vs hate (dark)")
    plt.tight_layout()
    savefig(fig, "fig_likes_en")


# ------------------------------------------------------------------ 10. gold standard (fig_gold_en)
def fig_gold():
    cm = pd.read_csv(GOLD / "hate_gemini_vs_models.csv", encoding="utf-8-sig")
    cm["zakres"] = cm["zakres"].replace({"wspólny podzbiór": "overall"})
    lm = pd.read_csv(GOLD / "llm_metrics.csv", encoding="utf-8-sig")
    lm = lm[lm["wariant"] == "Gemini + słownik"].replace({"zakres": {"ogółem": "overall"}})
    scopes = ["overall", "wykop", "bluesky", "youtube"]
    sname = {"overall": "overall", "wykop": "Wykop", "bluesky": "Bluesky", "youtube": "YouTube"}
    methods = [("HerBERT-HS", "HerBERT + dictionary", "#2a78d6"), ("Polbert-CB", "Polish BERT (cyberbullying)", "#7fb0ea"),
               ("Gemini + słownik", "Gemini + dictionary", "#eb6834"), ("RoBERTa-BAN-PL", "RoBERTa (BAN-PL)", "#1baf7a"),
               ("sam słownik", "dictionary only", "#8a8984")]
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.6), gridspec_kw={"width_ratios": [3, 1.3]})
    w = 0.8 / len(methods)
    for i, (m, lab, col) in enumerate(methods):
        e = cm[cm["metoda"] == m].set_index("zakres").reindex(scopes)
        x = np.arange(len(scopes)) + (i - (len(methods) - 1) / 2) * w
        axes[0].bar(x, e["f1"], w * 0.92, color=col, label=lab)
        for xi, v in zip(x, e["f1"]):
            axes[0].text(xi, v + 0.015, f"{v:.2f}", ha="center", fontsize=7, color=INK2)
    n0 = cm[cm["metoda"] == methods[0][0]].set_index("zakres")["n"]
    axes[0].set_xticks(range(len(scopes)), [f"{sname[s]}\n(n={int(n0[s])})" for s in scopes])
    axes[0].set_ylim(0, 1.12)
    axes[0].set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    axes[0].set_ylabel("F1 (hate)")
    axes[0].set_title("Label hate: F1 on the gold standard (same 600 comments)")
    axes[0].legend(ncol=5, fontsize=8, loc="upper left")
    t = lm[lm["zakres"].isin(scopes)].pivot_table(index="zakres", columns="etykieta", values="f1").reindex(scopes)
    y = np.arange(len(scopes))
    axes[1].barh(y - 0.2, t["hate"], 0.38, color="#eb6834", label="hate")
    axes[1].barh(y + 0.2, t["hate_migrant"], 0.38, color="#c2410c", label="hate_migrant")
    for yi, a, b in zip(y, t["hate"], t["hate_migrant"]):
        axes[1].text(a + 0.01, yi - 0.2, f"{a:.2f}", va="center", fontsize=7, color=INK2)
        axes[1].text(b + 0.01, yi + 0.2, f"{b:.2f}", va="center", fontsize=7, color=INK2)
    axes[1].set_yticks(y, [sname[s] for s in scopes])
    axes[1].invert_yaxis()
    axes[1].set_xlim(0, 1)
    axes[1].set_xlabel("F1")
    axes[1].grid(axis="x", visible=True)
    axes[1].grid(axis="y", visible=False)
    axes[1].set_title("Gemini + dictionary: F1 on the gold standard")
    axes[1].legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2)
    plt.tight_layout()
    savefig(fig, "fig_gold_en")


# ------------------------------------------------------------------ 11. HerBERT vs Gemini (fig_herbert_en)
def fig_herbert():
    g_ = EFF[EFF.measure == "hate"].set_index("cell")
    h_ = EFF[EFF.measure == "hate_herbert"].set_index("cell")
    both = g_[["OR", "sig", "platform"]].join(h_[["OR", "sig"]], rsuffix="_hb", how="inner").dropna(subset=["OR", "OR_hb"])
    hv = R["herbert_vs_gemini"]
    fig, ax = plt.subplots(figsize=(5.6, 5.2))
    for p in PL:
        b_ = both[both.platform == p]
        sg = b_["sig"].astype(bool) | b_["sig_hb"].astype(bool)
        ax.scatter(b_.loc[~sg, "OR"], b_.loc[~sg, "OR_hb"], s=40, facecolor="white", edgecolor=PLATFORM_COLORS[p], lw=1.4)
        ax.scatter(b_.loc[sg, "OR"], b_.loc[sg, "OR_hb"], s=50, color=PLATFORM_COLORS[p], edgecolor="white", lw=0.6, label=p)
    ax.plot([0.2, 9], [0.2, 9], ls="--", color=INK2, lw=1)
    ax.axhline(1, color=MUTED, lw=0.8, ls=":")
    ax.axvline(1, color=MUTED, lw=0.8, ls=":")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.2, 9)
    ax.set_ylim(0.2, 9)
    log_ticks(ax, "x")
    log_ticks(ax, "y")
    ax.grid(axis="x", visible=True)
    ax.set_xlabel("OR after vs before, hate (Gemini)")
    ax.set_ylabel("OR after vs before, hate (HerBERT)")
    ax.set_title(f"{hv['cells']} cells: r = {hv['pearson_logOR']:.2f}, same direction {100 * hv['same_direction']:.0f}%",
                 fontsize=11)
    ax.legend(loc="upper left", title="filled = significant\nwith either method", title_fontsize=8, fontsize=9)
    plt.tight_layout()
    savefig(fig, "fig_herbert_en")


# ------------------------------------------------------------------ 12. features of general hate (ha_2_profile, ha_4_logit)
HA_RC = {"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 11,
         "axes.titleweight": "bold", "font.size": 9, "axes.grid": False, "axes.titlelocation": "center",
         "axes.edgecolor": "black", "axes.labelcolor": "black", "xtick.color": "black", "ytick.color": "black",
         "legend.frameon": False}
HATE_C, NON_C, INK_HA = "#b4381f", "#9aa3ad", "#222222"
GROUPS = {"Language": ["profanity", "insults", "dehumanising words", "exclusion calls", "violence"],
          "Form": ["exclamation mark (!)", "question mark (?)", "CAPS LOCK", "emoji", "short (≤ 10 words)", "long (> 50 words)"],
          "Addressee": ["addressing the reader (you)", "“we / us”", "“they / them”"],
          "Groups": ["Ukrainians", "migrants (general)", "Muslims / Arabs / Africans", "Russians", "Poles / Poland",
                     "politicians / parties", "ideological labels"]}


def fig_profile():
    prof = R["q1b"]["profile"]
    order = [f for g in GROUPS.values() for f in g]
    with plt.rc_context(HA_RC):
        fig, axes = plt.subplots(1, len(PL), figsize=(4.0 * len(PL), 0.33 * len(order) + 1.2), sharey=True)
        y = np.arange(len(order))[::-1]
        for ax, p in zip(axes, PL):
            h = np.array([prof[p]["True"][f] for f in order])
            n = np.array([prof[p]["False"][f] for f in order])
            ax.hlines(y, np.minimum(h, n), np.maximum(h, n), color="#d6d6d6", lw=2)
            ax.scatter(n, y, color=NON_C, s=22, label="non-hate", zorder=3)
            ax.scatter(h, y, color=HATE_C, s=22, label="hate", zorder=3)
            ax.set_yticks(y, order)
            ax.set_title(p, color=PLATFORM_COLORS[p])
            ax.set_xlabel("% of comments with the feature")
            ax.grid(axis="x", color="#eeeeee")
            cut = len(order)
            for g in list(GROUPS)[:-1]:
                cut -= len(GROUPS[g])
                ax.axhline(cut - 0.5, color="#cccccc", lw=0.6)
        axes[0].legend(loc="lower right", frameon=False)
        fig.suptitle("How often hateful and non-hateful comments have each feature", fontweight="bold", y=1.0)
        plt.tight_layout()
        fig.savefig(OUT / "ha_2_profile.png", dpi=220, bbox_inches="tight", facecolor="white")
        plt.close(fig)
    print("saved ha_2_profile")


def fig_logit():
    lg = R["q1b"]["logit"]
    o = pd.DataFrame(lg).T.drop(index=[k for k in lg if k.startswith("log(")]).astype(float).sort_values("OR")
    with plt.rc_context(HA_RC):
        fig, ax = plt.subplots(figsize=(6.2, 0.3 * len(o) + 1))
        y = np.arange(len(o))
        c = [HATE_C if lo > 1 else ("#2f6db3" if hi < 1 else NON_C) for lo, hi in zip(o["lo"], o["hi"])]
        ax.hlines(y, o["lo"], o["hi"], color=c, lw=2)
        ax.scatter(o["OR"], y, color=c, s=24, zorder=3)
        ax.axvline(1, color=INK_HA, ls="--", lw=0.8)
        ax.set_xscale("log")
        ax.set_xticks([0.5, 0.75, 1, 1.5, 2, 3, 5, 10], ["0.5", "0.75", "1", "1.5", "2", "3", "5", "10"])
        ax.set_xlim(0.5, 14)
        ax.minorticks_off()
        ax.set_yticks(y, o.index)
        for yi, (v, hi) in enumerate(zip(o["OR"], o["hi"])):
            ax.text(hi * 1.05, yi, f"{v:.2f}", va="center", fontsize=7.5, color=INK_HA)
        ax.set_xlabel("adjusted odds ratio of hate (log scale)")
        ax.set_title("Which features are associated with hate?\n(logistic regression, 95% CI, model-labelled comments)")
        fig.savefig(OUT / "ha_4_logit.png", dpi=220, bbox_inches="tight", facecolor="white")
        plt.close(fig)
    print("saved ha_4_logit")


if __name__ == "__main__":
    fig_gold()
    fig_heatmap()
    fig_pooled()
    fig_herbert()
    fig_decomp()
    fig_daily(top_events(3))
    fig_h2("hate_migrant")
    fig_h3()
    fig_cloud()
    fig_words()
    fig_targets()
    fig_authors()
    fig_likes()
    fig_profile()
    fig_logit()
    print("ALL FIGURES DONE")
