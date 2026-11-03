#!/usr/bin/env python3
"""Test klasyfikacji migrant / hate / hate_migrant przez Groq / Gemini API na zbiorze gold.

Prompt (SYSTEM_PROMPT) to streszczenie docs/CODEBOOK.md; ten sam używa scripts/llm_classify.py.
wysyła paczki komentarzy do Groq (OpenAI-compatible API) lub Gemini (Google AI Studio),
mierzy czas, tokeny, zużycie zasobów lokalnych i limity API, a na końcu porównuje wynik z gold.

Klucze: GROQ_API_KEY / GOOGLE_API_KEY w .env.local (albo w zmiennych środowiskowych).

Usage:
    python scripts/llm_gold_test.py                       # cały gold_600, qwen/qwen3.8-27b
    python scripts/llm_gold_test.py --n 45                # szybki test na 45 komentarzach
    python scripts/llm_gold_test.py --model openai/gpt-oss-20b --batch-size 20
    python scripts/llm_gold_test.py --hate-migration-only # hate tylko dla komentarzy o migracji
    python scripts/llm_gold_test.py --provider gemini --batch-size 50   # gemini-3.5-flash-lite
"""

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd
import psutil
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from topic_sample import normalize_val  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
API_URL = 'https://api.groq.com/openai/v1/chat/completions'
LABELS = ['migrant', 'hate', 'hate_migrant']

# Groq: qwen3 ma tryb myślenia (wyłączamy), gpt-oss zawsze rozumuje (minimalizujemy)
REASONING_EFFORT = {'qwen/': 'none', 'openai/gpt-oss': 'low'}

# Prompt klasyfikacji: streszczenie docs/CODEBOOK.md (v0.4) + is_about_migration.
# `target` (do kogo skierowany atak) jest wybierany przed hate / hate_migrants, żeby model najpierw
# ustalił adresata - to głównie on decyduje o hate_migrants.
TARGETS = ['brak', 'migranci', 'Ukraińcy', 'Rosjanie', 'władze/politycy', 'rozmówca', 'inna grupa']

