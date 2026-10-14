"""Step 2: strip emoji, links and mentions from texts that survived the filter."""
from .text import HASHTAG_RE, LINK_RE, PLACEHOLDER_RE, USER_RE, normalize_whitespace, remove_emoji


def clean_text(text):
    text = USER_RE.sub(' ', text)
    text = LINK_RE.sub(' ', text)
    text = PLACEHOLDER_RE.sub(' ', text)
    text = HASHTAG_RE.sub(r'\1', text)     # '#migracja' -> 'migracja'
    text = remove_emoji(text)
    return normalize_whitespace(text)


def clean_frame(df):
    """Keep the original as text_raw, overwrite text with the cleaned version."""
    df = df.copy()
    df['text_raw'] = df['text']
    df['text'] = df['text'].fillna('').astype(str).map(clean_text)
    return df
