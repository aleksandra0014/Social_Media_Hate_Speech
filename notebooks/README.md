# Notebooki – mapa projektu

Kolejność folderów = kolejność pracy. **Wyniki projektu: `4_analizy_llm_hate_migrant/cross_platform_hate_analysis.ipynb` (LLM) i `6_wyniki_koncowe/cross_platform_hate_analysis_herbert.ipynb` (HerBERT).**

| Folder | Co zawiera | Kto | Wyniki zapisuje do |
|---|---|---|---|
| `1_eda/` | eksploracja surowych danych z Bluesky, YouTube i Wykopu | zespół | – |
| `2_modele_hate/` | `04` HerBERT, `05` Polbert, `06` dotrenowanie RoBERTy na BAN-PL, `07` predykcje RoBERTy – etykieta `hate` dla wszystkich wydarzeń | Gosia | `data/interim/<platforma>/<wydarzenie>/{herbert,polbert,roberta_banpl}/` |
| `3_gold_standard/` | `08` klasyfikatory na gold standardzie (wybór najlepszego), `09` etykiety LLM na gold standardzie (`hate`, `hate_migrant`, `migrant`), `10` `hate`: LLM vs klasyfikatory na tych samych komentarzach | Gosia | `reports/gold_model_eval/`, `reports/gold_llm_eval/` |
| `4_analizy_llm_hate_migrant/` | analizy na etykietach LLM (hejt wobec migrantów): notebook na każde wydarzenie × platforma, `wykop/all_events_…`, `youtube/all_events_…` i **`cross_platform_hate_analysis.ipynb`** – analiza międzyplatformowa (H1, H2, H4; metaanaliza, słowa, cele hejtu, autorzy, polubienia) | Ola, Julka, Marta | – |
| `5_analizy_herbert_hate/` | te same analizy na etykiecie `hate` z HerBERT-a, dla **wszystkich** 15 wydarzeń i okna ±28 dni (notebook na wydarzenie × platforma + `all_events_…` na platformę) | Gosia | `reports/hate_analysis_models/` |
| `6_wyniki_koncowe/` | **`cross_platform_hate_analysis_herbert.ipynb`** – analiza międzyplatformowa Oli 1:1 na hejcie z HerBERT-a: 11 wydarzeń × 3 platformy, okno −7…+14, miary `hate/temat` i `temat/all`; na końcu analizy dodatkowe (testy z README, H3, werdykty) | Gosia, na bazie analizy Oli | – |
| `archiwum/` | starsza wersja analizy H4 Oli (`old_h4_platformy_ola`), wcześniejsze wyniki końcowe (LLM + HerBERT na 7 wydarzeniach) i analiza HerBERT-a na 15 wydarzeniach ±28 dni | Ola, Gosia | – |

Wszystkie notebooki same znajdują katalog projektu (szukają `events.json` w górę), więc działają z dowolnego folderu.
Kilka notebooków naraz: `python scripts/run_notebooks.py notebooks/6_wyniki_koncowe` (albo inny folder).

## Co odpalić po nowych danych z DVC 

```bash
git merge origin/final && dvc pull
python scripts/run_notebooks.py notebooks/3_gold_standard/09_gold_standard_llm.ipynb notebooks/3_gold_standard/10_hate_models_vs_llm.ipynb
python scripts/run_notebooks.py notebooks/6_wyniki_koncowe
```

Notebooki `08` i `2_modele_hate/*` wymagają modeli (GPU / MPS) – tylko gdy zmieni się gold standard albo dane `clean/`.