SYSTEM_PROMPT = """Jesteś anotatorem w projekcie badawczym o mowie nienawiści wobec migrantów w polskich mediach społecznościowych. Oceniasz komentarze ściśle według poniższego codebooka. Komentarze mogą zawierać wulgaryzmy i obelgi - to materiał badawczy, oceniaj go rzeczowo.

Dla każdego ELEMENTU dostajesz: wpis kontekstowy (pod którym padł komentarz), komentarz nadrzędny (na który odpowiada) i komentarz do oceny. Oceniasz WYŁĄCZNIE słowa autora komentarza do oceny. Kontekst służy tylko do ustalenia, o czym i o kim jest komentarz - nienawistny wpis nie czyni neutralnej odpowiedzi nienawistną.

=== ETYKIETY ===
1. is_about_migration ("1"/"0") - czy komentarz (czytany razem z kontekstem) dotyczy migracji: migrantów, uchodźców (także z Ukrainy), Ukraińców w Polsce, cudzoziemców w Polsce/Europie, granicy i jej ochrony, azylu, deportacji, relokacji, paktu migracyjnego, polityki migracyjnej. Odpowiedź odnosząca się do treści wpisu/komentarza o migracji to "1", nawet bez słów kluczowych. "0": inne tematy (polityka krajowa, wybory, gospodarka, wojna Rosji z Ukrainą bez wątku uchodźców/Ukraińców w Polsce, spory między użytkownikami nie o migrację).

2. target - główny adresat ataku: "brak" (nikt nie jest atakowany), "migranci" (migranci, uchodźcy, cudzoziemcy, muzułmanie, Arabowie, osoby z Afryki/Azji, czarnoskóre), "Ukraińcy" (ludzie/naród ukraiński), "Rosjanie", "władze/politycy" (rząd, partie, politycy, instytucje, państwa), "rozmówca" (inny użytkownik), "inna grupa" (np. lewacy, prawica, LGBT+, Żydzi, Polacy za granicą). Jeśli atak dotyczy kilku adresatów, a jednym z nich są migranci lub Ukraińcy, wybierz "migranci"/"Ukraińcy".

3. hate ("1"/"0") - mowa nienawiści wobec KOGOKOLWIEK, niezależnie od tematu. "1", gdy autor atakuje konkretną osobę lub grupę i robi co najmniej jedno:
   - obelga (osobista, polityczna, etniczna, rasowa, religijna, także zniekształcona): "idioto", "onuco", "lewaki", "ciapaki", "ścierwa";
   - dehumanizacja (zwierzęta, robactwo, choroba, śmieci, broń, najazd): "to bydło", "szarańcza", "dzicz", "najeźdźcy";
   - stereotyp / generalizacja negatywnej cechy na całą grupę: "oni tylko do socjalu", "u nich to normalne", "nie wszyscy, ale większość to...";
   - wykluczenie całej grupy (wydalić, izolować, odebrać prawa) lub jego pochwała: "niech wracają, skąd przyszli", "wywieźć wszystkich", "Polska dla Polaków";
   - przemoc: groźba, wezwanie, życzenie krzywdy lub aprobata, także wobec "nielegalnych": "na granicy powinni strzelać", "oby ich pozabijali";
   - kod / ironia / mem, gdy wrogość jest czytelna: "ubogacił kulturowo", "inżynierowie przyjechali".
   "0": brak ataku; wulgaryzm bez adresata ("kurwa, znowu to samo"); ostra, ale rzeczowa krytyka decyzji, ustawy, polityki, rządu czy państwa ("pakt to błąd", "granica musi być szczelna", "ten minister kłamie"); rzeczowa statystyka; relacja z doświadczenia bez uogólnienia; kontrmowa, która cytuje lub potępia cudzą nienawiść bez własnych wyzwisk; deportacja konkretnego sprawcy za czyn; tekst nieczytelny lub nie po polsku.

4. hate_migrants ("1"/"0") - "1" tylko gdy hate="1" i choć jeden atak jest skierowany do migrantów ZE WZGLĘDU NA POCHODZENIE, NARODOWOŚĆ, RASĘ, RELIGIĘ LUB STATUS migranta/uchodźcy.
   Migranci w tym badaniu: migranci, imigranci, uchodźcy, azylanci, osoby przekraczające granicę nielegalnie, cudzoziemcy w Polsce/Europie, UKRAIŃCY ZAWSZE (jako ludzie, naród, żołnierze, uchodźcy - w Polsce i w Ukrainie), muzułmanie, Arabowie, osoby z Afryki, czarnoskóre i "śniade", pracownicy z Azji, Gruzji, Ameryki Łacińskiej.
   NIE są migrantami (hejt wobec nich = hate "1", hate_migrants "0"): Rosjanie ("kacapy", "orki", "ruskie"), Polacy za granicą ("polonusi"), państwo i władze Ukrainy jako instytucje ("reżim Zełeńskiego"), Żydzi, władze obcych państw i UE, historyczne formacje (UPA, naziści) - dopóki autor nie przenosi wrogości na dzisiejszych Ukraińców, politycy, partie, użytkownicy, osoby LGBT+, kobiety.
   hate_migrants "0" także przy wyzwisku wobec konkretnego sprawcy za jego czyn, bez odwołania do pochodzenia ("bandyta, niech gnije").

=== ZASADY ===
- Wystarczy jeden fragment: jedno zdanie spełniające kryterium daje hate "1"; jedno takie zdanie o migrantach daje też hate_migrants "1", nawet gdy reszta atakuje polityków ("zdrajcy wpuszczają tę dzicz" = 1/1).
- Osoba czy grupa: krytyka czynu jednej osoby = 0/0; wyzwisko wobec niej = 1/0; uogólnienie na grupę ("typowe dla nich") lub wyzwisko etniczne = 1/1.
- Decyzja/państwo czy ludzie: rzeczowa krytyka rządu, paktu, państwa ukraińskiego = 0/0; wyzwiska wobec władz = 1/0; przeniesienie wrogości na ludzi ("...i Ukraińcy są tacy sami") = 1/1.
- OBELGA ETNICZNA wobec migrantów lub Ukraińców ("ukry", "ukropy", "ciapaci", "ciapaki", "brudasy", "kozojebcy", "muzole", "nachodźcy", "banderowcy" o dzisiejszych Ukraińcach, "śniadzi", "pigmentodatni") = ZAWSZE 1/1, także w życzliwym zdaniu ("ukry to spoko ludzie"). Wyjątek: autor przytacza obelgę, żeby ją skrytykować ("nie nazywaj ich ukrami") = 0/0.
- Pytania retoryczne liczą się jak twierdzenia ("czemu oni zawsze...?" z negatywnym uogólnieniem = 1/1; "popierasz wpuszczanie nachodźców?" = 1/1).
- Ironia: jeśli wyraża wrogość - oceniaj jak twierdzenie wprost; ironia wymierzona w rasistów bez wyzwisk = 0/0.
- Samo "wypierdalaj"/"won": jako odpowiedź do użytkownika = 1/0; bezpośrednio pod wpisem o migrantach lub przestępstwie migranta = 1/1; pod wpisem o polityku = 1/0.
- Zastrzeżenia ("nie jestem rasistą, ale...", "nie wszyscy, ale...") nie zmieniają oceny stereotypu.
- Nie zgaduj ukrytych intencji, oceniaj to, co jest w tekście. Przy wątpliwości wybierz najbardziej oczywiste odczytanie.
- Spójność: hate_migrants "1" wymaga hate "1" i is_about_migration "1". hate "1" przy target "brak" jest błędem.

=== PRZYKŁADY (komentarz -> is_about_migration / target / hate / hate_migrants) ===
- "Zamknąć granice, pakt to zdrada interesów Polski." -> 1 / brak / 0 / 0
- "Kolejni ciapaci na socjalu, a Polak haruje." -> 1 / migranci / 1 / 1
- (wpis o ataku nożem) "No i ubogacił kulturowo." -> 1 / migranci / 1 / 1
- "Z Afryki nie przyjadą inżynierowie, tylko agresja i niskie IQ." -> 1 / migranci / 1 / 1
- "Ukry się panoszą i jeszcze wymagają." -> 1 / Ukraińcy / 1 / 1
- "Szkoda tych ludzi, ale nie mogą się tu panoszyć i wymagać." -> 1 / Ukraińcy / 1 / 1
- "Za pobicie od razu deportacja." -> 1 / brak / 0 / 0
- "W 2025 r. deportowano o 300% więcej osób niż w 2023." -> 1 / brak / 0 / 0
- "Pani w sklepie z Ukrainy zawsze miła, pozdrawiam." -> 1 / brak / 0 / 0
- "Ci, co biją Ukraińców za akcent, to zwykłe bydlaki." -> 1 / inna grupa / 1 / 0
- "@[user]: won za Ural, ruski trollu." -> 0 / rozmówca / 1 / 0
- "Rozstrzelać tych kacapów." -> 0 / Rosjanie / 1 / 0
- "Zełenski to złodziej i błazen." -> 0 / władze/politycy / 1 / 0
- "Te ścierwa zdradzieckie z rządu powinny zostać wygnane." -> 0 / władze/politycy / 1 / 0
- "Rząd znowu podniósł podatki, masakra." -> 0 / brak / 0 / 0
- "Banderowcy i UPA odpowiadają za Wołyń, to trzeba rozliczyć." -> 0 / brak / 0 / 0

=== FORMAT ===
Zwróć WYŁĄCZNIE obiekt JSON {"results": [...]} z jednym obiektem na każdy ELEMENT, w tej samej kolejności:
{"index": 1, "is_about_migration": "1"|"0", "target": jedna z wartości target, "hate": "1"|"0", "hate_migrants": "1"|"0"}"""

