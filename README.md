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

Projekt uwzględnia około 30 zróżnicowanych wydarzeń o charakterze społecznym, politycznym, kryminalnym i dezinformacyjnym. Przykładowe wydarzenia: 

* 24.02.2022 - atak Rosji na Ukrainę (wojna)
* 08.05.2022 - zabójstwo na Nowym Świecie i dezinformacja dotycząca sprawców (dezinformacja)
* 22.09.2023 - premiera „Zielonej granicy” (polityczne, medialne)
* 15.10.2023 - wybory parlamentarne i referendum (polityczne)
* 10.04.2024 - przyjęcie Paktu o Migracji i Azylu przez PE (polityczne)
* 28.05.2024 - atak na polskiego żołnierza na granicy (kryminalne)
* 06.06.2024 - śmierć sierż. Mateusza Sitka (kryminalne)
* 08.09.2024 - bójka w Śremie i reakcje wokół migracji (kryminalne)
* 12.10.2024 - ogłoszenie strategii migracyjnej Polski (polityczne)
* 06.06.2025 - rozpoczęcie nalotów ICE w Los Angeles (zagraniczne)
* 15.10.2025 - dezinformacja dotycząca rzekomego potrójnego morderstwa w Krakowie (dezinformacja)
* 12.06.2026 - wejście w życie Paktu o Migracji i Azylu (polityczne)
* 30.07.2026 - masowe przekroczenie granicy w Ceucie (zagraniczne)
* 15.08.2026 - atak nożownika w Kamiennej Górze i dezinformacja o narodowości sprawcy (dezinformacja)
* 15.09.2026 – atak w Jarosławiu (kryminalne)

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

| **Pytanie / hipoteza**                                               | **Co sprawdzamy?**                                                 | **Test / metoda**                           | **Dlaczego?**                                                                                                                                            |
| -------------------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **H1. Wydarzenia są związane ze zmianą poziomu HATE**                | Czy poziom HATE przed i po wydarzeniu różni się istotnie?          | **Wilcoxon + wielkość efektu**              | Porównujemy dwa powiązane pomiary dla tych samych wydarzeń. Nie zakładamy normalności.                                                                   |
| **H2. Siła efektu zależy od rodzaju wydarzenia**                     | Czy zmiana HATE różni się między typami wydarzeń?                  | **Kruskal–Wallis → post-hoc Dunn + Holm**   | Porównujemy więcej niż 2 niezależne grupy i nie zakładamy normalności. Post-hoc wskazuje, które typy wydarzeń różnią się między sobą.                    |
| **H3. HATE jest najwyższy bezpośrednio po wydarzeniu i potem spada** | Czy poziom HATE różni się między kolejnymi okresami po wydarzeniu? | **Friedman → post-hoc Wilcoxon + Holm**     | Te same wydarzenia obserwujemy w kilku kolejnych okresach, więc pomiary są zależne.                                                                      |
| **H3. Jak długo utrzymuje się efekt?**                               | Po ilu dniach HATE wraca do poziomu baseline?                      | **Wilcoxon: każde okno vs baseline + Holm** | Dla każdego wydarzenia porównujemy baseline z kolejnym oknem czasowym. Są to porównania parowane; korekcja ogranicza ryzyko fałszywie istotnych wyników. |
| **H4. Różnice między platformami**                                   | Czy poziom HATE różni się między YouTube, Wykopem i Bluesky?       | **Kruskal–Wallis → post-hoc Dunn + Holm**   | Porównujemy więcej niż 2 niezależne grupy i nie zakładamy normalności.                                                                                   |
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
