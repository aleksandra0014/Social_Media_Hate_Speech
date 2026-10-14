"""Step 1: decide which texts to drop and why (logic of text_quality from 01_bluesky_EDA)."""
import pandas as pd

from .lang import polish_confidence
from .text import has_emoji, letter_words, normalize_for_dedup, remove_emoji, strip_noise

NO_TEXT = 'no_text'            # only links / mentions / numbers / punctuation
EMOJI_ONLY = 'emoji_only'
VERY_SHORT = 'very_short'      # fewer than min_words letter-words
NON_POLISH = 'non_polish'      # lingua confidence for Polish below threshold
DUPLICATE = 'duplicate'        # same normalised text earlier in the same file


def rule_reason(text, min_words):
    """Reason from the cheap rules, or None if the text needs a language check."""
    words = letter_words(text)
    if not words:
        return EMOJI_ONLY if has_emoji(text) else NO_TEXT
    if len(words) < min_words:
        return VERY_SHORT
    return None


def assign_drop_reason(df, cfg, detector):
    """Series aligned with df: drop reason, or None for rows that stay."""
    texts = df['text'].fillna('').astype(str)
    reasons = texts.map(lambda t: rule_reason(t, cfg['min_words']))

    todo = reasons.isna()
    if todo.any():
        stripped = texts[todo].map(lambda t: remove_emoji(strip_noise(t)))
        conf = pd.Series(polish_confidence(detector, stripped), index=stripped.index)
        reasons[conf[conf < cfg['min_pl_confidence']].index] = NON_POLISH

    if cfg.get('drop_duplicates', True):
        kept = reasons.isna()
        order = df.loc[kept].sort_values('created_at', kind='stable').index
        keys = texts[order].map(normalize_for_dedup)
        reasons[keys[keys.duplicated()].index] = DUPLICATE

    return reasons


def split_frame(df, cfg, detector):
    """(kept, excluded) — excluded gets a drop_reason column in front."""
    reasons = assign_drop_reason(df, cfg, detector)
    kept = df[reasons.isna()]
    excluded = df[reasons.notna()].copy()
    excluded.insert(0, 'drop_reason', reasons[reasons.notna()])
    return kept, excluded
