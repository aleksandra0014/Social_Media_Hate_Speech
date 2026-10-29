# Analiza międzyplatformowa: plan i decyzje

**Wersja 0.1  2026-10-27**

Dokument opisuje, jak porównać mowę nienawiści wobec migrantów na trzech platformach (Wykop, YouTube, Bluesky) wokół tych samych wydarzeń. Zbiera:
- dlaczego dane z platform nie są wprost porównywalne,
- jakie decyzje podjęliśmy i dlaczego,
- jak testujemy hipotezy H1, H2 i H4,
- jakie analizy znajdą się w nowym notebooku.

Techniki statystyczne użyte w tym dokumencie (RR, meta-analiza, korekta Holma itd.) są wyjaśnione w [METODY_ANALIZY.md](METODY_ANALIZY.md).

Stary notebook `notebooks/4_analizy_llm_hate_migrant/all_platforms_hate_analysis.ipynb` zostaje bez zmian. Analiza powstanie w nowym notebooku.

---

## 1. Cel i pytania badawcze

Chcemy sprawdzić, czy wydarzenia związane z migracją zmieniają poziom hejtu wobec migrantów i czy ta zmiana wygląda tak samo na każdej platformie.

| Hipoteza | Treść | Gdzie w analizie |
|---|---|---|
| **H1** – wpływ wydarzeń | Istotne wydarzenia związane z migrantami powodują zmiany poziomu mowy nienawiści wobec migrantów w polskojęzycznych mediach społecznościowych. | punkt 1, [§4.1](#41-h1--wpływ-wydarzeń) |
| **H2** – charakter wydarzenia | Siła i kierunek zmian mowy nienawiści zależą od rodzaju wydarzenia (np. kryminalne, polityczne, zagraniczne). | punkt 7, [§4.3](#43-h2--charakter-wydarzenia) |
| **H4** – różnice między platformami | Zależność między wydarzeniami a poziomem mowy nienawiści różni się między YouTube, Wykopem a Bluesky. | punkt 1, [§4.2](#42-h4--różnice-między-platformami) |

---

## 2. Dane i dlaczego nie są wprost porównywalne

### 2.1. Platformy

| | Wykop | YouTube | Bluesky |
|---|---|---|---|
| Sposób zbierania | posty i komentarze wybrane po słowach kluczowych | **wszystkie** komentarze pod filmami z 6 kanałów informacyjnych | posty i komentarze wybrane po słowach kluczowych |
| Okno w danych | −28..+28 dni | −7..+18 dni (filmy z −7..+14, komentarze pod filmem do 4 dni od publikacji) | −28..+28 dni |
| Wydarzenia w analizie | 7 | 6 (bez Smierc_Zolnierza, patrz [§3.9](#39-youtube-smierc_zolnierza)) | 3 |
| Komentarze (clean, przybliżone) | ~160 tys. | ~590 tys. | ~76 tys. |
| Co ma etykiety LLM | cały podzbiór z regexa tematycznego (`topic/`), w tym etykieta „o migracji” | tylko komentarze o migracji (regex + LLM) | tylko komentarze o migracji (regex + LLM) |
| Leksykon obelg (`hate_auto`) | tak | nie (brak etapu `slurs/`) | tak (ale w etykietach używamy tylko LLM, patrz [§3.6](#36-etykiety-hejtu-na-wykopie)) |
| Autorzy | hash | **brak** (puste już w surowych danych) | pseudonim |
| Polubienia | `votes` (mogą być ujemne) | `likeCount` | `like_count` |

### 2.2. Wydarzenia

Daty dnia 0 pochodzą z `events.json`. Typ i zasięg zostały przypisane ręcznie (`EVENT_META` w starym notebooku).

| Wydarzenie | Dzień 0 | Typ | Zasięg | Wykop | YT | Bluesky |
|---|---|---|---|:-:|:-:|:-:|
| Pakt_Azyl_PE | 2024-04-10 | polityczne (polityka / prawo) | zagraniczne (UE) | ✓ | ✓ | – |
| Smierc_Zolnierza | 2024-06-06 | kryminalne (przemoc / incydent) | krajowe | ✓ | ✗ | – |
| Bojka_Srem | 2024-09-08 | kryminalne (przemoc / incydent) | krajowe | ✓ | ✓ | – |
| Strategia_Migracyjna | 2024-10-12 | polityczne (polityka / prawo) | krajowe | ✓ | ✓ | – |
| Dezinformacja_Krakow | 2025-10-15 | dezinformacja | krajowe | ✓ | ✓ | ✓ |
| Ceuta_Masowe_Przekroczenie | 2026-07-30 | kryzys graniczny | zagraniczne (UE) | ✓ | ✓ | ✓ |
| Atak_Kamienna_Gora | 2026-08-15 | kryminalne (przemoc / incydent) | krajowe | ✓ | ✓ | ✓ |

✗ oznacza, że wydarzenie jest wykluczone z analizy. Docelowo jest **16 komórek wydarzenie × platforma** (7 + 6 + 3). Trzy wydarzenia (Kraków, Ceuta, Kamienna Góra) występują na wszystkich platformach.

> **Uwaga o danych:** w pliku `data/interim/bluesky/2026-08-15_Atak_Kamienna_Gora/labeled/comments.csv` nagłówek ma 9 kolumn, a wiersze 10 (brak nazwy kolumny `parent_context`). Pandas bierze wtedy pierwszą kolumnę za indeks i wszystkie kolumny przesuwają się o jedną (w `comment_id` lądują id postów). Prawdziwe `comment_id` w 100% pasują do `clean/comments.csv`. Notebook wykrywa to przy wczytywaniu i dokłada brakującą nazwę kolumny, więc analiza ma pełne **16 komórek**, a zbalansowany panel – **3 wydarzenia**.

Pozostałe wydarzenia z `events.json` (Atak_Zolnierz_Granica, Naloty_ICE_Los_Angeles, Pakt_Migracyjny_Wejscie_w_Zycie, Atak_Jaroslaw) nie mają etykiet i nie wchodzą do analizy.

### 2.3. Skąd różnica ~20% vs ~5%

Odsetek komentarzy o migracji i odsetek hejtu jest na Wykopie i Bluesky kilka razy wyższy niż na YT. **To w dużej mierze efekt sposobu zbierania, a nie platformy:**
- Wykop i Bluesky są już przefiltrowane słowami kluczowymi o migracji, więc w próbie jest dużo komentarzy na ten temat.
- YT zawiera wszystkie komentarze pod wszystkimi filmami z kanałów informacyjnych, a większość tych filmów migracji nie dotyczy.

Dla `hate_migrant/all` w starym notebooku: Wykop 14,1%, YT 2,2%. Te liczby **nie mówią**, że Wykop jest 6 razy bardziej nienawistny. Mówią, że próby są inaczej dobrane.

### 2.4. Pokrycie dni na YouTube

Na YT zbieramy filmy opublikowane w oknie −7..+14 i komentarze do 4 dni od publikacji filmu. W efekcie:
- dni **−3..+14** mają pełne pokrycie (komentarz z dnia *d* może pochodzić z każdego filmu z dni *d−4..d*),
- dni **−7..−4** mają pokrycie częściowe (brakuje filmów sprzed −7),
- dni **+15..+18** mają pokrycie częściowe (brakuje filmów po +14).

Liczby komentarzy na brzegach okna są więc zaniżone. Na odsetki ma to mniejszy wpływ.

### 2.5. Etykiety tylko w podzbiorze „o migracji”

Na YT i Bluesky LLM oceniało hejt tylko w komentarzach o migracji (regex + LLM). Komentarz spoza tego podzbioru ma z definicji `hate_migrant = 0`. Kolumny `human_*` na YT i Bluesky są puste, więc korzystamy wyłącznie z etykiet LLM.

---

## 3. Rozterki i decyzje

Każda decyzja jest opisana jako: **problem → rozważane opcje → decyzja → dlaczego**.

### 3.1. Wspólne okno czasowe

- **Problem:** Wykop i Bluesky mają ±28 dni, YT −7..+18.
- **Opcje:** każda platforma w swoim oknie; okno symetryczne −7..+7; wspólne −7..+14.
- **Decyzja:** **okno −7..+14** dla wszystkich platform. Bez analiz odporności na wybór okna. Dane ±28 Wykopu i Bluesky wykorzystujemy tylko w teście placebo (§4.1).
- **Dlaczego:** −7..+14 to okno, w którym zbierano filmy na YT, więc jest najdłuższe możliwe bez dni z niepełnym pokryciem po stronie „po”.

### 3.2. Przypisanie do „przed” i „po”

- **Problem:** komentarz pod filmem z dnia −3 może zostać napisany w dniu +1.
- **Opcje:** data komentarza; data posta / filmu.
- **Decyzja:** **data komentarza** (`relative_day` z `clean/comments.csv`, liczony w czasie Europe/Warsaw). Przed = dni −7..−1, po = dni 0..+14. **Dzień 0 należy do „po”**.
- **Dlaczego:** mierzymy reakcję ludzi w czasie. Wydarzenia zwykle wywołują reakcję tego samego dnia. Tak też liczą wszystkie istniejące skrypty i notebooki.

### 3.3. Poziomy czy zmiany

- **Problem:** poziomy hejtu nie są porównywalne między platformami ([§2.3](#23-skąd-różnica-20-vs-5)).
- **Opcje:** porównywać poziomy; porównywać zmianę przed → po; jedno i drugie.
- **Decyzja:**
  - **między platformami porównujemy tylko zmianę przed → po:** ryzyko względne (RR) i iloraz szans (OR) z 95% CI, różnica w punktach procentowych (pp) jako uzupełnienie,
  - **poziomy (%) i liczby bezwzględne pokazujemy tylko w obrębie jednej platformy**, z zastrzeżeniem w tekście.
- **Dlaczego:** każda platforma jest swoją własną kontrolą. Sposób zbierania wpływa na poziom, ale w obrębie platformy jest taki sam przed i po wydarzeniu, więc zmiana względna jest porównywalna.

### 3.4. Liczby bezwzględne

- **Problem:** okres „przed” trwa 7 dni, a „po” 15 dni (0..+14). Suma komentarzy „po” będzie większa nawet bez żadnego efektu.
- **Decyzja:** liczby komentarzy i komentarzy z hejtem podajemy jako **średnią dzienną** przed i po (plus sumę w tabeli). W widokach łącznych **zawsze rozbijamy je na platformy** (słupki skumulowane lub osobne panele). Nie sumujemy ich w jeden wspólny odsetek.
- **Dlaczego:** średnia dzienna usuwa wpływ długości okresu. Rozbicie na platformy chroni przed tym, żeby YT przykrył wolumenem pozostałe platformy.

### 3.5. Miary

- **Problem:** mamy dwie etykiety hejtu (ogólny i wobec migrantów) i etykietę tematu. Na Wykopie hejt ogólny był oceniany w szerszym podzbiorze niż na YT i Bluesky.
- **Opcje:** liczyć wszystko wobec wszystkich komentarzy; wobec komentarzy o migracji; oba warianty.
- **Decyzja:** trzy miary:

  | Miara | Co mierzy | Rola |
  |---|---|---|
  | `hate_migrant/all` | jaki odsetek wszystkich komentarzy to hejt wobec migrantów | **główna** |
  | `migrant/all` | jaki odsetek wszystkich komentarzy dotyczy migracji | wspierająca: czy wydarzenie zwiększa samą dyskusję o migracji |
  | `hate_migrant/migrant` | jaki odsetek komentarzy o migracji to hejt | wspierająca, „ciekawostka”: czy dyskusja o migracji staje się bardziej nienawistna |

  `hate/all` (hejt ogólny) **pomijamy**.
- **Dlaczego:** na Wykopie hejt ogólny był oceniany w całym podzbiorze z regexa, a na YT i Bluesky tylko w komentarzach o migracji. Ta sama miara mierzyłaby na platformach różne rzeczy. `hate_migrant` jest zdefiniowany spójnie.
- **Szczegół:** w `hate_migrant/migrant` liczymy tylko komentarze z `migrant = 1`. Na Wykopie leksykon czasem trafia komentarz, którego LLM nie uznał za dotyczący migracji. Taki komentarz liczy się w `hate_migrant/all`, ale nie w `hate_migrant/migrant`, dzięki czemu odsetek nie przekracza 100%.

### 3.6. Etykiety hejtu na Wykopie

- **Problem:** na Wykopie są dwa źródła etykiety: LLM i leksykon obelg (`hate_migrants_auto`). Na YT i Bluesky tylko LLM.
- **Opcje:** wszędzie tylko LLM; na Wykopie LLM OR leksykon.
- **Decyzja:** na Wykopie `hate_migrant = llm_is_hate_migrants OR hate_migrants_auto`, na YT i Bluesky tylko LLM.
- **Dlaczego:** leksykon wychwytuje jednoznaczne obelgi, które LLM czasem pomija. Asymetrię zapisujemy jako ograniczenie. Na wnioski o *zmianie* wpływa ona słabo, bo w obrębie platformy definicja jest stała przed i po.

### 3.7. Poprawione etykiety tematu

- **Decyzja:** dla Wykopu (Strategia_Migracyjna, Ceuta_Masowe_Przekroczenie) używamy `comments_corrected.csv`, które poprawiają `llm_is_about_migration`.
- **Wpływ:** zmienia `migrant/all` i `hate_migrant/migrant` dla tych dwóch wydarzeń.

### 3.8. Bluesky ma tylko 3 wydarzenia

- **Opcje:** w analizach łącznych wszystkie komórki; tylko 3 wydarzenia wspólne dla wszystkich platform; Bluesky osobno.
- **Decyzja:** **analiza główna używa wszystkich 16 komórek**. **Zbalansowany panel** (3 wspólne wydarzenia × 3 platformy = 9 komórek) jest jednym z testów wspierających H4 (§4.2). Na wykresach per wydarzenie brakujące komórki Bluesky zostają puste.
- **Dlaczego:** wszystkie komórki dają więcej danych. Zbalansowany panel pokazuje, że różnice między platformami nie wynikają z tego, że każda platforma ma inny zestaw wydarzeń.

### 3.9. YouTube Smierc_Zolnierza

- **Decyzja:** wykluczone.
- **Dlaczego:** cały okres „przed” to 99 komentarzy pod jednym filmem. Porównanie przed / po mierzyłoby ten jeden film, a nie wydarzenie.

### 3.10. Nakładające się okna na Wykopie

- **Problem:** okna Bojka_Srem / Strategia_Migracyjna (34 dni różnicy) i Ceuta / Kamienna_Gora (16 dni różnicy) częściowo się pokrywają w danych ±28. Ten sam komentarz może trafić do dwóch wydarzeń.
- **Decyzja:** **traktujemy to jako ograniczenie**, bez korekty.
- **Uwaga:** przy oknie −7..+14 nakładanie w dużej mierze znika (zostaje Ceuta +9..+14 = Kamienna Góra −7..−2). W analizach opartych na tekście i autorach (punkty 3–6) duplikaty komentarzy usuwamy. Z testu placebo wykluczamy komórki, w których okno placebo zawiera dzień 0 innego wydarzenia.

### 3.11. Łączenie platform

- **Problem:** „wspólnie dla wszystkich platform” można policzyć na kilka sposobów.
- **Opcje:**
  - (a) zsumować komentarze ze wszystkich platform i policzyć jeden odsetek,
  - (b) meta-analiza: każda komórka wydarzenie × platforma to osobne „badanie” z własnym efektem, a efekty łączymy z wagami,
  - (c) regresja logistyczna z efektami stałymi komórek.
- **Decyzja:** **(b) jako wynik główny, (c) jako potwierdzenie.**
  - per wydarzenie (2–3 platformy): **fixed-effect**, bo przy 2–3 komórkach random-effects jest niestabilny,
  - per platforma i łącznie: **random-effects** (DerSimonian–Laird + Hartung–Knapp).
- **Dlaczego nie (a):** YT ma ok. 590 tys. komentarzy, Wykop ok. 160 tys., Bluesky ok. 76 tys., więc zsumowany odsetek byłby w praktyce wynikiem YT. Do tego poziomy są nieporównywalne ([§2.3](#23-skąd-różnica-20-vs-5)), więc ich mieszanie tworzy liczbę bez interpretacji.

---

## 4. Hipotezy i jak je testujemy

Zasady wspólne dla wszystkich hipotez:
- **testy dwustronne**, bo hipotezy mówią o *zmianie*, a nie tylko o wzroście,
- **miara główna `hate_migrant/all`**, a `migrant/all` i `hate_migrant/migrant` jako miary wspierające z tymi samymi testami,
- poziom istotności α = 0,05, korekta Holma tam, gdzie jest wiele testów tej samej rodziny,
- efekt komórki = log-OR (do testów i meta-analizy), raportowany też jako RR i różnica w pp.

### 4.1. H1 – wpływ wydarzeń

**Pytanie:** czy po wydarzeniu poziom hejtu wobec migrantów się zmienia?

| Element | Co robimy |
|---|---|
| **Test główny** | meta-analiza random-effects log-OR ze wszystkich 16 komórek (DerSimonian–Laird + Hartung–Knapp), H0: łączny log-OR = 0 |
| Wspierający 1 | test każdej komórki: OR z regresji logistycznej `y ~ po` z błędami klastrowanymi po wątku, korekta Holma; podsumowanie „ile komórek istotnie ↑ / ↓ / bez zmian” |
| Wspierający 2 | test znaków: czy komórek ze wzrostem jest więcej niż ze spadkiem |
| Wspierający 3 | model łączny `y ~ po + C(wydarzenie×platforma)` z błędami klastrowanymi po wątku |
| Wspierający 4 | przerwany szereg czasowy (ITS) `y ~ relative_day + po + relative_day:po`: oddziela skok poziomu w dniu 0 od zmiany trendu |
| Wspierający 5 | test placebo: fałszywy dzień 0 na −14 w danych ±28 (Wykop, Bluesky), z porównaniem −21..−15 vs −14..−1. Efekt **nie powinien** wyjść |

**Wykresy:**
- forest plot: OR każdej komórki z CI i rombem efektu łącznego,
- dumbbell: % przed → % po dla każdej komórki (osobny panel na platformę),
- wykres ITS: punkty dzienne i dopasowane odcinki przed i po.

**Kryterium:**
- **potwierdzona:** efekt łączny istotny, a większość istotnych komórek zmienia się w tym samym kierunku, placebo nieistotne,
- **częściowo:** efekt łączny nieistotny, ale część komórek ma istotne zmiany (wtedy wydarzenia działają, ale nie jednakowo, co prowadzi do H2 i H4),
- **niepotwierdzona:** brak istotnego efektu łącznego i brak istotnych komórek po Holmie.

### 4.2. H4 – różnice między platformami

**Pytanie:** czy wielkość zmiany przed → po różni się między platformami?

Porównujemy **wielkość zmiany** (log-OR), a nie poziomy.

| Element | Co robimy |
|---|---|
| **Test główny** | test różnic podgrup w meta-analizie: moderator = platforma, statystyka Q_between |
| Wspierający 1 | model `y ~ po + po:C(platforma) + C(wydarzenie×platforma)` z błędami klastrowanymi, test Walda na łączne zero wszystkich interakcji `po:platforma` |
| Wspierający 2 | pary platform: stosunek OR (ROR) z CI, korekta Holma dla 3 par |
| Wspierający 3 | I² i Q Cochrana w każdej platformie: czy w obrębie platformy wydarzenia działają podobnie |
| Wspierający 4 | powtórzenie testu głównego na zbalansowanym panelu (3 wspólne wydarzenia × 3 platformy) |

**Wykresy:**
- forest plot pogrupowany po platformach z rombem efektu łącznego każdej platformy,
- wykres interakcji: indeks przed → po (przed = 1,0), jedna linia na platformę,
- sparowany wykres 3 wspólnych wydarzeń: dla każdego wydarzenia OR na każdej platformie obok siebie.

**Kryterium:**
- **potwierdzona:** Q_between istotne i wynik utrzymuje się na zbalansowanym panelu,
- **częściowo:** istotne tylko w jednym z dwóch wariantów albo tylko dla jednej pary platform,
- **niepotwierdzona:** brak istotnych różnic.

### 4.3. H2 – charakter wydarzenia

**Pytanie:** czy siła i kierunek zmiany zależą od rodzaju wydarzenia?

**Wymiary charakteru wydarzenia:**
- **typ:** kryminalne (przemoc / incydent, 3 wydarzenia), polityczne (polityka / prawo, 2), dezinformacja (1), kryzys graniczny (1),
- **zasięg:** krajowe (5) vs zagraniczne (2).

| Element | Co robimy |
|---|---|
| **Test główny** | meta-regresja log-OR (16 komórek) z moderatorem `typ` i kontrolą platformy, test omnibus moderatora |
| Wspierający 1 | kontrast binarny: kryminalne (3) vs reszta (4) |
| Wspierający 2 | meta-regresja z moderatorem `zasięg` (krajowe vs zagraniczne) |
| Wspierający 3 | test permutacyjny: wszystkie przetasowania etykiet typu między 7 wydarzeniami, dokładne p |
| Wspierający 4 | kierunek: tabela znaków efektów per typ (ile komórek ↑ i ile ↓) |

**Per platforma:** na Wykopie (7 wydarzeń) i YT (6) test kontrastu kryminalne vs reszta. Na Bluesky każdy typ ma jedno wydarzenie, więc tylko opis.

**Wykresy:**
- forest plot pogrupowany po typie z rombem każdego typu,
- wykres punktowy RR: typ × platforma,
- rozkład statystyki z testu permutacyjnego z zaznaczoną wartością obserwowaną.

**Kryterium:**
- **potwierdzona:** istotny moderator w meta-regresji i zgodny test permutacyjny,
- **częściowo:** istotny tylko kontrast binarny albo tylko zasięg, albo różnice w kierunku bez istotności,
- **niepotwierdzona:** brak różnic.

**Zastrzeżenie:** wynik jest **eksploracyjny**. Jest tylko 7 wydarzeń, a dezinformacja i kryzys graniczny mają po jednym, więc „efekt typu” jest w nich nieodróżnialny od efektu konkretnego wydarzenia. Typy zostały przypisane ręcznie.

---

## 5. Plan analiz

Dla każdej analizy: pytanie, miara, metoda, wykres i ograniczenia. Wszystko w oknie −7..+14, chyba że zaznaczono inaczej.

### 5.1. Odsetek przed i po, liczba hejtu, liczba komentarzy (H1, H4)

Dla każdej komórki wydarzenie × platforma liczymy:
- % przed, % po dla trzech miar,
- różnicę w pp z 95% CI (Newcombe),
- RR z 95% CI,
- OR z regresji logistycznej z błędami klastrowanymi po wątku, p z korektą Holma w obrębie miary,
- średnią dzienną komentarzy i komentarzy z hejtem przed i po.

Cztery widoki:

| Widok | Jak łączymy | Wykres |
|---|---|---|
| a. wydarzenia osobno, na każdej platformie | bez łączenia, 16 komórek | dumbbell + forest plot, panel na platformę; tabela liczności |
| b. wydarzenia osobno, wspólnie dla platform | fixed-effect po platformach dla każdego wydarzenia | forest plot: wydarzenia, przy każdym komórki platform i romb łączny |
| c. przed / po wspólnie dla wydarzeń, osobno na platformę | random-effects po wydarzeniach w obrębie platformy | forest plot pogrupowany po platformach (to samo co H4) |
| d. przed / po wspólnie dla wydarzeń i platform | random-effects ze wszystkich 16 komórek + model logistyczny | romb łączny (H1), słupki średnich dziennych rozbite na platformy |

### 5.2. Top 3 największe zmiany na osi czasu

- **Ranking:** |log RR| dla `hate_migrant/all`, czyli największe zmiany względne w którąkolwiek stronę (hipotezy mówią o zmianie). Bierzemy komórki istotne po korekcie Holma i z co najmniej 20 komentarzami z hejtem w okresie „przed” (żeby mała baza nie dawała absurdalnych RR). Jeśli istotnych komórek jest mniej niż 3, listę uzupełniamy kolejnymi i oznaczamy je jako nieistotne.
- **Trzy warianty:**
  - per platforma: 3 wydarzenia o największym RR na każdej platformie (na Bluesky to wszystkie 3),
  - ogólnie, bez łączenia platform: 3 największe komórki z całej puli 16,
  - łącząc platformy: 3 wydarzenia z największym efektem łącznym z widoku 5.1 b; na wykresie linie wszystkich platform dla danego wydarzenia.
- **Oś czasu:** `relative_day` −7..+14, linia pionowa w dniu 0, przerywana linia średniej „przed”.
  - jedna platforma na wykresie: dzienny % ze średnią kroczącą 3-dniową,
  - kilka platform na wykresie: **indeks** = % dzienny / średnia „przed” (1,0 = brak zmiany), bo surowe poziomy nie zmieszczą się na jednej skali,
  - pod spodem słupki z liczbą komentarzy dziennie, żeby było widać, kiedy % liczony jest z małej próby.
- Miary wspierające jako dodatkowe panele na tych samych wykresach.

### 5.3. Najczęstsze słowa w hejcie wobec migrantów

- **Materiał:** komentarze `hate_migrant = 1` ze wszystkich platform razem (przybliżone liczby w oknie: ok. 15 tys. z Wykopu, ok. 12 tys. z YT, kilkaset z Bluesky).
- **Przetwarzanie:** małe litery, usunięcie linków i wzmianek, tokeny z co najmniej 3 liter, stopwordy ze starego notebooka, **lematyzacja `simplemma`** (trzeba ją dopisać do `requirements.txt`).
- **Wynik:**
  - top 30 najczęstszych słów (unigramy i bigramy),
  - top 30 słów wyróżniających: log-odds z priorytetem Dirichleta (Monroe i in. 2008), `hate_migrant = 1` vs komentarze o migracji bez hejtu,
  - jako uzupełnienie: małe panele per platforma, żeby było widać, czy wynik nie pochodzi z jednej platformy.
- **Ograniczenie:** pula wspólna jest zdominowana przez Wykop i YT. Bluesky ma kilkaset komentarzy.

### 5.4. Kogo obrażono i jakimi obelgami

- **Grupy docelowe:** regex `TARGET_GROUPS` ze starych notebooków na komentarzach `hate_migrant = 1`, na wszystkich platformach. Cztery grupy:
  - Ukraińcy,
  - Muzułmanie / Arabowie / Bliski Wschód,
  - Afrykanie / czarnoskórzy,
  - Migranci / uchodźcy (ogólnie).

  Jeden komentarz może trafić do kilku grup. Osobno pokazujemy „brak wskazanej grupy”.
- **Kategorie obelg:** `src/lexicon/slurs.py` uruchomiony w notebooku na tekstach `hate_migrant = 1` ze wszystkich trzech platform (na YT nie ma etapu `slurs/`, więc liczymy od nowa). 15 kategorii zwijamy do 6 grup:

  | Grupa | Kategorie z `slurs.py` |
  |---|---|
  | obelga etniczna | obelga_etniczna, obelga_etniczna_zlozenie, obelga_historyczna |
  | dehumanizacja | dehumanizacja |
  | stereotyp | stereotyp, stereotyp_swiadczenia, stereotyp_seksistowski |
  | kody | kod, kod_historyczny, kod_ironiczny, kod_spiskowy, kod_inwazji, kod_prorosyjski |
  | wezwanie do wydalenia | wezwanie_do_wydalenia |
  | inne obelgi | obelga |

- **Wykresy:** heatmapy wydarzenie × grupa i platforma × grupa (osobno dla grup docelowych i kategorii obelg), wartości jako % komentarzy z hejtem.
- **Ograniczenie:** leksykon łapie tylko część hejtu. Zawsze pokazujemy, jaki % komentarzy `hate_migrant` zawiera jakikolwiek termin z leksykonu.

### 5.5. Koncentracja autorów hejtu

- **Platformy:** tylko Wykop i Bluesky (YT nie ma autorów).
- **Miary:**
  - udział hejtu napisanego przez top 1% i top 10% autorów hejtu,
  - współczynnik Giniego,
  - krzywa Lorenza.
- **Punkt odniesienia:** ta sama koncentracja dla **wszystkich** komentarzy. Pytanie brzmi: czy hejt jest bardziej skoncentrowany niż zwykłe pisanie?
- **Dodatkowo:** czy ci sami autorzy hejtują przy kilku wydarzeniach. **Tylko Wykop:** na Bluesky pseudonimy są nadawane od nowa w każdym wydarzeniu (`Pseudonyms()` w `scripts/bluesky.py`), więc tam autor = (wydarzenie, pseudonim).

### 5.6. Czy hejt zbiera więcej polubień

- **Porównanie:** `hate_migrant = 1` vs `hate_migrant = 0` **w obrębie komentarzy o migracji** (`migrant = 1`), osobno na każdej platformie. Dzięki temu porównujemy komentarze na ten sam temat, a na YT i Bluesky tylko tam mamy etykiety.
- **Miary:** mediana, średnia, % komentarzy z co najmniej jednym polubieniem.
- **Testy:**
  - test Manna-Whitneya,
  - jako miara efektu: model ujemny dwumianowy `likes ~ hate_migrant + C(wydarzenie)` z błędami klastrowanymi po wątku, który daje stosunek średnich.
- **Wykop:** ujemne `votes` zostają w testach rangowych, a w modelu przycinamy je do 0.

### 5.7. Typ wydarzenia a wielkość zmiany (H2)

Opisane w [§4.3](#43-h2--charakter-wydarzenia).
- **łącznie dla platform:** meta-regresja z moderatorem typ i kontrolą platformy, kontrast kryminalne vs reszta, zasięg, test permutacyjny,
- **per platforma:** wykres punktowy RR pokolorowany typem; test kontrastu na Wykopie i YT, na Bluesky tylko opis.

---

## 6. Ograniczenia

1. **Dobór próby:** Wykop i Bluesky zebrane po słowach kluczowych, YT po kanałach. Poziomy nie są porównywalne między platformami.
2. **Asymetria etykiet:** na Wykopie hejt = LLM OR leksykon, na YT i Bluesky tylko LLM.
3. **Tylko etykiety LLM:** kolumny `human_*` są puste na YT i Bluesky. Trafność klasyfikatora sprawdzamy osobno na zbiorze referencyjnym ([CODEBOOK.md](CODEBOOK.md)).
4. **Nakładające się okna** na Wykopie (Bojka / Strategia, Ceuta / Kamienna Góra); w oknie −7..+14 zostaje tylko część Ceuta / Kamienna Góra.
5. **Niepełne pokrycie dni** na brzegu okna YT (dni −7..−4).
6. **Brak autorów na YT:** koncentracja autorów tylko dla Wykopu i Bluesky.
7. **Małe n wydarzeń:** 7 wydarzeń, 16 komórek, dwa typy z jednym wydarzeniem. H2 jest eksploracyjna. Na Bluesky przy 3 wydarzeniach łączny efekt platformy ma szeroki przedział (Hartung–Knapp z 2 stopniami swobody).
8. **Ręczne przypisanie typów** wydarzeń.
9. **Leksykon** obejmuje tylko część hejtu, a dla YT nie ma etapu `slurs/` (liczony w notebooku).
10. **Brak lematyzacji w starych notebookach:** wyniki słownikowe nie są wprost porównywalne z nowymi.
11. **Korelacja w czasie:** wydarzenia mogą zbiegać się z innymi tematami w mediach. Placebo i ITS częściowo to sprawdzają, ale nie wykluczają.
12. **Brak analiz odporności:** nie sprawdzamy, czy wnioski zależą od wyboru okna ani od przypisania dnia 0.

---

## 7. Struktura notebooka

Notebook: [`notebooks/4_analizy_llm_hate_migrant/cross_platform_hate_analysis.ipynb`](../notebooks/4_analizy_llm_hate_migrant/cross_platform_hate_analysis.ipynb).

1. Konfiguracja: ścieżki, okno, `EVENT_META`, `TARGET_GROUPS`, kolory.
2. Wczytanie i ujednolicenie danych: łączenie `labeled` z `clean` po `comment_id`, definicje `migrant` i `hate_migrant`, przycięcie do okna.
3. Opis danych: tabela liczności per komórka, poziomy w obrębie platform.
4. **Punkt 1 + H1 + H4:** widoki a–d, testy, forest ploty, ITS, placebo.
5. Punkt 2: top 3 zmiany na osi czasu.
6. Punkt 3: słowa.
7. Punkt 4: grupy docelowe i kategorie obelg.
8. Punkt 5: koncentracja autorów.
9. Punkt 6: polubienia.
10. **Punkt 7 + H2:** typ wydarzenia.
11. Podsumowanie hipotez: tabela H1 / H2 / H4 z rozstrzygnięciem.