HATE_MIGRATION_ONLY = ('\n\nDODATKOWA REGUŁA: jeśli is_about_migration = "0", wpisz hate "0" '
                       'i hate_migrants "0" (oceniamy hejt tylko w komentarzach o migracji).')

# Gemini: structured output - model nie może zwrócić innych pól ani wartości
RESPONSE_SCHEMA = {
    'type': 'OBJECT',
    'properties': {'results': {'type': 'ARRAY', 'items': {
        'type': 'OBJECT',
        'properties': {
            'index': {'type': 'INTEGER'},
            'is_about_migration': {'type': 'STRING', 'enum': ['0', '1']},
            'target': {'type': 'STRING', 'enum': TARGETS},
            'hate': {'type': 'STRING', 'enum': ['0', '1']},
            'hate_migrants': {'type': 'STRING', 'enum': ['0', '1']},
        },
        'required': ['index', 'is_about_migration', 'target', 'hate', 'hate_migrants'],
        'propertyOrdering': ['index', 'is_about_migration', 'target', 'hate', 'hate_migrants'],
    }}},
    'required': ['results'],
}


def parse_reset(s):
    """'1m26.4s' / '2.8s' / '350ms' -> sekundy."""
    if not s:
        return 0.0
    total = 0.0
    for num, unit in re.findall(r'([\d.]+)(ms|h|m|s)', s):
        total += float(num) * {'ms': 0.001, 's': 1, 'm': 60, 'h': 3600}[unit]
    return total


