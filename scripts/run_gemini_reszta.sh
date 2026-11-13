#!/usr/bin/env bash
# Gemini: klasyfikacja wydarzeń (Wykop, Bluesky), których Ola jeszcze nie sklasyfikowała.
# Uruchom z głównego folderu projektu:   bash scripts/run_gemini_reszta.sh
# Można uruchamiać wiele razy (np. następnego dnia po limicie) - dokańcza tylko brakujące komentarze.
set -u
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && source .venv/bin/activate

grep -q "llm_classify" dvc.yaml 2>/dev/null || { echo "Brak etapu llm w dvc.yaml - przejdź najpierw na gałąź gemini-reszta (z origin/new-events-bluesky)."; exit 1; }
grep -qs '^GOOGLE_API_KEY=..*' .env.local || { echo "Brak GOOGLE_API_KEY w pliku .env.local."; exit 1; }

RUNS="wykop:2024-04-10_Pakt_Azyl_PE wykop:2024-05-28_Atak_Zolnierz_Granica wykop:2024-06-06_Smierc_Zolnierza
wykop:2024-09-08_Bojka_Srem wykop:2024-10-12_Strategia_Migracyjna wykop:2025-10-15_Dezinformacja_Krakow
wykop:2026-07-30_Ceuta_Masowe_Przekroczenie wykop:2026-08-15_Atak_Kamienna_Gora
bluesky:2024-04-10_Pakt_Azyl_PE bluesky:2024-06-06_Smierc_Zolnierza bluesky:2024-09-08_Bojka_Srem
bluesky:2024-10-12_Strategia_Migracyjna bluesky:2025-10-15_Dezinformacja_Krakow
bluesky:2026-07-30_Ceuta_Masowe_Przekroczenie bluesky:2026-08-15_Atak_Kamienna_Gora"

# 1) dopisz brakujące przebiegi do params.yaml (sekcja llm.runs jest na końcu pliku)
python - $RUNS <<'PY' || exit 1
import sys
lines = open('params.yaml', encoding='utf-8').read().rstrip('\n').split('\n')
if not (lines[-1].startswith('    ') and '{platform:' in lines[-1]):
    sys.exit('params.yaml nie kończy się sekcją llm.runs - dopisz przebiegi ręcznie.')
text = '\n'.join(lines)
added = []
for r in sys.argv[1:]:
    p, e = r.split(':', 1)
    name = f'{p}-{e.split("_", 1)[1]}'
    if f'{name}:' not in text:
        lines.append(f'    {name + ":":<38} {{platform: {p}, event: {e}, args: "--window -7:14"}}')
        added.append(name)
open('params.yaml', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('Dopisano do params.yaml:', ', '.join(added) if added else 'nic (już są)')
PY

# 2) test na gold standardzie (600 komentarzy, ~12 zapytań) - tylko jeśli jeszcze nie ma wyniku
SUM=reports/groq_test/summary_gemini-3.5-flash-lite_b50.json
if ! grep -qs '"classified": 600' "$SUM"; then
  echo "== Gold standard (Gemini) =="
  dvc pull data/gold_600_ollama.csv.dvc
  python scripts/llm_gold_test.py --provider gemini --batch-size 50 || { echo "Test na gold się nie udał - sprawdź klucz API."; exit 1; }
fi

# 3) filtr tematyczny (nowa wersja Oli) + Gemini, wydarzenie po wydarzeniu
#    - "STOP" od skryptu = dzienny limit API -> koniec na dziś
#    - inne błędy (np. zepsuty JSON w jednej paczce) -> ponawiamy mniejszymi paczkami i idziemy dalej
LOG=$(mktemp)
retry_small () {   # $1 platform, $2 event, $3 name
  tried=0
  for bs in 10 2 1; do
    left=$(python -c "import json;print(json.load(open('data/interim/$1/$2/llm/report.json'))['remaining'])")
    [ "$left" = "0" ] && break
    tried=1
    echo "   ponawiam $left komentarzy paczkami po $bs"
    python scripts/llm_classify.py --platform "$1" --event "$2" --provider gemini --model gemini-3.5-flash-lite \
      --batch-size $bs --window -7:14 2>&1 | tee "$LOG" | grep -v -i "warn"
    grep -q "^STOP" "$LOG" && return 1
  done
  [ "$tried" = "1" ] && dvc commit -f -q "llm@$3"
  return 0
}

for r in $RUNS; do
  p=${r%%:*}; e=${r#*:}; name="$p-${e#*_}"
  echo; echo "== $name =="
  dvc repro -s "topic_${p}@${e}" || exit 1
  dvc repro -s -f "llm@${name}" 2>&1 | tee "$LOG" | grep -v -i "warning"
  if grep -q "^STOP" "$LOG"; then
    echo; echo "Dzienny limit API. Uruchom skrypt ponownie jutro rano (ok. 9:00)."; exit 0
  fi
  retry_small "$p" "$e" "$name" || { echo; echo "Dzienny limit API. Uruchom skrypt ponownie jutro rano (ok. 9:00)."; exit 0; }
done

echo; echo "Podsumowanie (pozostało = komentarze, których nie udało się sklasyfikować):"
for r in $RUNS; do
  p=${r%%:*}; e=${r#*:}
  python -c "import json;d=json.load(open('data/interim/$p/$e/llm/report.json'));print(f'  {\"$p\":8}{\"$e\":48} pozostało {d[\"remaining\"]}')"
done
echo; echo "GOTOWE. Teraz: dvc push, potem commit params.yaml i dvc.lock."
