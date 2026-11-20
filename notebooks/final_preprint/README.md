# Final preprint – notebooki, z których pochodzą wyniki

Kopie notebooków użytych w finalnym preprincie i plakacie (etykiety Gemini 3.5 Flash-Lite, 20 wydarzeń).
Odpalaj po kolei; każdy sam znajduje folder projektu, więc działa z tego miejsca.

| # | notebook | co liczy | część preprintu | wyniki zapisuje w |
|---|---|---|---|---|
| 1 | `1_gold_klasyfikatory.ipynb` | HerBERT, Polish BERT, RoBERTa (BAN-PL) i sam słownik na 600 komentarzach złotego standardu | Gold standard (Tab. 2) | `reports/gold_model_eval/` |
| 2 | `2_gold_gemini.ipynb` | Gemini na złotym standardzie (`hate`, `hate_migrant`), osobno dla platform | Gold standard (Tab. 2, Rys. 2) | `reports/gold_gemini_eval/` |
| 3 | `3_gold_gemini_vs_klasyfikatory.ipynb` | Gemini vs klasyfikatory na tych samych komentarzach, testy istotności (bootstrap, McNemar) | Gold standard – wybór Gemini | `reports/gold_gemini_eval/` |
| 4 | `4_hipotezy_H1_H3_i_Q1a.ipynb` | dane, OR dla każdej komórki, H1 (metaanaliza, uwaga vs ton, przebieg dzienny), H2, H3 (Wykop vs YouTube na 19 wspólnych wydarzeniach + 3 platformy), H1 i H2 bez Bluesky, sprawdzenie HerBERTem, Q1(a): słowa, chmura, cele, autorzy, lajki; na końcu komórka z liczbami cytowanymi w wynikach H1–H3 | Data, Results H1–H3, Q1(a) | `reports/final_gemini/` |
| 5 | `5_cechy_hejtu_Q1b.ipynb` | cechy komentarzy z hejtem i bez, regresja logistyczna; na końcu to samo z etykietami HerBERTa (sprawdzenie) | Results Q1(b) | `reports/final_gemini/` |
| 6 | `6_wykresy_preprintu.ipynb` | wszystkie wykresy preprintu w starym stylu (kod rysowania przeniesiony z `cross_platform_hate_analysis.ipynb` z gałęzi `gold_herbert`, `wyniki_koncowe.ipynb` i `hate_analysis`), z wyników notebooków 2–5 | wszystkie rysunki poza pipeline'em | `reports/final_gemini/preprint/` |

Wszystkie liczby z preprintu są w `reports/final_gemini/results.json`.
Notebooki 4 i 5 = ten sam kod co `scripts/final_analysis_gemini.py` (wersja do terminala); ich własne wykresy w `reports/final_gemini/*.png` są robocze.
Notebook 6 = `scripts/final_figures_gemini.py`; to z niego są wykresy w preprincie (`reports/final_gemini/preprint/`).
Obrazek pipeline'u (`fig_pipeline_en.png`) jest rysowany ręcznie, nie z kodu.
Oryginały: `3_gold_standard/08, 09b, 10b`, `6_wyniki_koncowe/wyniki_koncowe_final.ipynb`, `7_hate_analysis/hate_analysis_final.ipynb`.