class Groq:
    def __init__(self, api_key, model, max_tokens):
        self.model = model
        self.max_tokens = max_tokens
        self.session = requests.Session()
        self.session.headers['Authorization'] = f'Bearer {api_key}'
        self.reasoning = next((v for k, v in REASONING_EFFORT.items() if model.startswith(k)), None)
        self.remaining_tokens = None
        self.reset_tokens_at = 0.0
        self.last_headers = {}
        self.wait_s = 0.0
        self.retries = 0
        self.usage = Counter()

    def _throttle(self, est_tokens):
        """Czeka, jeśli w bieżącym oknie minutowym zabraknie tokenów (limit TPM)."""
        if self.remaining_tokens is not None and self.remaining_tokens < est_tokens:
            delay = self.reset_tokens_at - time.time()
            if delay > 0:
                self.wait_s += delay
                time.sleep(delay)

    def chat(self, messages, est_tokens):
        body = {
            'model': self.model,
            'messages': messages,
            'temperature': 0,
            'seed': 1,
            'max_completion_tokens': self.max_tokens,
            'response_format': {'type': 'json_object'},
        }
        if self.reasoning:
            body['reasoning_effort'] = self.reasoning

        for attempt in range(8):
            self._throttle(est_tokens)
            r = self.session.post(API_URL, json=body, timeout=120)
            h = r.headers
            if 'x-ratelimit-remaining-tokens' in h:
                self.last_headers = {k: v for k, v in h.items() if k.lower().startswith('x-ratelimit')}
                self.remaining_tokens = int(h['x-ratelimit-remaining-tokens'])
                self.reset_tokens_at = time.time() + parse_reset(h.get('x-ratelimit-reset-tokens'))

            if r.status_code == 429 or r.status_code >= 500:
                delay = float(h.get('retry-after') or 0) or min(2 ** attempt, 60)
                if 'tokens per day' in r.text.lower() or 'requests per day' in r.text.lower():
                    raise RuntimeError(f'Wyczerpany dzienny limit: {r.text[:300]}')
                self.retries += 1
                self.wait_s += delay
                time.sleep(delay)
                continue
            if r.status_code == 400 and 'json_validate_failed' in r.text and attempt < 2:
                self.retries += 1
                continue
            r.raise_for_status()

            j = r.json()
            u = j.get('usage', {})
            for k in ['prompt_tokens', 'completion_tokens', 'total_tokens',
                      'queue_time', 'prompt_time', 'completion_time', 'total_time']:
                self.usage[k] += u.get(k) or 0
            self.usage['reasoning_tokens'] += (u.get('completion_tokens_details') or {}).get('reasoning_tokens') or 0
            self.usage['requests'] += 1
            return j['choices'][0]['message'].get('content') or ''
        raise RuntimeError('Przekroczono liczbę ponowień')


GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
GEMINI_SAFETY_OFF = [
    {'category': c, 'threshold': 'BLOCK_NONE'}
    for c in ['HARM_CATEGORY_HATE_SPEECH', 'HARM_CATEGORY_HARASSMENT',
              'HARM_CATEGORY_DANGEROUS_CONTENT', 'HARM_CATEGORY_SEXUALLY_EXPLICIT']
]


