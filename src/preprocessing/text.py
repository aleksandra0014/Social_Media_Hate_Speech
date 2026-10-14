"""Regexes and helpers shared by the filter and clean steps (ported from 01_bluesky_EDA, section 10)."""
import re

import emoji

# Masked placeholders written by the collectors ([link], @[user], [email], [phone]) plus raw links/domains.
LINK_RE = re.compile(
    r'\[link\]|https?://\S+|www\.\S+'
    r'|\b[\w.-]+\.(?:pl|com|org|net|eu|be|social|app|io|tv|info|gov|uk|de|me|ly|news|fun)\b/?\S*',
    re.I,
)
USER_RE = re.compile(r'@\[user\]|(?<![\w@])@[\w.-]+')
PLACEHOLDER_RE = re.compile(r'\[email\]|\[phone\]')
HASHTAG_RE = re.compile(r'#(\w+)')
WORD_RE = re.compile(r'[^\W\d_]+')
# Emoji leftovers the emoji package does not cover on their own: ZWJ, variation selectors, keycap.
EMOJI_EXTRA_RE = re.compile('[‍︎️⃣]')
SPACES_RE = re.compile(r'[ \t ]+')
NEWLINES_RE = re.compile(r'\s*\n\s*')


def remove_emoji(text):
    return EMOJI_EXTRA_RE.sub('', emoji.replace_emoji(text, replace=' '))


def has_emoji(text):
    return emoji.emoji_count(text) > 0


def strip_noise(text):
    """Text without links, mentions, placeholders and hashtags; used for word counts and language detection."""
    text = USER_RE.sub(' ', text)      # before LINK_RE, so '@jan.bsky.social' is not eaten as a domain
    text = LINK_RE.sub(' ', text)
    text = PLACEHOLDER_RE.sub(' ', text)
    return HASHTAG_RE.sub(' ', text)


def letter_words(text):
    return WORD_RE.findall(strip_noise(text))


def normalize_whitespace(text):
    text = SPACES_RE.sub(' ', text)
    text = NEWLINES_RE.sub('\n', text)
    return text.strip()


def normalize_for_dedup(text):
    """Key for duplicate detection: letters/digits only, lowercased."""
    text = PLACEHOLDER_RE.sub(' ', LINK_RE.sub(' ', USER_RE.sub(' ', text)))
    text = remove_emoji(HASHTAG_RE.sub(r'\1', text)).lower()
    return ' '.join(re.findall(r'\w+', text))
