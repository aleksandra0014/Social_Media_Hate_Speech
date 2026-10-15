# Codebook: mowa nienawiści wobec migrantów

**Wersja 0.3 · 2026-10-15 · do pilotażu**

Codebook opisuje, jak zamienić komentarz z mediów społecznościowych na jedną etykietę: **czy komentarz jest mową nienawiści wobec migrantów (1), czy nie (0)**. Celem jest, żeby każda osoba kodująca ten sam komentarz przypisała mu tę samą wartość. Etykiety tworzą zbiór referencyjny (gold standard), na którym sprawdzana jest trafność automatycznego klasyfikatora.

Reguły i przykłady powstały na podstawie komentarzy z Wykopu i Bluesky zebranych wokół wydarzeń z `events.json`. Przykłady są **parafrazami**, a nie cytatami, bo cytat można wyszukać i odnaleźć autora.

---

## 1. Zakres

**Kodowane jest** tylko jedno zjawisko: wrogość wobec migrantów jako ludzi, ze względu na ich pochodzenie lub status.

**Nie jest kodowane:**
- czy komentarz jest wulgarny lub obraźliwy w ogóle,
- czy dotyczy migracji jako tematu,
- poglądy polityczne autora,
- wrogość wobec innych grup (np. polityków, użytkowników, innych mniejszości).

Takie komentarze, nawet bardzo agresywne, dostają `0`.

## 2. Jednostka analizy i materiał

- **Jednostka:** jeden komentarz, czyli wiersz arkusza.
- **Kolumny z danymi** (tylko do odczytu):

| Kolumna | Zawartość |
|---|---|
| `item_id` | identyfikator komentarza w arkuszu |
| `context_post` | tytuł lub początek wpisu, pod którym padł komentarz |
| `context_parent` | komentarz, na który ten odpowiada (puste, jeśli to komentarz bezpośrednio pod wpisem) |
| `context_quote` | fragment innego komentarza, który autor zacytował (na platformie oznaczony `>`); puste, jeśli autor nikogo nie cytuje |
| `text` | komentarz do zakodowania: tylko słowa autora, bez cytatu |

- **Oznaczenia w tekście:**
  - `[link]`, `@[user]`, `[email]`, `[phone]` to zamaskowane linki, wzmianki i dane kontaktowe,
  - `@[user]:` na początku komentarza oznacza odpowiedź do innego użytkownika,
  - słowa wykropkowane przez platformę (`k---a`, `j-----ć`) czytaj jak pełne.
- **Klasyfikator ocenia ten sam tekst** (`text`), ale bez wzmianek, linków i emoji, z „lenny face” zamienioną na `[lenny]`. Cytaty z `context_quote` nie trafiają do klasyfikatora.

## 3. Zmienne kodowane

| Zmienna | Wartości | Obowiązkowa | Definicja |
|---|---|---|---|
| `hate` | `1` / `0` | tak | Czy komentarz jest mową nienawiści wobec migrantów (pkt 3.1 i 3.2). |
| `uncertain` | `1` / puste | nie | Wpisz `1`, jeśli wybierając wartość `hate`, nie masz pewności. |
| `note` | tekst | gdy `uncertain=1` | Jedno zdanie: co budzi wątpliwość albo dlaczego przypadek jest nietypowy. |

### 3.1 `hate = 1`: mowa nienawiści wobec migrantów

Komentarz dostaje `1`, gdy autor **ze względu na pochodzenie, narodowość, rasę, religię lub status migranta albo uchodźcy** robi co najmniej jedną z poniższych rzeczy:

| Kryterium | Opis | Przykład (parafraza) |
|---|---|---|
| **Obelga** | wyzwisko etniczne, rasowe lub religijne, także zniekształcone | „znowu ciapaki na dworcu”, „ukry wszędzie” |
| **Dehumanizacja** | przedstawia ludzi jako zwierzęta, robactwo, chorobę, śmieci, broń, najazd | „to nie uchodźcy, to szarańcza” |
| **Stereotyp / generalizacja** | przypisuje całej grupie negatywne cechy | „oni się nie nadają do pracy, tylko do socjalu” |
| **Wykluczenie** | wzywa do wydalenia, izolacji lub odebrania praw **całej grupie** albo to pochwala | „wywieźć wszystkich, kobiety i dzieci też” |
| **Przemoc** | grozi przemocą, wzywa do niej albo ją pochwala | „na granicy powinni strzelać” |
| **Kod / ironia** | robi któreś z powyższych za pomocą kodu, ironii lub memu, gdy intencja jest czytelna | „nie molestował, tylko ubogacał kulturowo” |

**Migranci** to w tym badaniu:
- migranci, imigranci, uchodźcy, osoby ubiegające się o azyl, cudzoziemcy przyjeżdżający do Polski lub Europy albo w nich mieszkający,
- **Ukraińcy** jako ludzie i naród, w tym uchodźcy z Ukrainy,
- grupy kojarzone w dyskusji z migracją: muzułmanie, Arabowie, osoby z Afryki, osoby czarnoskóre i „śniade”, a także pracownicy z Azji, Gruzji, Ameryki Łacińskiej.

Wulgaryzm **nie jest konieczny**: grzecznie sformułowany stereotyp to `1`.

### 3.2 `hate = 0`: brak mowy nienawiści wobec migrantów

Komentarz dostaje `0`, gdy:
- nie wyraża wrogości wobec migrantów (jest neutralny, informacyjny, życzliwy albo dotyczy czegoś innego),
- krytykuje **politykę migracyjną, decyzję, ustawę, rząd, UE, państwo** (także państwo ukraińskie i jego władze), ale nie atakuje ludzi ze względu na pochodzenie,
- atakuje **konkretną osobę za jej czyn**, bez uogólnienia na grupę i bez wyzwisk etnicznych,
- atakuje **inną grupę** niż migranci: polityków, innych użytkowników, „lewaków”, „faszystów”, osoby LGBT+,
- **cytuje lub relacjonuje** cudzą nienawiść, żeby ją skrytykować albo ośmieszyć (kontrmowa),
- jest nie po polsku, nieczytelny albo składa się z samych emotikon. Wtedy wpisz też `uncertain=1` i `note=nieczytelny` albo `note=jezyk`.

## 4. Zasady kodowania

1. **Oceniaj słowa autora.** Cytat z innego komentarza jest w `context_quote` i nie wpływa na kod. Tak samo pomiń tekst w cudzysłowie przytoczony po to, żeby go skrytykować.
2. **Kontekst służy tylko do ustalenia, o kim jest komentarz.** `context_post`, `context_parent` i `context_quote` mówią, kto jest adresatem. To, czy komentarz jest nienawistny, wynika z samego komentarza. Neutralna odpowiedź pod nienawistnym wpisem dostaje `0`.
3. **Wystarczy jeden fragment.** Jeśli choć jedno zdanie spełnia kryterium z pkt 3.1, wpisz `1`, nawet gdy reszta komentarza jest neutralna.
4. **Krytyka** **jednej** osoby za to, co zrobiła, to `0`. Ta sama krytyka z uogólnieniem („typowe dla nich”, „wszyscy tacy”) albo z wyzwiskiem etnicznym to `1`.
5. **Ludzie czy decyzja albo państwo?** Wrogość wobec rządu, ustawy, paktu czy państwa ukraińskiego to `0`. Jeśli autor przenosi ją na ludzi („…i Ukraińcy są tacy sami”), wpisz `1`.
6. **Ironia:** jeśli z tekstu jasno wynika, że ironia wyraża wrogość wobec migrantów, wpisz `1`. Jeśli ironia jest skierowana przeciwko rasistom albo jej kierunku nie da się ustalić, wpisz `0` (w drugim przypadku z `uncertain=1`).
7. **Pytania liczą się jak twierdzenia.** Pytanie retoryczne z uogólnieniem („czemu oni zawsze wyglądają na upośledzonych?”) to `1`. Pytanie zawierające wyzwisko („popierasz wpuszczanie nachodźców?”) też.
8. **Forma nie przesądza.** Wulgaryzm nie wystarcza do `1`, a jego brak nie wyklucza `1`.
9. **Nie zgaduj ukrytych intencji.** Koduj to, co da się odczytać z tekstu. Nie dopowiadaj, „co autor na pewno miał na myśli”.
10. **Nie korzystaj z niczego poza arkuszem.** Nie szukaj wpisu na platformie i nie sprawdzaj autora. Platforma ani poglądy autora nie wpływają na kod.
11. **Wątpliwość:** wybierz najbardziej oczywiste odczytanie, wpisz `uncertain=1` i jednym zdaniem opisz problem w `note`. Nie zostawiaj pustego `hate`.

