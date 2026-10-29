# Analiza mediów cyfrowych: Wpływ wydarzeń społecznych i politycznych na poziom mowy nienawiści wobec migrantów w polskojęzycznych mediach społecznościowych

Projekt badawczy analizujący dynamikę, skalę oraz mechanizmy mowy nienawiści w polskojęzycznych mediach społecznościowych w latach 2022–2026.

---

## 🎯 1. Problem badawczy i motywacja

**Problem badawczy:**
Sprawdzenie, czy, w jakim stopniu i przez jak długo istotne wydarzenia społeczne, polityczne i medialne związane m. in. z Ukrainą wpływają na poziom mowy nienawiści wobec migrantów w polskojęzycznych mediach społecznościowych.

**Motywacja:**
Mowa nienawiści wobec migrantów, w tym Ukraińców jest istotnym problemem społecznym, szczególnie po rozpoczęciu pełnoskalowej inwazji Rosji w 2022 r. Jednocześnie jej poziom może zmieniać się w zależności od bieżących wydarzeń, np. napływu uchodźców, sporów gospodarczych czy napięć politycznych. Chcemy więc sprawdzić, czy konkretne wydarzenia wiążą się ze wzrostem lub spadkiem mowy nienawiści, jak silny jest ten efekt i jak długo się utrzymuje.

---

## ❓ 2. Pytania i hipotezy badawcze

### Pytanie główne:
> *Czy istotne wydarzenia społeczne, polityczne i medialne związane z migrantami są powiązane ze zmianami poziomu mowy nienawiści wobec migrantów w polskojęzycznych mediach społecznościowych?*

### Hipotezy badawcze:
* **H1 - Wpływ wydarzeń:** Istotne wydarzenia związane z migrantami powodują zmiany poziomu mowy nienawiści wobec migrantów w polskojęzycznych mediach społecznościowych.
* **H2 - Charakter wydarzenia:** Siła i kierunek zmian mowy nienawiści zależą od rodzaju wydarzenia (np. kryminalne, polityczne, zagraniczne).
* **H3 - Trwałość efektu:** Zmiana poziomu mowy nienawiści jest największa bezpośrednio po wydarzeniu, a następnie stopniowo słabnie.
* **H4 - Różnice między platformami:** Zależność między wydarzeniami a poziomem mowy nienawiści różni się między YouTube, Wykopem, a Bluesky.

---

## 📅 3. Wydarzenia

Dane zebrano wokół **15 wydarzeń** z lat 2022–2026 (`events.json` + 4 wcześniejsze wydarzenia tylko z YouTube).
**Analiza główna** (hejt wobec migrantów, etykiety LLM) obejmuje **7 wydarzeń** – te, dla których zespół przygotował
etykiety LLM (`docs/ANALIZA_MIEDZYPLATFORMOWA.md`). Pozostałe wydarzenia są w analizie uzupełniającej (HerBERT, sam hejt).

| Data | Wydarzenie | Typ | Analiza główna (7) | Platformy z danymi |
|---|---|---|---|---|
| 24.02.2022 | atak Rosji na Ukrainę | wojna | – | YouTube |
| 08.05.2022 | zabójstwo na Nowym Świecie (dezinformacja o sprawcy) | dezinformacja | – | YouTube |
| 22.09.2023 | premiera „Zielonej granicy” | polityczne | – | YouTube |
| 15.10.2023 | wybory i referendum | polityczne | – | YouTube |
| 10.04.2024 | Pakt o migracji i azylu – przyjęcie w PE | polityczne | ✓ | Wykop, YouTube, (Bluesky – za mało komentarzy) |
| 28.05.2024 | atak na żołnierza na granicy | kryminalne | – | Wykop, YouTube |
| 06.06.2024 | śmierć sierż. Mateusza Sitka | kryminalne | ✓ | Wykop (YouTube wykluczony: brak okresu „przed”) |
| 08.09.2024 | bójka w Śremie | kryminalne | ✓ | Wykop, YouTube |
| 12.10.2024 | strategia migracyjna Polski | polityczne | ✓ | Wykop, YouTube |
| 06.06.2025 | naloty ICE w Los Angeles | zagraniczne | – | Wykop, YouTube, Bluesky |
| 15.10.2025 | dezinformacja o morderstwie w Krakowie | dezinformacja | ✓ | Wykop, YouTube, Bluesky |
| 12.06.2026 | wejście w życie Paktu o migracji i azylu | polityczne | – | Wykop, YouTube, Bluesky |
| 30.07.2026 | masowe przekroczenie granicy w Ceucie | kryzys graniczny | ✓ | Wykop, YouTube, Bluesky |
| 15.08.2026 | atak w Kamiennej Górze (dezinformacja o sprawcy) | kryminalne | ✓ | Wykop, YouTube, Bluesky |
| 15.09.2026 | atak w Jarosławiu | kryminalne | – | Wykop, YouTube, Bluesky |

