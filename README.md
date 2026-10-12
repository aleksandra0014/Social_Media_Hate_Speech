# Analiza mediów cyfrowych: Wpływ wydarzeń społecznych i politycznych na poziom mowy nienawiści wobec migrantów w polskojęzycznych mediach społecznościowych

Projekt badawczy analizujący dynamikę, skalę oraz mechanizmy mowy nienawiści w polskojęzycznych mediach społecznościowych w latach 2021–2026.

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

## 📅 3. Baza wydarzeń (2021–2026)

Projekt uwzględnia x zróżnicowanych wydarzeń o charakterze społecznym, politycznym, kryminalnym i dezinformacyjnym:

---

## ⚙️ 4. Dane i pipeline technologiczny

**Dane:**
* Okres: 2021-2026.
* Platformy: YouTube, Wykop, Bluesky.
* Język: polskojęzyczne komentarze.
* Tematyka: treści dotyczące migrantów.
* Jednostka analizy: pojedynczy komentarz.
* Wydarzenia: ok. 30 istotnych wydarzeń społecznych, politycznych, gospodarczych i medialnych związanych z m. in. Ukrainą.
* Analiza: poziom mowy nienawiści w czasie oraz jego zmiany w związku z wybranymi wydarzeniami, z uwzględnieniem różnic między platformami.

**Pipeline:**
1. **Pozyskanie danych:** Pobieranie publicznych komentarzy z YouTube, Wykopu oraz Bluesky z zachowaniem odpowiedniego okna czasowego dla komentarzy 28 dni po i 28 dni przed wydarzeniem (32 dni przed i 28 dni po dla postów/wideo, komentarze max do 4 dni od powstania posta/wideo).
2. **Filtrowanie:** Selekcja słownikowa oparta na słowach kluczowych związanych z migrantami i Ukraińcami.
3. **Klasyfikacja:** Model Polish RoBERTa-v2 (large) lub HerBERT (large) douczane na zbiorze BAN-PL (ok. 24 tys. oznaczonych treści z Wykopu) lub PolEval 2019 (szkodliwe wypowiedzi z X/Twittera).
4. **Metryki jakości:** Ocena modelu oparta na Accuracy, Precision, Recall, F1-score oraz macierzy pomyłek z wykorzystaniem stworzonego zbioru referencyjnego (gold standard).
5. **Analiza:** Analiza bazująca na dziennym odsetku komentarzy klasyfikowanych jako nienawiść. Analiza skoków, wygasania oraz porównanie między wydarzeniami, ich typami oraz platformami.

---

## 📈 5. Testy statystyczne i ewaluacja hipotez



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