class Gemini:
    """Natywne API Gemini; free tier nie zwraca nagłówków limitów, więc throttling po --rpm."""

    def __init__(self, api_key, model, max_tokens, rpm):
        self.model = model
        self.max_tokens = max_tokens
        self.min_interval = 60.0 / rpm if rpm else 0.0
        self.session = requests.Session()
        self.session.headers['x-goog-api-key'] = api_key
        self.last_request = 0.0
        self.last_headers = {}
        self.wait_s = 0.0
        self.retries = 0
        self.usage = Counter()

    def _sleep(self, delay):
        self.wait_s += delay
        time.sleep(delay)

    def chat(self, messages, est_tokens=None):
        body = {
            'systemInstruction': {'parts': [{'text': messages[0]['content']}]},
            'contents': [{'role': 'user', 'parts': [{'text': messages[1]['content']}]}],
            'generationConfig': {
                'temperature': 0,
                'seed': 1,
                'maxOutputTokens': self.max_tokens,
                'responseMimeType': 'application/json',
                'responseSchema': RESPONSE_SCHEMA,
            },
            'safetySettings': GEMINI_SAFETY_OFF,
        }
        for attempt in range(8):
            delay = self.last_request + self.min_interval - time.time()
            if delay > 0:
                self._sleep(delay)
            self.last_request = time.time()
            r = self.session.post(GEMINI_URL.format(model=self.model), json=body, timeout=180)

            if r.status_code == 429 or r.status_code >= 500:
                if 'PerDay' in r.text:
                    raise RuntimeError(f'Wyczerpany dzienny limit: {r.text[:300]}')
                m = re.search(r'"retryDelay":\s*"([\d.]+)s"', r.text)
                self.retries += 1
                self._sleep(float(m.group(1)) + 1 if m else min(2 ** (attempt + 1), 60))
                continue
            r.raise_for_status()

            j = r.json()
            u = j.get('usageMetadata', {})
            self.usage['prompt_tokens'] += u.get('promptTokenCount') or 0
            self.usage['completion_tokens'] += (u.get('candidatesTokenCount') or 0) + (u.get('thoughtsTokenCount') or 0)
            self.usage['reasoning_tokens'] += u.get('thoughtsTokenCount') or 0
            self.usage['total_tokens'] += u.get('totalTokenCount') or 0
            self.usage['requests'] += 1
            cand = (j.get('candidates') or [{}])[0]
            if cand.get('finishReason') not in (None, 'STOP'):
                print(f"  uwaga: finishReason={cand.get('finishReason')}")
            return ''.join(p.get('text', '') for p in cand.get('content', {}).get('parts', []) if not p.get('thought'))
        raise RuntimeError('Przekroczono liczbę ponowień')


def make_messages(batch, hate_all=True):
    """hate_all=False: hate oceniany tylko w komentarzach o migracji (stare zachowanie)."""
    items = [
        f"--- ELEMENT {it['index']} ---\n"
        f"Wpis kontekstowy: {it['post_context'] or '(brak)'}\n"
        f"Komentarz nadrzędny (na który odpowiada): {it['parent_context'] or '(brak - odpowiedź na wpis)'}\n"
        f"Komentarz do oceny: {it['text'][:1000]}"
        for it in batch
    ]
    return [
        {'role': 'system', 'content': SYSTEM_PROMPT + ('' if hate_all else HATE_MIGRATION_ONLY)},
        {'role': 'user', 'content': f'Oceń {len(batch)} komentarzy:\n\n' + '\n\n'.join(items)},
    ]


def parse_results(content, n):
    """Zwraca dla każdego elementu (is_about_migration, hate, hate_migrants, target) albo None."""
    try:
        parsed = json.loads(content)
    except Exception:
        return [None] * n
    if isinstance(parsed, dict):
        parsed = next((v for v in parsed.values() if isinstance(v, list)), [])
    by_index = {}
    for i, it in enumerate(parsed if isinstance(parsed, list) else []):
        if isinstance(it, dict):
            by_index.setdefault(int(it.get('index', i + 1)) if str(it.get('index', '')).isdigit() else i + 1, it)
    out = []
    for i in range(1, n + 1):
        it = by_index.get(i, {})
        vals = [normalize_val(it.get(k)) for k in ['is_about_migration', 'hate', 'hate_migrants']]
        if None in vals:
            out.append(None)
            continue
        mig, hate, hate_mig = (int(v) for v in vals)
        # dozwolone pary hate/hate_migrants: 0/0, 1/0, 1/1 (codebook pkt 3); hate_migrants=1 => temat migracji
        if hate_mig:
            hate, mig = 1, 1
        out.append((mig, hate, hate_mig, str(it.get('target') or '')))
    return out


