# Metody analizy: słowniczek

**Wersja 0.1  2026-10-27**

Ten plik wyjaśnia techniki użyte w [ANALIZA_MIEDZYPLATFORMOWA.md](ANALIZA_MIEDZYPLATFORMOWA.md). Każda technika ma:
- **co to jest** – definicja w jednym, dwóch zdaniach,
- **intuicja i przykład** – liczby zmyślone, ale realistyczne,
- **dlaczego tutaj** – po co w tej analizie,
- **jak czytać** – co znaczy wynik,
- **uwaga** – typowe pułapki.

W przykładach „komórka” oznacza jedno wydarzenie na jednej platformie, np. Kamienna Góra na Wykopie.

---

## Spis

1. [Miary zmiany: pp, RR, OR, log-OR](#1-miary-zmiany-pp-rr-or-log-or)
2. [Przedziały ufności: Wilson i Newcombe](#2-przedziały-ufności-wilson-i-newcombe)
3. [Testy dwustronne](#3-testy-dwustronne)
4. [Regresja logistyczna i błędy klastrowane](#4-regresja-logistyczna-i-błędy-klastrowane)
5. [Wielokrotne porównania i korekta Holma](#5-wielokrotne-porównania-i-korekta-holma)
6. [Meta-analiza](#6-meta-analiza)
7. [Różnice podgrup i meta-regresja](#7-różnice-podgrup-i-meta-regresja)
8. [Interakcja w regresji, test Walda, ROR](#8-interakcja-w-regresji-test-walda-ror)
9. [Przerwany szereg czasowy (ITS)](#9-przerwany-szereg-czasowy-its)
10. [Test placebo](#10-test-placebo)
11. [Test znaków i test permutacyjny](#11-test-znaków-i-test-permutacyjny)
12. [Szeregi dzienne: średnia krocząca, indeks, średnia dzienna](#12-szeregi-dzienne-średnia-krocząca-indeks-średnia-dzienna)
13. [Zbalansowany panel](#13-zbalansowany-panel)
14. [Analiza słów: stopwordy, lematyzacja, log-odds](#14-analiza-słów-stopwordy-lematyzacja-log-odds)
15. [Leksykon a klasyfikator LLM](#15-leksykon-a-klasyfikator-llm)
16. [Koncentracja: Lorenz, Gini, top k%](#16-koncentracja-lorenz-gini-top-k)
17. [Polubienia: Mann-Whitney i model ujemny dwumianowy](#17-polubienia-mann-whitney-i-model-ujemny-dwumianowy)

---

## 1. Miary zmiany: pp, RR, OR, log-OR

**Co to jest.** Cztery sposoby opisania, jak zmienił się odsetek między okresem „przed” (p₀) a „po” (p₁).

| Miara | Wzór | Przykład: p₀ = 2%, p₁ = 4% | Przykład: p₀ = 14%, p₁ = 16% |
|---|---|---|---|
| różnica w punktach procentowych (pp) | p₁ − p₀ | +2 pp | +2 pp |
| ryzyko względne (RR) | p₁ / p₀ | 2,0 | 1,14 |
| iloraz szans (OR) | [p₁/(1−p₁)] / [p₀/(1−p₀)] | 2,04 | 1,17 |
| log-OR | ln(OR) | 0,71 | 0,16 |

**Intuicja.** Obie platformy w przykładzie urosły o 2 pp, ale na pierwszej hejt się podwoił, a na drugiej wzrósł o 14%. Różnica w pp zależy od poziomu wyjściowego, a RR i OR mówią o zmianie *względnej*.

**Dlaczego tutaj.** Poziomy hejtu na platformach różnią się przez sposób zbierania danych (Wykop ok. 14%, YT ok. 2% dla `hate_migrant/all`). Porównywanie wzrostów w pp byłoby więc niesprawiedliwe. RR i OR porównują wzrost względny, który od poziomu wyjściowego zależy znacznie mniej.

**Jak czytać.**
- RR = 1 lub OR = 1: brak zmiany. Powyżej 1: wzrost, poniżej: spadek.
- RR = 1,5: po wydarzeniu odsetek jest o 50% wyższy niż przed.
- Przy małych odsetkach (poniżej ok. 10%) RR i OR są prawie równe.

**Dlaczego log-OR w testach.** Logarytm robi skalę symetryczną: podwojenie (OR = 2) to +0,69, a spadek o połowę (OR = 0,5) to −0,69. Rozkład log-OR jest też bliższy normalnemu, co jest potrzebne w meta-analizie. W tabelach i na wykresach pokazujemy RR lub OR, bo łatwiej je zrozumieć.

**Uwaga.** Przy bardzo małej bazie RR potrafi wyjść ogromny (np. 1 komentarz z hejtem przed i 6 po daje RR = 6). Dlatego w rankingu top 3 bierzemy tylko komórki z co najmniej 20 komentarzami z hejtem „przed”.

---

## 2. Przedziały ufności: Wilson i Newcombe

**Co to jest.** Przedział ufności (CI) 95% to zakres wartości zgodnych z danymi. Jeśli powtarzalibyśmy badanie wiele razy, 95% takich przedziałów zawierałoby prawdziwą wartość.

- **Wilson:** przedział dla jednego odsetka (np. % hejtu przed).
- **Newcombe:** przedział dla *różnicy* dwóch odsetków (pp), zbudowany z dwóch przedziałów Wilsona.

**Intuicja i przykład.** 30 hejtów na 1000 komentarzy daje 3,0% z CI Wilsona ok. 2,1–4,3%. Ten sam odsetek z 30 tys. komentarzy dałby CI ok. 2,8–3,2%. Im więcej danych, tym węższy przedział.

**Dlaczego tutaj.** Prosty wzór „p ± 1,96·SE” daje złe wyniki przy małych odsetkach (np. 2% na YT) i może wyjść poza zakres 0–100%. Wilson i Newcombe zachowują się poprawnie.

**Jak czytać.** Jeśli CI różnicy w pp nie zawiera 0 (albo CI dla RR lub OR nie zawiera 1), zmiana jest istotna na poziomie 5%.

**Uwaga.** Te przedziały zakładają niezależne komentarze. Komentarze w jednym wątku są ze sobą powiązane, więc testy opieramy na regresji z błędami klastrowanymi ([§4](#4-regresja-logistyczna-i-błędy-klastrowane)).

---

## 3. Testy dwustronne

**Co to jest.**
- Test **dwustronny** sprawdza, czy jest *jakakolwiek* zmiana (wzrost albo spadek).
- Test **jednostronny** sprawdza tylko jeden kierunek (np. tylko wzrost).

**Dlaczego tutaj.** H1 i H2 mówią o *zmianach* poziomu oraz o *sile i kierunku* zmian. Spadek hejtu po wydarzeniu też byłby ciekawym wynikiem, więc nie zakładamy z góry kierunku. Test dwustronny jest bardziej ostrożny: ten sam efekt musi być nieco silniejszy, żeby wyszedł istotny.

**Jak czytać.** p < 0,05 oznacza, że gdyby naprawdę nie było żadnej zmiany, tak duża różnica (w którąkolwiek stronę) pojawiałaby się rzadziej niż w 5% przypadków.

---

## 4. Regresja logistyczna i błędy klastrowane

**Co to jest.** Regresja logistyczna modeluje prawdopodobieństwo, że komentarz jest hejtem (y = 1), w zależności od zmiennych. W najprostszym modelu `y ~ po`, gdzie `po` = 1 dla komentarzy po wydarzeniu, współczynnik przy `po` to log-OR zmiany przed → po.

**Błędy klastrowane.** Zwykłe testy zakładają, że każdy komentarz to niezależna obserwacja. W praktyce komentarze w jednym wątku są do siebie podobne: jeden zapalny wpis ściąga wiele hejtu, a ludzie odpowiadają sobie nawzajem. Błędy klastrowane po wątku (`thread_id`) uwzględniają to podobieństwo.

**Intuicja i przykład.** Mamy 10 000 komentarzy, ale z 50 wątków. Efektywnie mamy więc bliżej „50 niezależnych rozmów” niż 10 000 niezależnych opinii. Zwykły test byłby zbyt pewny siebie i za często pokazywałby istotność. Błędy klastrowane poszerzają przedział ufności do uczciwej szerokości.

**Dlaczego tutaj.** Bez klastrowania nawet drobne zmiany wychodziłyby istotne tylko dlatego, że mamy dziesiątki tysięcy komentarzy.

**Model łączny.** `y ~ po + C(wydarzenie×platforma)` dodaje osobny poziom wyjściowy dla każdej komórki (efekty stałe), więc współczynnik `po` mierzy średnią zmianę *w obrębie* komórek, a nie różnice poziomów między platformami.

**Uwaga.** W modelu łącznym duże komórki (YT) mają większy wpływ. Dlatego modele są potwierdzeniem, a wynikiem głównym jest meta-analiza ([§6](#6-meta-analiza)).

---

## 5. Wielokrotne porównania i korekta Holma

**Co to jest.** Gdy robimy wiele testów naraz, rośnie szansa, że któryś wyjdzie istotny przez przypadek. Przy 16 komórkach i α = 0,05, nawet bez żadnego prawdziwego efektu, spodziewamy się średnio 0,8 fałszywego „odkrycia”.

**Korekta Holma** działa krok po kroku:
1. Sortujemy p-wartości od najmniejszej.
2. Najmniejszą porównujemy z α/m (m = liczba testów), kolejną z α/(m−1), następną z α/(m−2) itd.
3. Zatrzymujemy się przy pierwszym teście, który nie przechodzi; ten i wszystkie dalsze są nieistotne.

**Przykład.** Trzy testy z p = 0,01; 0,03; 0,04:
- 0,01 < 0,05/3 = 0,0167 → istotny,
- 0,03 > 0,05/2 = 0,025 → nieistotny, stop,
- 0,04 → nieistotny.

**Dlaczego tutaj.** Testujemy 16 komórek, 3 pary platform itd. Holm jest mniej konserwatywny niż Bonferroni (który dzieli wszystko przez m), a tak samo chroni przed fałszywymi odkryciami.

**Jak czytać.** W tabelach podajemy p „po korekcie Holma”. Istotność oceniamy względem 0,05.

**Uwaga.** Korektę robimy w obrębie jednej rodziny testów (np. 16 komórek dla jednej miary), nie dla wszystkich testów w notebooku naraz.

---

## 6. Meta-analiza

**Co to jest.** Sposób łączenia wyników wielu badań w jeden wynik ogólny. Tutaj każda komórka wydarzenie × platforma to osobne „badanie” ze swoim log-OR i jego niepewnością (błędem standardowym).

**Wagi.** Każda komórka dostaje wagę odwrotnie proporcjonalną do wariancji: im dokładniej oszacowany efekt (więcej danych), tym większa waga. W przeciwieństwie do sumowania komentarzy, wielka komórka YT nie zagłusza reszty, bo dokładność rośnie wolniej niż liczba komentarzy, a w random-effects wagi dodatkowo się wyrównują.

**Fixed-effect vs random-effects.**
- **Fixed-effect:** zakłada, że wszystkie komórki mierzą *ten sam* prawdziwy efekt i różnią się tylko losowo. Używamy go per wydarzenie (2–3 platformy), bo przy tak małej liczbie komórek nie da się sensownie oszacować zróżnicowania.
- **Random-effects:** zakłada, że każda komórka ma *własny* prawdziwy efekt (bo wydarzenia i platformy się różnią), a my szacujemy średnią tych efektów. To bardziej realistyczne przy różnych wydarzeniach, więc używamy go per platforma i łącznie.

**DerSimonian–Laird (DL)** to metoda szacowania, jak bardzo prawdziwe efekty różnią się między komórkami (wariancja τ²).

**Hartung–Knapp (HK)** to poprawka przedziału ufności efektu łącznego. Przy małej liczbie komórek zwykły przedział random-effects jest za wąski; HK go poszerza (używa rozkładu t zamiast normalnego).

**Q Cochrana i I².**
- **Q:** test, czy efekty komórek różnią się bardziej, niż wynikałoby z przypadku.
- **I²:** jaki % zróżnicowania efektów jest prawdziwy, a nie losowy. Orientacyjnie: 25% niskie, 50% umiarkowane, 75% wysokie.

**Forest plot.** Główny wykres meta-analizy:
- każdy wiersz to komórka: kwadrat = efekt (wielkość kwadratu = waga), kreska = CI,
- pionowa linia OR = 1 oznacza brak zmiany,
- romb na dole to efekt łączny; jego szerokość to CI.

**Jak czytać.** Jeśli romb nie przecina linii 1, efekt łączny jest istotny (H1). Wysokie I² mówi, że wydarzenia lub platformy działają różnie, i prowadzi do pytań H2 i H4.

---

## 7. Różnice podgrup i meta-regresja

**Test różnic podgrup (Q_between).** Dzielimy komórki na grupy (np. wg platformy) i robimy meta-analizę w każdej. Q_between sprawdza, czy efekty łączne grup różnią się od siebie bardziej niż przez przypadek. To test główny H4.

**Meta-regresja.** Regresja, w której obserwacją jest komórka, zmienną zależną jej log-OR, a zmiennymi objaśniającymi cechy komórki (moderatory): typ wydarzenia, zasięg, platforma. Każda komórka ma wagę jak w meta-analizie.

**Przykład.** Meta-regresja `log-OR ~ typ + platforma` może pokazać, że wydarzenia kryminalne mają log-OR średnio o 0,4 wyższy niż polityczne przy tej samej platformie. Test omnibus moderatora sprawdza, czy `typ` jako całość coś wyjaśnia.

**Dlaczego tutaj.** To test główny H2. Kontrola platformy jest potrzebna, bo Bluesky ma tylko 3 wydarzenia, więc bez niej różnica typów mogłaby być w rzeczywistości różnicą platform.

**Problem małego n.** Mamy 16 komórek, ale tylko 7 wydarzeń, a dwa typy mają po jednym wydarzeniu. Efekt „typu dezinformacja” to w praktyce efekt jednego wydarzenia w Krakowie. Dlatego:
- dodajemy **kontrast binarny** (kryminalne 3 vs reszta 4), który ma sensowną moc,
- dodajemy **test permutacyjny** ([§11](#11-test-znaków-i-test-permutacyjny)), który nie zakłada rozkładu normalnego,
- wynik H2 opisujemy jako **eksploracyjny**.

---

## 8. Interakcja w regresji, test Walda, ROR

**Interakcja.** W modelu `y ~ po + po:C(platforma) + C(wydarzenie×platforma)` składnik `po:platforma` mówi, *o ile* efekt wydarzenia na danej platformie różni się od efektu na platformie bazowej. Jeśli interakcje są równe 0, wszystkie platformy reagują tak samo.

**Test Walda.** Sprawdza naraz, czy kilka współczynników jest równych zero (tu: obie interakcje `po:platforma`). To jedno pytanie „czy platformy różnią się w reakcji?” zamiast kilku osobnych testów.

**ROR (stosunek OR).** ROR = OR platformy A / OR platformy B.

**Przykład.** OR na YT = 1,6, OR na Wykopie = 1,2, więc ROR = 1,33: na YT wzrost szans hejtu był o jedną trzecią silniejszy niż na Wykopie. ROR = 1 oznacza taką samą reakcję.

**Dlaczego tutaj.** To testy wspierające H4. Model regresji i meta-analiza liczą to samo innymi drogami; zgodność wyników wzmacnia wniosek.

---

## 9. Przerwany szereg czasowy (ITS)

**Co to jest.** Model dla danych dziennych, który rozdziela dwa rodzaje zmiany po wydarzeniu:

```
y ~ relative_day + po + relative_day:po
```

- `relative_day`: trend przed wydarzeniem (czy hejt rósł już wcześniej),
- `po`: **skok poziomu** w dniu 0,
- `relative_day:po`: **zmiana trendu** po wydarzeniu.

**Intuicja i przykład.** Proste porównanie przed / po nie odróżni dwóch sytuacji:
- hejt rósł powoli już przed wydarzeniem i po prostu rośnie dalej (fałszywy efekt),
- hejt był stały, a w dniu 0 skoczył (prawdziwy efekt).

ITS je odróżnia: w pierwszej sytuacji `po` wychodzi ok. 0, w drugiej istotnie dodatnio.

**Dlaczego tutaj.** Wspiera H1: pokazuje, czy zmiana zaczyna się w dniu wydarzenia.

**Uwaga.** Przy 7 dniach „przed” trend przed jest szacowany z niewielu punktów. ITS traktujemy jako uzupełnienie, nie test główny.

---

## 10. Test placebo

**Co to jest.** Udajemy, że wydarzenie było w innym dniu, w którym nic się nie stało, i liczymy ten sam efekt.

**Przykład.** W danych ±28 Wykopu i Bluesky ustawiamy fałszywy dzień 0 na −14 i porównujemy dni −21..−15 z dniami −14..−1. Wszystko dzieje się przed prawdziwym wydarzeniem.

**Dlaczego tutaj.** Jeśli „efekt” wychodzi także w dniu bez wydarzenia, to znaczy, że hejt fluktuuje sam z siebie i nasz efekt może być przypadkowy. Jeśli placebo wychodzi nieistotne, a prawdziwe wydarzenie istotne, to mocny argument za H1.

**Uwaga.** Na YT nie ma danych sprzed −7, więc placebo jest tylko dla Wykopu i Bluesky.

---

## 11. Test znaków i test permutacyjny

**Test znaków.** Liczymy, ile komórek ma wzrost, a ile spadek. Gdyby wydarzenia nie miały wpływu, wzrost i spadek byłyby jak rzut monetą. Test sprawdza, czy np. 13 wzrostów na 16 to za dużo jak na przypadek (p ≈ 0,02). Ignoruje wielkość zmian, więc jest bardzo odporny, ale ma niewielką moc.

**Test permutacyjny.** Sprawdza, czy zróżnicowanie efektów między typami wydarzeń mogło powstać przez przypadek:
1. Liczymy statystykę dla prawdziwego przypisania typów (np. różnicę średnich log-OR: kryminalne vs reszta).
2. Przetasowujemy etykiety typu między 7 wydarzeniami na wszystkie możliwe sposoby (przy 3 vs 4 to 35 przypisań).
3. Dla każdego przetasowania liczymy tę samą statystykę.
4. p = jaka część przetasowań daje statystykę co najmniej tak skrajną jak prawdziwa.

**Dlaczego tutaj.** Przy 7 wydarzeniach nie możemy polegać na założeniu rozkładu normalnego. Test permutacyjny daje dokładne p bez tego założenia. Uwaga: przy 35 przypisaniach najmniejsze możliwe p to 1/35 ≈ 0,029 (a w praktyce często 2/35 ≈ 0,057), więc test ma ograniczoną moc. To kolejny powód, żeby H2 opisywać ostrożnie.

**Uwaga.** Etykiety tasujemy między **wydarzeniami**, nie komórkami, bo typ jest cechą wydarzenia. Wszystkie komórki jednego wydarzenia dostają ten sam typ.

---

## 12. Szeregi dzienne: średnia krocząca, indeks, średnia dzienna

**Średnia krocząca 3-dniowa.** Wartość dla dnia *d* to średnia z dni *d−1, d, d+1*. Wygładza przypadkowe wahania z dnia na dzień i ułatwia zobaczenie trendu.

**Indeks względem średniej „przed”.** Indeks = % w danym dniu / średni % w okresie przed.
- 1,0 = taki sam poziom jak przed,
- 1,5 = o 50% więcej niż przed.

Pozwala pokazać na jednym wykresie platformy o różnych poziomach (np. Wykop 14% i YT 2%): obie startują z 1,0.

**Średnia dzienna przy asymetrycznym oknie.** Okres „przed” ma 7 dni, „po” 15. Suma komentarzy „po” jest więc większa nawet bez efektu. Średnia dzienna (suma / liczba dni) usuwa ten problem. Odsetków to nie dotyczy, bo są już ilorazami.

**Uwaga.** Dzień z kilkunastoma komentarzami daje bardzo niepewny %. Dlatego pod wykresami pokazujemy liczbę komentarzy dziennie.

---

## 13. Zbalansowany panel

**Zbalansowany panel vs wszystkie komórki.**
- **Wszystkie komórki (16):** więcej danych, ale platformy mają różne zestawy wydarzeń (Bluesky tylko 3).
- **Zbalansowany panel (3 × 3 = 9):** te same 3 wydarzenia na każdej platformie.

**Dlaczego to ważne dla H4.** Jeśli Bluesky wypada inaczej w analizie wszystkich komórek, może to wynikać z tego, że ma *inne wydarzenia*, a nie z tego, że jest *inną platformą*. Zbalansowany panel to rozstrzyga.

---

## 14. Analiza słów: stopwordy, lematyzacja, log-odds

**Stopwordy.** Bardzo częste słowa bez treści (*i, że, nie, to, się*) usuwamy przed liczeniem, bo zdominowałyby każdą listę.

**Lematyzacja.** Sprowadzanie słów do formy podstawowej: *imigranci, imigrantów, imigrantami* → *imigrant*. Polski ma bogatą odmianę, więc bez lematyzacji jedno słowo rozpada się na kilka pozycji na liście, a każda ma za małą liczbę wystąpień. Używamy biblioteki `simplemma` (lekka, działa offline). Jest słownikowa, więc rzadkie lub slangowe słowa mogą zostać bez zmian.

**Częstość vs słowa wyróżniające.**
- **Częstość:** jakie słowa są najczęstsze w hejcie. Wada: najczęstsze będą słowa częste w ogóle w dyskusji o migracji (*polska, ludzie, kraj*).
- **Słowa wyróżniające:** jakie słowa są *bardziej typowe* dla hejtu niż dla zwykłej dyskusji o migracji.

**Log-odds z priorytetem Dirichleta (Monroe i in. 2008).** Dla każdego słowa porównuje, jak często występuje w hejcie i w komentarzach o migracji bez hejtu, i zwraca **z-score**:
- duży dodatni z (np. > 3): słowo wyraźnie typowe dla hejtu,
- z bliskie 0: słowo równie częste w obu grupach.

„Priorytet” to poprawka, która nie pozwala rzadkim słowom (2–3 wystąpienia) wskoczyć na szczyt listy tylko przez przypadek. Bez niej słowo użyte raz w hejcie i nigdy poza nim miałoby nieskończony iloraz.

**Unigramy i bigramy.** Unigram to jedno słowo, bigram to para sąsiednich słów (*nielegalni imigranci*). Bigramy łapią zwroty, które pojedyncze słowa gubią.

---

## 15. Leksykon a klasyfikator LLM

**Leksykon** (`src/lexicon/slurs.py`) to lista ok. 55 obelg i kodów zapisanych jako wyrażenia regularne, każda z kategorią i celem.
- **Plus:** wysoka **precyzja** (co znajdzie, jest prawie na pewno obelgą), przejrzystość, każda kategoria jest nazwana.
- **Minus:** niskie **pokrycie** (recall): nie złapie hejtu bez konkretnej obelgi, ironii, nowych określeń.

**LLM:**
- **Plus:** rozumie kontekst i hejt bez wulgaryzmów, więc łapie znacznie więcej.
- **Minus:** mniej przejrzysty, może się mylić w obie strony, nie podaje kategorii.

**Dlaczego oba.** LLM daje etykietę hejtu (czy komentarz jest hejtem). Leksykon daje **kategorie** obelg (jak ktoś hejtuje). Dlatego przy kategoriach zawsze podajemy, jaki % hejtu w ogóle zawiera termin z leksykonu: rozkład kategorii opisuje tylko tę część.

---

## 16. Koncentracja: Lorenz, Gini, top k%

**Krzywa Lorenza.** Sortujemy autorów od tych, którzy napisali najmniej, do tych, którzy napisali najwięcej. Na osi X skumulowany % autorów, na osi Y skumulowany % komentarzy.
- Gdyby każdy napisał tyle samo, krzywa byłaby przekątną.
- Im bardziej krzywa wygina się poniżej przekątnej, tym bardziej pisanie jest skupione w rękach nielicznych.

**Współczynnik Giniego.** Jedna liczba opisująca krzywą Lorenza: od 0 (wszyscy piszą tyle samo) do 1 (jedna osoba pisze wszystko).

**Udział top k%.** Najbardziej konkretna miara.

**Przykład.** „Top 1% autorów hejtu napisał 30% hejtu” znaczy, że na 1000 osób piszących hejt 10 najaktywniejszych odpowiada za prawie jedną trzecią całości.

**Dlaczego punkt odniesienia.** Aktywność w internecie jest zawsze skoncentrowana: niewielu ludzi pisze dużo, większość mało. Sama informacja „hejt jest skoncentrowany” nic nie mówi. Pytanie brzmi: czy hejt jest **bardziej** skoncentrowany niż zwykłe komentowanie? Dlatego zawsze porównujemy z koncentracją wszystkich komentarzy.

---

## 17. Polubienia: Mann-Whitney i model ujemny dwumianowy

**Problem z polubieniami.** Rozkład jest bardzo skośny: mediana 1, ale pojedyncze komentarze mają tysiące polubień. Średnia jest wtedy zdominowana przez kilka hitów, a testy zakładające rozkład normalny nie działają.

**Test Manna-Whitneya.** Porównuje *rangi*, a nie wartości: sprawdza, czy losowy komentarz z hejtem ma zwykle więcej polubień niż losowy komentarz bez hejtu. Jeden komentarz z 20 tys. polubień nie zmieni wyniku. Wynik można podać jako prawdopodobieństwo przewagi, np. 0,55: w 55% par hejt ma więcej polubień.

**Model ujemny dwumianowy (NB).** Regresja dla liczb (0, 1, 2, …), która dopuszcza **nadmierną dyspersję**, czyli wariancję dużo większą niż średnia, typową dla polubień. Zwykły model Poissona zakłada wariancję = średnia i przy polubieniach dawałby za wąskie przedziały.

`likes ~ hate_migrant + C(wydarzenie)` daje **stosunek średnich**.

**Przykład.** Stosunek 1,3: komentarz z hejtem ma średnio o 30% więcej polubień niż komentarz bez hejtu w tym samym wydarzeniu. `C(wydarzenie)` kontroluje to, że przy niektórych wydarzeniach wszyscy dostawali więcej polubień.

**Dlaczego oba.** Mann-Whitney odpowiada na pytanie „czy typowy hejt jest bardziej lubiany”, a NB na pytanie „o ile więcej polubień średnio”. Jeśli oba wskazują ten sam kierunek, wniosek jest mocny.

**Uwaga na Wykopie.** `votes` to głosy w górę minus w dół, więc mogą być ujemne. Testy rangowe radzą sobie z tym bez problemu. Model NB wymaga liczb nieujemnych, więc tam przycinamy ujemne wartości do 0.