Bluesky: etykiety LLM są dla wszystkich 7 wydarzeń; 4 wydarzenia z 2024 r. mają za mało komentarzy (< 30 przed wydarzeniem) i są pomijane w testach.

---

## ⚙️ 4. Dane i pipeline

**Dane:** publiczne komentarze z **Wykopu, YouTube i Bluesky** (API platform), wersjonowane w DVC (`docs/DVC_INSTRUKCJA.md`),
zanonimizowane (pseudonimy zamiast identyfikatorów).

| | Wykop | YouTube | Bluesky |
|---|---|---|---|
| Zbieranie | wpisy i komentarze ±28 dni, wyszukiwanie słowami o migracji | filmy z okna wokół wydarzenia, komentarze do 4 dni od publikacji filmu | wpisy i komentarze ±28 dni, słowa o migracji |
| Okno w analizie głównej | −7…+14 dni | −7…+14 dni | −7…+14 dni |

**Pipeline:**
1. **Pozyskanie** – `scripts/wykop.py`, `scripts/youtube.py`, `scripts/bluesky.py` → `data/raw/`.
2. **Czyszczenie i filtrowanie** – `scripts/preprocess_*.py` → `data/interim/<platforma>/<wydarzenie>/clean/` (cytaty, linki,
   wzmianki, emoji usunięte); filtr tematyczny migracji (`scripts/topic_filter.py`); słownik obelg (`src/lexicon/slurs.py`).
3. **Etykiety LLM** (zespół) – `scripts/topic_sample.py`, lokalny LLM przez Ollamę: czy komentarz dotyczy migracji,
   czy jest hejtem, czy hejtem wobec migrantów → `labeled/` (codebook: `docs/CODEBOOK.md`).
4. **Klasyfikatory** – HerBERT-HS, Polbert-CB i Polish RoBERTa-base-v2 dotrenowana na BAN-PL (`docs/MODELE_HATE.md`):
   najpierw słownik, potem model → etykieta `hate`.
5. **Gold standard** – 600 komentarzy (po 200 z platformy) oznaczonych przez anotatorów LLM z rozstrzyganiem sporów
   (`docs/ANOTACJA.md`) → ocena klasyfikatorów i etykiet LLM (Accuracy, Precision, Recall, F1, MCC, macierz pomyłek).
6. **Analiza** – dzienny odsetek komentarzy z hejtem przed i po wydarzeniu, testy z sekcji 5.

**Struktura repozytorium:** notebooki – `notebooks/README.md`; wyniki – `reports/README.md`.

---

## 📈 5. Testy statystyczne i ewaluacja hipotez

| **Pytanie / hipoteza**                                               | **Co sprawdzamy?**                                                 | **Test / metoda**                           | **Dlaczego?**                                                                                                                                            |
| -------------------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **H1. Wydarzenia są związane ze zmianą poziomu HATE**                | Czy poziom HATE przed i po wydarzeniu różni się istotnie?          | **Wilcoxon + wielkość efektu**              | Porównujemy dwa powiązane pomiary dla tych samych wydarzeń. Nie zakładamy normalności.                                                                   |
| **H2. Siła efektu zależy od rodzaju wydarzenia**                     | Czy zmiana HATE różni się między typami wydarzeń?                  | **Kruskal–Wallis → post-hoc Dunn + Holm**   | Porównujemy więcej niż 2 niezależne grupy i nie zakładamy normalności. Post-hoc wskazuje, które typy wydarzeń różnią się między sobą.                    |
| **H3. HATE jest najwyższy bezpośrednio po wydarzeniu i potem spada** | Czy poziom HATE różni się między kolejnymi okresami po wydarzeniu? | **Friedman → post-hoc Wilcoxon + Holm**     | Te same wydarzenia obserwujemy w kilku kolejnych okresach, więc pomiary są zależne.                                                                      |
| **H3. Jak długo utrzymuje się efekt?**                               | Po ilu dniach HATE wraca do poziomu baseline?                      | **Wilcoxon: każde okno vs baseline + Holm** | Dla każdego wydarzenia porównujemy baseline z kolejnym oknem czasowym. Są to porównania parowane; korekcja ogranicza ryzyko fałszywie istotnych wyników. |
| **H4. Różnice między platformami**                                   | Czy poziom HATE różni się między YouTube, Wykopem i Bluesky?       | **Kruskal–Wallis → post-hoc Dunn + Holm**   | Porównujemy więcej niż 2 niezależne grupy i nie zakładamy normalności.                                                                                   |
---