def metrics(y_true, y_pred):
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    n = tp + tn + fp + fn
    po = (tp + tn) / n if n else 0.0
    pe = ((tp + fp) * (tp + fn) + (tn + fn) * (tn + fp)) / n ** 2 if n else 0.0
    kappa = (po - pe) / (1 - pe) if pe < 1 else 0.0
    return {'n': n, 'acc': round(po, 3), 'precision': round(p, 3), 'recall': round(r, 3),
            'f1': round(f1, 3), 'kappa': round(kappa, 3), 'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default=str(ROOT / 'data' / 'gold_600_ollama.csv'))
    ap.add_argument('--provider', choices=['groq', 'gemini'], default='groq')
    ap.add_argument('--model', default=None,
                    help='Domyślnie: qwen/qwen3.8-27b (groq), gemini-3.5-flash-lite (gemini)')
    ap.add_argument('--rpm', type=int, default=10, help='Gemini: limit zapytań/min (free tier ~10)')
    ap.add_argument('--rpd', type=int, default=500, help='Gemini: limit zapytań/dzień do prognozy (free tier ~500)')
    ap.add_argument('--batch-size', type=int, default=15)
    ap.add_argument('--n', type=int, default=0, help='Liczba komentarzy (0 = wszystkie)')
    ap.add_argument('--max-tokens', type=int, default=None,
                    help='Limit tokenów odpowiedzi na paczkę (domyślnie max(2048, 80 * batch-size))')
    ap.add_argument('--hate-migration-only', dest='hate_all', action='store_false',
                    help='Oceniaj hate tylko w komentarzach o migracji (domyślnie: we wszystkich, jak w codebooku)')
    ap.add_argument('--out-dir', default=str(ROOT / 'reports' / 'groq_test'))
    args = ap.parse_args()

    load_dotenv(ROOT / '.env.local')
    load_dotenv(ROOT / '.env')
    key_name = 'GROQ_API_KEY' if args.provider == 'groq' else 'GOOGLE_API_KEY'
    api_key = os.environ.get(key_name)
    if not api_key:
        sys.exit(f'Brak {key_name} w .env.local / środowisku')
    if args.max_tokens is None:
        args.max_tokens = max(2048, 80 * args.batch_size)
    if args.model is None:
        args.model = 'qwen/qwen3.8-27b' if args.provider == 'groq' else 'gemini-3.5-flash-lite'

    df = pd.read_csv(args.input).fillna({'context_post': '', 'context_parent': '', 'context_quote': ''})
    if args.n:
        df = df.head(args.n)
    print(f'Model: {args.model} | komentarzy: {len(df)} | batch: {args.batch_size} | hate_all: {args.hate_all}')

    if args.provider == 'groq':
        client = Groq(api_key, args.model, args.max_tokens)
    else:
        client = Gemini(api_key, args.model, args.max_tokens, args.rpm)
    proc = psutil.Process()
    proc.cpu_percent(None)
    cpu0, peak_rss = proc.cpu_times(), proc.memory_info().rss
    preds, errors, t0 = {}, 0, time.time()
    est_tokens = None

    try:
        for start in range(0, len(df), args.batch_size):
            chunk = df.iloc[start:start + args.batch_size]
            batch = []
            for idx, (_, row) in enumerate(chunk.iterrows(), start=1):
                post_ctx = row.context_post.strip().replace('\n', ' ')[:300]
                if row.context_quote.strip():
                    post_ctx += f" [cytowany wpis: {row.context_quote.strip().replace(chr(10), ' ')[:300]}]"
                batch.append({
                    'index': idx,
                    'post_context': post_ctx,
                    'parent_context': row.context_parent.strip().replace('\n', ' ')[:300],
                    'text': row.text,
                })
            messages = make_messages(batch, args.hate_all)
            # pierwsza paczka: zgrubnie ~3 znaki/token; potem średnia z rzeczywistego zużycia
            if est_tokens is None:
                est_tokens = sum(len(m['content']) for m in messages) // 3 + 400

            t_b = time.time()
            try:
                labels = parse_results(client.chat(messages, est_tokens), len(batch))
            except RuntimeError as e:
                print(f'STOP: {e}')
                break
            except Exception as e:
                print(f'  błąd API w paczce od {start + 1}: {str(e)[:200]}')
                labels = [None] * len(batch)
            dt = time.time() - t_b
            if client.usage['requests']:
                est_tokens = int(client.usage['total_tokens'] / client.usage['requests'] * 1.1)

            for (_, row), lab in zip(chunk.iterrows(), labels):
                if lab is None:
                    errors += 1
                else:
                    preds[row.item_id] = lab[:3]
            peak_rss = max(peak_rss, proc.memory_info().rss)
            print(f'{start + len(chunk)}/{len(df)} | paczka {dt:.1f}s | błędy {errors} | '
                  f'tokeny łącznie {client.usage["total_tokens"]} | czekanie na limit {client.wait_s:.0f}s',
                  flush=True)
    except KeyboardInterrupt:
        print('\nPrzerwano - zapisuję częściowe wyniki.')

    wall = time.time() - t0
    cpu1 = proc.cpu_times()

    pred_df = pd.DataFrame([(k, *v) for k, v in preds.items()],
                           columns=['item_id', 'pred_migrant', 'pred_hate', 'pred_hate_migrant'])
    res = df.merge(pred_df, on='item_id', how='left')

    evald = res.dropna(subset=['pred_migrant'])
    report = {}
    for lab in LABELS:
        report[lab] = metrics(evald[lab].astype(int), evald[f'pred_{lab}'].astype(int))
    sub = evald[evald.migrant == 1]
    report['hate | gold migrant=1'] = metrics(sub.hate.astype(int), sub.pred_hate.astype(int))

    n_done = len(evald)
    u = client.usage
    summary = {
        'model': args.model,
        'batch_size': args.batch_size,
        'hate_all': args.hate_all,
        'comments': len(df),
        'classified': n_done,
        'parse_or_api_errors': errors,
        'wall_time_s': round(wall, 1),
        's_per_comment': round(wall / max(n_done, 1), 3),
        'comments_per_min': round(n_done / wall * 60, 1) if wall else None,
        'rate_limit_wait_s': round(client.wait_s, 1),
        'retries': client.retries,
        'groq_requests': u['requests'],
        'tokens': {k: u[k] for k in ['prompt_tokens', 'completion_tokens', 'reasoning_tokens', 'total_tokens']},
        'tokens_per_comment': round(u['total_tokens'] / max(n_done, 1), 1),
        'groq_server_time_s': {k: round(u[k], 2) for k in ['queue_time', 'prompt_time', 'completion_time', 'total_time']},
        'local_cpu_time_s': round((cpu1.user - cpu0.user) + (cpu1.system - cpu0.system), 2),
        'local_peak_rss_mb': round(peak_rss / 2 ** 20, 1),
        'last_rate_limit_headers': client.last_headers,
        'metrics': report,
    }
    if n_done and args.provider == 'groq':
        # Prognoza dla dużych zbiorów przy limitach free tier (8000 TPM, 1000 RPD)
        tpm = int(client.last_headers.get('x-ratelimit-limit-tokens', 8000))
        rpd = int(client.last_headers.get('x-ratelimit-limit-requests', 1000))
        tpc = u['total_tokens'] / n_done
        summary['capacity_estimate'] = {
            'max_comments_per_min_by_TPM': round(tpm / tpc, 1),
            'max_comments_per_day_by_RPD': rpd * args.batch_size,
            'note': 'dzienny limit tokenów (TPD) nie jest zwracany w nagłówkach - patrz console.groq.com/settings/limits',
        }
    elif n_done:
        summary['capacity_estimate'] = {
            'max_comments_per_min_by_RPM': args.rpm * args.batch_size,
            'max_comments_per_day_by_RPD': args.rpd * args.batch_size,
            'note': 'limity z --rpm/--rpd; aktualne wartości: aistudio.google.com -> Usage & limits',
        }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{args.model.replace('/', '_')}_b{args.batch_size}{'' if args.hate_all else '_hatemig'}"
    res.to_csv(out_dir / f'pred_{tag}.csv', index=False, encoding='utf-8-sig')
    (out_dir / f'summary_{tag}.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    print('\n--- PODSUMOWANIE ---')
    print(f"Sklasyfikowano {n_done}/{len(df)} | błędy {errors} | czas {wall:.0f}s "
          f"({summary['s_per_comment']}s/komentarz, {summary['comments_per_min']}/min)")
    print(f"Czekanie na limity API: {client.wait_s:.0f}s | ponowienia: {client.retries}")
    print(f"Tokeny: {summary['tokens']} (~{summary['tokens_per_comment']}/komentarz)")
    if args.provider == 'groq':
        print(f"Czas po stronie Groq: {summary['groq_server_time_s']}")
    print(f"Lokalnie: CPU {summary['local_cpu_time_s']}s, peak RAM {summary['local_peak_rss_mb']} MB")
    if 'capacity_estimate' in summary:
        print(f"Prognoza free tier: {summary['capacity_estimate']}")
    print('\nMetryki vs gold:')
    print(pd.DataFrame(report).T.to_string())
    print(f'\nZapisano: {out_dir / f"pred_{tag}.csv"}, {out_dir / f"summary_{tag}.json"}')


if __name__ == '__main__':
    main()
