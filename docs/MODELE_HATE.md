# Klasyfikatory hate speech, gold standard i analizy na etykiecie `hate`

Dodatek do pipeline'u zespołu: trzy klasyfikatory mowy nienawiści, ich ocena (i ocena etykiet LLM) na gold standardzie
oraz analizy wydarzeń na etykiecie `hate` z najlepszego modelu. Mapa notebooków: `notebooks/README.md`.

## Co jest gdzie

| Ścieżka | Zawartość |
|---|---|
| `src/classifier/hate_models.py` | wybór komentarzy (filtr tematyczny zespołu), słownik → model, okna dla długich tekstów, zapis wyników |
| `src/classifier/banpl.py` | preprocessing BAN-PL (trening i predykcja RoBERTa-BAN-PL; usuwa artefakty zbioru: maski wulgaryzmów, placeholdery) |
| `notebooks/2_modele_hate/04_herbert_hate.ipynb` | HerBERT-large, mowa nienawiści (PolEval 2019) → `herbert/` |
| `notebooks/2_modele_hate/05_polbert_cyberbullying.ipynb` | Polbert, cyberbullying (PolEval 2019) → `polbert/` |
| `notebooks/2_modele_hate/06_banpl_roberta_finetune.ipynb` | fine-tuning Polish RoBERTa-base-v2 na BAN-PL (hiperparametry z publikacji) → `models/` |
| `notebooks/2_modele_hate/07_roberta_banpl_hate.ipynb` | predykcje douczonym modelem → `roberta_banpl/` |
| `notebooks/3_gold_standard/08_gold_standard_eval.ipynb` | 3 modele vs gold (`hate`), wybór najlepszego → `reports/gold_model_eval/` |
| `notebooks/3_gold_standard/09_gold_standard_llm.ipynb` | etykiety LLM zespołu vs gold (`hate`, `hate_migrant`, `migrant`) → `reports/gold_llm_eval/` |
| `notebooks/3_gold_standard/10_hate_models_vs_llm.ipynb` | `hate`: LLM vs klasyfikatory na tych samych komentarzach (McNemar, bootstrap ΔF1) |
| `notebooks/5_analizy_herbert_hate/` | analizy wydarzeń (kopie notebooków zespołu) na etykiecie `hate`, 15 wydarzeń, ±28 dni |
| `notebooks/6_wyniki_koncowe/` | wyniki końcowe projektu (H1–H4, LLM i HerBERT) i analiza uzupełniająca |
| `scripts/run_notebooks.py` | odpala notebooki z folderu po kolei |

## Zasady predykcji

1. **Komentarze** = filtr tematyczny zespołu (`scripts/topic_filter.py`): słownik obelg 1/1 **albo**
   `topic_sample.is_potential_migration` (wpis + komentarz), liczony w pamięci.
2. **Najpierw słownik** (`src/lexicon/slurs.py`, reguła z `scripts/preprocess_slurs.py`): `hate_auto = 1` → hejt.
3. **Model tylko dla pozostałych komentarzy**; teksty > 512 tokenów w nakładających się oknach (maksimum po oknach).
4. `hate_final` = słownik **albo** model (`prob_hate_max ≥ 0.5`). Na tej etykiecie liczone są analizy.

## Kolejność uruchamiania

```bash
source .venv/bin/activate
pip install "torch>=2.6" transformers tqdm nbclient ipykernel   # jednorazowo
dvc pull
```

1. `2_modele_hate/06_…` – trening (MPS: ~3 min na epokę), potem `04_…`, `05_…`, `07_…` – predykcje (wznawialne).
2. `3_gold_standard/08_…` (wymaga modeli), potem `09_…` i `10_…` (bez modeli, kilka sekund).
3. `python scripts/run_notebooks.py notebooks/5_analizy_herbert_hate` – analizy pojedynczych wydarzeń (opcjonalnie).
4. `python scripts/run_notebooks.py notebooks/6_wyniki_koncowe` – wyniki końcowe.

## Wyniki

- `data/interim/<platforma>/<wydarzenie>/{herbert,polbert,roberta_banpl}/comments.csv` – tylko id i wyniki (w `.gitignore`).
- `reports/` – opis w `reports/README.md`.

## Uwagi

- Gold standard (600 komentarzy, 2 rundy): klucz `gold_id` = runda + `item_id` (numery `item_id` powtarzają się między rundami).
- Wczesne wydarzenia na Bluesky (2024) mają po kilkanaście–kilkadziesiąt komentarzy w temacie – pomijane w testach.
- `models/` (~500 MB) i `data/external/ban_pl/` są w `.gitignore`.
