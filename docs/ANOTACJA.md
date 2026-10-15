# Anotacja: przygotowanie rundy i liczenie zgodności

Zasady kodowania są w [CODEBOOK.md](CODEBOOK.md). Ten plik opisuje, jak przygotować arkusze i policzyć zgodność kodowania `hate` (1/0).

## 1. Przygotowanie zestawu

```powershell
git pull ; dvc pull
python scripts/annotation_sample.py --name pilot_v1 --n-per-platform 100 --annotators A B C D
# jeśli nie ma jeszcze data/raw/youtube:
python scripts/annotation_sample.py --name pilot_v1 --n-per-platform 100 --annotators A B C D --youtube-csv sciezka\do\komentarze.csv
```

- Z każdej platformy losowanych jest `--n-per-platform` komentarzy. **Wszyscy kodujący dostają ten sam zestaw.**
- Skład zestawu na każdej platformie:
  - 40%: komentarz wspomina migrantów lub Ukraińców i zawiera wrogie słowo,
  - 40%: komentarz wspomina migrantów lub Ukraińców bez wrogiego słowa,
  - 20%: wrogie słowo bez wzmianki o migrantach, pod wpisem o migracji. To przypadki z niejasnym adresatem, np. samo „wypierdalajcie”.
- Wynik trafia do `data/annotation/pilot_v1/`:
  - `sheets/pilot_v1_<osoba>.xlsx` to arkusz z listą rozwijaną w kolumnach `hate` i `uncertain` oraz zakładką `instrukcja`,
  - w arkuszu `text` zawiera tylko słowa autora; cytat z innego komentarza (`>`) jest w kolumnie `context_quote`,
  - `manifest.csv` mapuje `item_id` na platformę i identyfikatory. Nie przekazuj go kodującym, bo kodowanie jest na ślepo.
- Drugie uruchomienie z tą samą nazwą jest zablokowane, bo zmieniłoby `item_id` w już rozdanych arkuszach.

## 2. Kodowanie

1. Otwórz swój arkusz i zakoduj każdy komentarz według codebooka.
2. Zapisz plik **pod tą samą nazwą** w `data/annotation/pilot_v1/annotated/`, jako `.xlsx` albo CSV UTF-8.

## 3. Zgodność

```powershell
python scripts/annotation_agreement.py --name pilot_v1
```

W `data/annotation/pilot_v1/results/` powstają:
- `report.md`:
  - dla wszystkich komentarzy, bez komentarzy oznaczonych `uncertain` oraz osobno według platformy i puli: α Krippendorffa z 95% przedziałem ufności, κ Fleissa, średnia κ Cohena z par, pełna zgodność i udział `hate=1`,
  - κ Cohena dla każdej pary,
  - dla każdej osoby: zgodność z większością pozostałych i udział `hate=1`,
- `disagreements.csv`: komentarze z różnymi kodami, z kodami i notatkami wszystkich osó
- `problems.csv`: brakujące albo niedozwolone wartości oraz `uncertain=1` bez notatki. Niedozwolona albo brakująca wartość `hate` liczy się jako brak kodu.

**Wyniki:**
- **α Krippendorffa** to główna miara: obsługuje braki kodów i dowolną liczbę kodujących. ≥ 0,80 oznacza zgodność dobrą, 0,667–0,80 wystarcza tylko do wniosków wstępnych, a < 0,667 oznacza, że trzeba poprawić codebook i powtórzyć rundę (Krippendorff, 2004).
- **κ Fleissa** mierzy zgodność wszystkich kodujących naraz, ale liczy się tylko z komentarzy zakodowanych przez wszystkich (`n` w nawiasie). **κ Cohena** dotyczy jednej pary; średnia z par to tzw. κ Lighta. Skala Landisa i Kocha (1977): 0,41–0,60 umiarkowana, 0,61–0,80 znaczna, > 0,80 prawie pełna zgodność. Przy kompletnych danych κ Fleissa i α są prawie równe.
- **Rzadka kategoria:** w podzbiorach, w których `hate=1` prawie nie występuje (np. pula `mig_other`), α bywa niska mimo wysokiej pełnej zgodności. Taki wynik czytaj razem z kolumną „pełna zgodność” i nie opieraj na nim wniosków.
- **Udział `hate=1`:** jeśli jedna osoba ma go wyraźnie wyższy lub niższy niż reszta, koduje ostrzej albo łagodniej. Omów to na podstawie `disagreements.csv`.

## 4. Po rundzie

```powershell
dvc add data/annotation/pilot_v1        # arkusze zawierają treści komentarzy: tylko DVC, nigdy git
git add data/annotation/pilot_v1.dvc data/annotation/.gitignore
git commit -m "Pilot annotation round v1" ; dvc push ; git push
```

Zmiany reguł wpisz do historii w codebooku i podnieś jego wersję. Każda kolejna runda dostaje nową nazwę (`pilot_v2`, `gold_v1`…).