## 5. Kolejność decyzji

```
1. Czy AUTOR (nie cytat) wyraża wrogość lub negatywną ocenę wobec ludzi?   nie -> 0
2. Czy adresatem są migranci (pkt 3.1)?                                    nie -> 0
3. Czy chodzi o ludzi z powodu pochodzenia lub statusu,
   a nie o czyn konkretnej osoby, decyzję albo państwo?                     nie -> 0
4. Czy spełnione jest któreś kryterium: obelga, dehumanizacja,
   stereotyp, wykluczenie, przemoc, kod/ironia?                              tak -> 1, nie -> 0
Jeśli uważasz że nie da się rozstrzygnąć -> wybierz najbardziej oczywiste, intuicyjne odczytanie + uncertain=1
```

## 6. Przypadki graniczne: jak rozstrzygać

| Sytuacja | `hate` | Uzasadnienie |
|---|---|---|
| Krytyka polityki („pakt migracyjny to błąd”, „granica musi być szczelna”) | 0 | dotyczy decyzji, nie ludzi |
| Opinia o skali migracji bez wrogości („są w porządku, ale jest ich za dużo”) | 0, `uncertain=1` | brak obelgi i uogólnienia, ale blisko granicy; do omówienia po pilotażu |
| Deportacja **konkretnego** sprawcy („za pobicie od razu deportacja”) | 0 | dotyczy czynu |
| Wydalenie **wszystkich** („niech wracają, skąd przyszli”) | 1 | wykluczenie grupy |
| Sprawca + uogólnienie („u nich to normalne”) | 1 | stereotyp |
| Wyzwisko etniczne wobec jednej osoby („kogo obchodzi jakiś banderowiec” o zmarłym Ukraińcu) | 1 | atak z powodu pochodzenia |
| Samo „wypierdalaj / won” jako **odpowiedź do użytkownika** (`@[user]:` albo jest `context_parent`) | 0 | adresatem jest rozmówca |
| Samo „wypierdalać / won” **bezpośrednio pod wpisem** o przybyciu migrantów albo o przestępstwie migranta | 1, `uncertain=1` | odnosi się do grupy z wpisu; wykluczenie |
| Jak wyżej, ale wpis jest o polityku lub decyzji („premier ogłasza strategię”) | 0, `uncertain=1` | najbliższym adresatem jest polityk |
| Atak na polityków lub aktywistów z dehumanizacją migrantów („zdrajcy wpuszczają tę dzicz”) | 1 | dehumanizacja migrantów, choć głównym adresatem jest kto inny |
| Kontrmowa cytująca obelgę („ci, co krzyczą do Ukraińców »wypierdalać«, nigdy nie pomogli”) | 0 | autor potępia nienawiść |
| Kontrmowa z wyzwiskiem wobec hejterów („faszyści”, „bydlaki”) | 0 | atak na sprawców, nie na migrantów |
| „Polska dla Polaków, stop ukrainizacji” | 1 | hasło wykluczenia |
| „Polska dla Polaków, Anglia dla Anglików… i Polaków” | 0 | ironia wobec nacjonalistów (podwójne standardy) |
| „Banderowcy”, „UPA” w dyskusji historycznej (Wołyń, ekshumacje) | 0 | temat historyczny, bez przenoszenia na dzisiejszych Ukraińców |
| „Banderowcy” jako nazwa dzisiejszych Ukraińców | 1 | obelga |
| „Banderowska onuca” albo „rublarz” jako wyzwisko dla użytkownika | 0 | wyzwisko polityczne wobec rozmówcy |
| Wrogość wobec państwa ukraińskiego lub władz („państwo mafijne”) | 0 | państwo, nie ludzie |
| Rosjanie jako strona wojny („kacapy”, „orkowie”) | 0 | poza zakresem badania |
| Statystyka przestępczości podana rzeczowo | 0 | informacja |
| Statystyka jako dowód, że „oni” są gorsi („liczby pokazują, że to dzikusy”) | 1 | dehumanizacja i stereotyp |
| Doświadczenie osobiste bez uogólnienia („pracowałem z Ukraińcami, różnie bywało”) | 0 | relacja |
| Doświadczenie osobiste z uogólnieniem („pracowałem z nimi, wszyscy leniwi”) | 1 | stereotyp |
| „Nie jestem rasistą, ale…” + stereotyp | 1 | zastrzeżenie nie zmienia treści |
| Zastrzeżenie „nie wszyscy, ale większość z nich to…” + negatywna cecha | 1 | generalizacja na większość grupy |
| Nienawiść wobec innej grupy bez wątku migracji | 0 | poza zakresem badania |

