# Klasyfikatory hate speech i analizy na etykiecie `hate`

Dodatek do pipeline'u zespołu: trzy gotowe / douczone klasyfikatory mowy nienawiści, ich ocena na gold standardzie
zespołu oraz analizy wydarzeń (jak `notebooks/hate_analysis/`) na **samej etykiecie `hate`** z najlepszego modelu.
Kod zespołu (`scripts/`, `src/preprocessing`, `src/lexicon`, `notebooks/hate_analysis`) nie jest zmieniany – jest tylko używany.

## Co jest gdzie

| Ścieżka | Zawartość |
|---|---|
| `src/classifier/hate_models.py` | wybór komentarzy (filtr tematyczny zespołu), słownik → model, okna dla długich tekstów, zapis wyników |
| `src/classifier/banpl.py` | preprocessing BAN-PL (trening i predykcja modelu RoBERTa-BAN-PL) |
| `notebooks/models/04_herbert_hate.ipynb` | HerBERT-large, mowa nienawiści (PolEval 2019) → `herbert/` |
| `notebooks/models/05_polbert_cyberbullying.ipynb` | Polbert, cyberbullying (PolEval 2019) → `polbert/` |
| `notebooks/models/06_banpl_roberta_finetune.ipynb` | fine-tuning Polish RoBERTa-base-v2 na BAN-PL (hiperparametry z publikacji) → `models/` |
| `notebooks/models/07_roberta_banpl_hate.ipynb` | predykcje douczonym modelem → `roberta_banpl/` |
| `notebooks/models/08_gold_standard_eval.ipynb` | 3 modele vs `data/annotation/gold/gold.csv` (tylko `hate`) → `reports/gold_model_eval/` |
| `notebooks/hate_analysis_models/<platforma>/<wydarzenie>/` | analiza pojedynczego wydarzenia (kopia notebooka zespołu, etykieta `hate`) |
| `notebooks/hate_analysis_models/<platforma>/all_events_hate_analysis.ipynb` | wszystkie wydarzenia platformy razem (metaanaliza, typy wydarzeń, słowa) |
| `scripts/run_notebooks.py` | odpala wszystkie notebooki z folderu po kolei |

## Zasady (te same co w AMC_Hate_Speech, notebooki 04–07)

1. **Komentarze** = filtr tematyczny zespołu (`scripts/topic_filter.py`): słownik obelg 1/1 **albo**
   `topic_sample.is_potential_migration` (wpis + komentarz). Liczony w pamięci, `topic/` nie jest potrzebne ani zapisywane.
2. **Najpierw słownik** (`src/lexicon/slurs.py`, reguła z `scripts/preprocess_slurs.py`): `hate_auto = 1` → hejt.
3. **Model tylko dla pozostałych komentarzy**; teksty > 512 tokenów w nakładających się oknach (maksimum po oknach).
4. `hate_final` = słownik **albo** model (`prob_hate_max ≥ 0.5`). Na tej etykiecie liczone są analizy.

Etykiety LLM zespołu (`labeled/`) **nie są potrzebne** – modele dają własną etykietę `hate`, a gold standard jest w `data/annotation/gold/`.

## Kolejność uruchamiania

```bash
source .venv/bin/activate
pip install "torch>=2.6" transformers tqdm nbclient ipykernel   # jednorazowo (poza requirements.txt zespołu)
dvc pull                                                         # clean/ i slurs/ dla wszystkich platform
```

1. `notebooks/models/06_banpl_roberta_finetune.ipynb` – trening (Mac M / MPS: ~3–15 min na epokę, early stopping zwykle po 6–8 epokach).
2. `notebooks/models/04_…`, `05_…`, `07_…` – predykcje (~435 tys. komentarzy do modelu na 3 platformach; HerBERT-large najwolniejszy).
   Można przerwać i odpalić ponownie – policzone fragmenty są pomijane.
3. `notebooks/models/08_gold_standard_eval.ipynb` – metryki i wybór najlepszego modelu (`reports/gold_model_eval/best_model.json`).
4. Analizy: `python scripts/run_notebooks.py notebooks/hate_analysis_models` (albo ręcznie pojedyncze notebooki).
   Model do analiz bierze się z `best_model.json`; inny model: ustaw `MODEL = "polbert"` itd. w konfiguracji notebooka.

## Wyniki

- `data/interim/<platforma>/<wydarzenie>/{herbert,polbert,roberta_banpl}/comments.csv` (+ `meta.json`) – tylko id i wyniki,
  bez treści; foldery są w `.gitignore` wydarzenia (jak `clean/`). Podsumowania: `data/interim/<platforma>/<model>_summary.csv`.
- `reports/gold_model_eval/` – `model_metrics.csv` (ogółem i per platforma, 3 warianty), `gold_predictions.csv`, `best_model.json`.
- `reports/hate_analysis_models/` – efekty wydarzeń i metaanaliza per platforma (CSV) z notebooków `all_events_…`.

## Uwagi

- Wczesne wydarzenia na Bluesky (2024) mają po kilkanaście–kilkadziesiąt komentarzy w temacie – w notebookach pojedynczych
  wydarzeń testy są wtedy pomijane, a w analizie zbiorczej wydarzenia z < 200 komentarzami nie biorą udziału w testach łącznych.
- Typy i zasięgi wydarzeń (`EVENT_META` w notebookach `all_events_…`) są przypisane ręcznie: 7 jak u zespołu, reszta wg README.
- `models/` (wytrenowany model, ~500 MB) i `data/external/ban_pl/` są w `.gitignore` – nie trafiają do gita.