## 📊 Wyniki (skrót)

Pełne wyniki z wykresami: **`notebooks/4_analizy_llm_hate_migrant/cross_platform_hate_analysis.ipynb`** (LLM, 7 wydarzeń) i **`notebooks/6_wyniki_koncowe/cross_platform_hate_analysis_herbert.ipynb`** (HerBERT, 11 wydarzeń). Skrót poniżej pochodzi z wcześniejszej wersji (`notebooks/archiwum/wyniki_koncowe_llm_herbert_7_wydarzen.ipynb`) – do aktualizacji.

Analiza na **komentarzach o migracji** (te, które są w `labeled/`; komentarzy spoza tej selekcji nie analizujemy) –
16 komórek wydarzenie × platforma, 46,5 tys. komentarzy; etykiety LLM (hejt wobec migrantów) i HerBERT (hejt) na tych samych komentarzach.

- **Jakość etykiet:** najlepszy klasyfikator hejtu to **HerBERT** (F1 0,78 na 600 komentarzach gold; Polbert 0,64,
  RoBERTa-BAN-PL 0,54). LLM na komentarzach gold o migracji (349): `hate` F1 0,74 (HerBERT na tych samych 0,79),
  `hate_migrant` F1 0,59.
- **H1 – częściowo:** udział hejtu wobec migrantów zmienia się istotnie tylko w 3 z 16 komórek (YouTube: ↑ Kamienna Góra,
  ↓ Pakt w PE i strategia migracyjna); łącznie brak wzrostu (OR 0,83, p = 0,10). HerBERT: brak istotnych zmian.
- **H2 – brak dowodów:** typ wydarzenia nie wyjaśnia zmiany (K–W p = 0,07).
- **H3 – brak dowodów:** brak szczytu tuż po wydarzeniu i wygasania.
- **H4 – częściowo:** platformy różnią się poziomem hejtu (YouTube 60% > Wykop 42% > Bluesky 33% komentarzy o migracji),
  ale reagują na wydarzenia podobnie.
- Wydarzenia zwiększają raczej **ilość dyskusji o migracji** niż jej wrogość. Etykiety LLM i HerBERT dają zgodne wnioski.

Na Bluesky w testach są 3 wydarzenia (Kraków, Ceuta, Kamienna Góra) – pozostałe mają za mało komentarzy.

---

## ⚖️ 6. Etyka i ochrona prywatności

* Pozyskanie: dane pozyskiwane legalnie z publicznie dostępnych źródeł/API, zgodnie z regulaminami platform.
* Przechowywanie: przechowujemy tylko dane niezbędne do badania, przez wymagany okres.
* Przetwarzanie: dane wykorzystywane wyłącznie do celów badawczych.
* Anonimizacja: usuwamy dane pozwalające na bezpośrednią identyfikację użytkowników, identyfikatory zastępujemy losowymi kodami (pseudonimizacja)

---

## 💡 7. Beneficjenci i wpływ projektu

* **Bezpośrednio (Setki osób):** Moderatorzy, redakcje, organizacje i badacze, którzy użyją wyników i metod bezpośrednio.
* **Społecznie (Setki tysięcy osób):** Migrańci mieszkający w Polsce, w tym Ukraińcy, których nienawiść dotyka.
* **Pośrednio (Miliony osób):** Czytelnicy komentarzy poprzez zwiększenie świadomości oraz lepsze doświadczenia przy użytkowaniu mediów społecznościowych, dzięki lepszej moderacji.