## 7. Przykłady

Przykłady są parafrazami komentarzy z danych.

### 7.1 Typowe

| Komentarz (kontekst) | `hate` | Dlaczego |
|---|---|---|
| „Kolejni ciapaci na socjalu, a Polak haruje.” | 1 | obelga + stereotyp |
| (wpis o ataku nożem) „No i ubogacił kulturowo.” | 1 | kod / ironia |
| „To nie ludzie, to broń Łukaszenki. Wszystkich bez wyjątku won, dzieci też.” | 1 | dehumanizacja + wykluczenie |
| „Z Afryki nie przyjadą inżynierowie, tylko agresja i niskie IQ.” | 1 | stereotyp |
| „Ukry się panoszą i jeszcze wymagają.” | 1 | obelga + stereotyp |
| „Strategia migracyjna rządu to pic na wodę.” | 0 | krytyka polityki |
| „Pani w sklepie z Ukrainy zawsze miła, pozdrawiam.” | 0 | życzliwy:) |
| „W 2025 r. deportowano o 300% więcej osób niż w 2023.” | 0 | informacja |
| „@[user]: won za Ural, ruski trollu.” | 0 | wyzwisko wobec użytkownika |
| „Ci, co biją Ukraińców za akcent, to zwykłe bydlaki.” | 0 | kontrmowa |

### 7.2 Nietypowe

| Komentarz (kontekst) | `hate` | Dlaczego |
|---|---|---|
| `context_quote`: „Dziś w mieście widziałem samych murzynów i ciapaków” · `text`: „@[user]: Ło matko, solidna podstawa światopoglądu xD” | 0 | obelgi są w cytacie; autor z nich kpi |
| „Czemu oni zawsze siedzą w kapturach w pomieszczeniu?” | 0, `uncertain=1` | pytanie bez wyraźnego uogólnienia negatywnego; zależy od kontekstu |
| „Czemu oni zawsze wyglądają, jakby byli upośledzeni?” | 1 | pytanie retoryczne z dehumanizującym uogólnieniem |
| „@[user]: popierasz wpuszczanie tutaj nachodźców?” | 1 | pytanie do użytkownika, ale grupa nazwana obelgą |
| „Kogo obchodzi jakiś banderowiec.” (wpis: śmierć ukraińskiego biznesmena) | 1 | wyzwisko etniczne wobec osoby, adresat z kontekstu |
| „Mają farta, za pobicie Polaka zwalniają z aresztu, a za suma deportacja xD” | 0 | kpina z wymiaru sprawiedliwości, nie z ludzi |
| „Psychoprawica nie wie, czy chwalić sprawcę za atak na LGBT, czy gnębić za islam – pewnie skleją »je**ć LGBT i ciapatych«.” | 0 | obelga przytoczona, żeby ośmieszyć prawicę |
| „Ukraina to nasz wróg, tak samo jak Rosja, kraje mafijne.” | 0, `uncertain=1` | wrogość wobec państwa; granica z ludźmi niejasna |
| „Szkoda tych ludzi, ale to nie znaczy, że mają się tu panoszyć i wymagać.” | 1, `uncertain=1` | łagodny stereotyp „roszczeniowych” Ukraińców |
| „1. Wrocław 2. Ukrainiec 3. Pijany 4. Awantura 5. Robi z siebie ofiarę xD” | 1 | ironiczna „lista” sugerująca stały schemat zachowania grupy |

## 8. Słownik kodów spotykanych w danych

Te słowa **same nie przesądzają** o kodzie. Pomagają rozpoznać intencję i znaczą tyle, ile znaczą w zdaniu.

| Kod | Znaczenie w danych | Zwykle |
|---|---|---|
| „ubogacenie (kulturowe)”, „ubogacać”, „ubogacacze” | ironiczne nazwanie przestępstw migrantów | 1 |
| „inżynierowie”, „lekarze” (z Afryki), „nowi Europejczycy” | ironiczne określenie migrantów | 1 |
| „śniadzi (książęta)”, „pigmentodatni”, „czarne …” o ludziach | określenie rasowe | 1 |
| „ciapaci”, „ciapaki”, „brudasy”, „kozojebcy”, „muzole” | wyzwiska etniczne lub religijne | 1 |
| „nachodźcy” | gra słów: uchodźcy jako najeźdźcy | 1 |
| „ukry”, „ukropy”, „ukraccy”, „banderowcy” (o dzisiejszych Ukraińcach) | wyzwiska wobec Ukraińców | 1 |
| „wdzięczność” (sarkastycznie), „panoszą się”, „roszczeniowi” | stereotyp niewdzięcznych Ukraińców | 1, gdy dotyczy grupy |
| „multikulti”, „kebaby” jako nazwa ludzi | pogardliwe określenie społeczeństwa wielokulturowego | zależy od zdania |
| „onuca”, „rublarz”, „kacap”, „ruski agent” | wyzwiska dla prorosyjskich użytkowników lub Rosjan | 0 |
| „faszyści”, „psychoprawica”, „lewactwo”, „lewaki” | wyzwiska polityczne | 0 |

## 9. Procedura i kontrola jakości

1. Wszystkie osoby kodują ten sam zestaw (po 50–100 komentarzy z każdej platformy).
2. Arkusz nie pokazuje platformy, wydarzenia ani trafień słownika. Nie ustalaj ich.
3. **Arkusz:** wartości wybieraj z listy rozwijanej. Nie zmieniaj kolumn z danymi ani nazwy pliku.
4. **Zgodność:**: Zgodność liczy `scripts/annotation_agreement.py` 
5. **Rozbieżności:** omawiane są na spotkaniu zespołu. Decyzję i ewentualną zmianę reguły zapisz poniżej.

## 10. Historia zmian

| Wersja | Data | Zmiana |
|---|---|---|
| 0.1 | 2026-10-14 | Szkic z kodowaniem binarnym, zakres, definicje kategorii 1 i 0, zasady kodowania, kolejność decyzji, przypadki graniczne, przykłady typowe i nietypowe |