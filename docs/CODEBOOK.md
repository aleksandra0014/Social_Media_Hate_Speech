# Codebook: mowa nienawiści wobec migrantów

**Wersja 0.2 · 2026-10-15 · do pilotażu**

Codebook opisuje, jak zamienić komentarz z mediów społecznościowych na dwie etykiety:
- **`hate`:** czy komentarz jest mową nienawiści (hejtem) wobec kogokolwiek (1), czy nie (0),
- **`hate_migrants`:** czy ten hejt jest skierowany do migrantów (1), czy nie (0).

Celem jest, żeby każda osoba kodująca ten sam komentarz przypisała mu te same wartości. Etykiety tworzą zbiór referencyjny (gold standard), na którym sprawdzana jest trafność automatycznego klasyfikatora: `hate` pozwala ocenić klasyfikator ogólnej szkodliwości (np. douczony na BAN-PL), a `hate_migrants` mierzy zjawisko, o które pyta badanie.

Reguły i przykłady powstały na podstawie komentarzy z Wykopu i Bluesky zebranych wokół wydarzeń z `events.json`. Przykłady są **parafrazami**, a nie cytatami, bo cytat można wyszukać i odnaleźć autora.

---

## 1. Zakres

**Kodowane jest:**
- **`hate`:** czy autor atakuje jakąkolwiek osobę lub grupę (użytkownika, polityka, migrantów, inną mniejszość…),
- **`hate_migrants`:** czy atak jest skierowany do migrantów ze względu na ich pochodzenie lub status.

**Nie jest kodowane:**
- czy komentarz dotyczy migracji jako tematu,
- poglądy polityczne autora,
- sam wulgarny język bez adresata („kurwa, ale upał”) – to `hate=0`.

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
| `hate` | `1` / `0` | tak | Czy komentarz jest mową nienawiści wobec kogokolwiek (pkt 3.1). |
| `hate_migrants` | `1` / `0` | tak | Czy ta mowa nienawiści jest skierowana do migrantów (pkt 3.2). Może być `1` tylko przy `hate=1`. |
| `uncertain` | `1` / puste | nie | Wpisz `1`, jeśli przy którejś z etykiet nie masz pewności. |
| `note` | tekst | gdy `uncertain=1` | Jedno zdanie: co budzi wątpliwość albo dlaczego przypadek jest nietypowy. |

Dozwolone pary: `0/0`, `1/0`, `1/1`. Para `0/1` jest błędem i trafi do raportu problemów.

### 3.1 `hate = 1`: mowa nienawiści wobec kogokolwiek

Komentarz dostaje `hate=1`, gdy autor atakuje **konkretną osobę albo grupę** i robi co najmniej jedną z poniższych rzeczy:

| Kryterium | Opis | Przykład (parafraza) |
|---|---|---|
| **Obelga** | wyzwisko wobec osoby lub grupy (osobiste, polityczne, etniczne, rasowe, religijne), także zniekształcone | „idioto”, „onuco”, „lewaki”, „ciapaki” |
| **Dehumanizacja** | przedstawia ludzi jako zwierzęta, robactwo, chorobę, śmieci, broń, najazd | „to bydło”, „to nie uchodźcy, to szarańcza” |
| **Stereotyp / generalizacja** | przypisuje całej grupie negatywne cechy | „oni się nie nadają do pracy, tylko do socjalu” |
| **Wykluczenie** | wzywa do wydalenia, izolacji lub odebrania praw **całej grupie** albo to pochwala | „wywieźć wszystkich, kobiety i dzieci też” |
| **Przemoc** | grozi przemocą, wzywa do niej albo ją pochwala | „na granicy powinni strzelać” |
| **Kod / ironia** | robi któreś z powyższych za pomocą kodu, ironii lub memu, gdy intencja jest czytelna | „nie molestował, tylko ubogacał kulturowo” |

Wulgaryzm **nie jest konieczny** (grzeczny stereotyp to `1`) ani **wystarczający** (wulgaryzm bez adresata to `0`). Ostra, ale rzeczowa krytyka („ten minister kłamie”, „ustawa jest fatalna”) to `0`.

### 3.2 `hate_migrants = 1`: mowa nienawiści wobec migrantów

Komentarz dostaje `hate_migrants=1`, gdy ma `hate=1` i atak jest skierowany do migrantów **ze względu na ich pochodzenie, narodowość, rasę, religię lub status migranta albo uchodźcy**. Wystarczy jeden fragment wymierzony w migrantów, nawet jeśli komentarz atakuje też kogoś innego.

**Migranci** to w tym badaniu:
- migranci, imigranci, uchodźcy, osoby ubiegające się o azyl, cudzoziemcy przyjeżdżający do Polski lub Europy albo w nich mieszkający,
- **Ukraińcy** jako ludzie i naród, w tym uchodźcy z Ukrainy,
- grupy kojarzone w dyskusji z migracją: muzułmanie, Arabowie, osoby z Afryki, osoby czarnoskóre i „śniade”, a także pracownicy z Azji, Gruzji, Ameryki Łacińskiej.

### 3.3 Kiedy `0`

`hate=0` (a więc także `hate_migrants=0`), gdy komentarz:
- nikogo nie atakuje (jest neutralny, informacyjny, życzliwy),
- jest wulgarny, ale bez adresata,
- krytykuje **decyzję, ustawę, politykę, państwo** rzeczowo, bez obelg i uogólnień o ludziach,
- **cytuje lub relacjonuje** cudzą nienawiść, żeby ją skrytykować albo ośmieszyć (kontrmowa bez własnych wyzwisk),
- jest nie po polsku, nieczytelny albo składa się z samych emotikon. Wtedy wpisz też `uncertain=1` i `note=nieczytelny` albo `note=jezyk`.

`hate=1`, ale `hate_migrants=0`, gdy atak dotyczy **kogoś innego niż migranci**: innego użytkownika, polityka, partii, „lewaków”, „faszystów”, Rosjan jako strony wojny, osób LGBT+ – albo migranta **za jego czyn**, bez odwołania do pochodzenia (np. wyzwisko „bandyta” wobec sprawcy bez uogólnienia na grupę).

## 4. Zasady kodowania

1. **Oceniaj słowa autora.** Cytat z innego komentarza jest w `context_quote` i nie wpływa na kod. Tak samo pomiń tekst w cudzysłowie przytoczony po to, żeby go skrytykować.
2. **Kontekst służy tylko do ustalenia, o kim jest komentarz.** `context_post`, `context_parent` i `context_quote` mówią, kto jest adresatem. To, czy komentarz jest nienawistny, wynika z samego komentarza. Neutralna odpowiedź pod nienawistnym wpisem dostaje `0/0`.
3. **Wystarczy jeden fragment.** Jeśli choć jedno zdanie spełnia kryterium z pkt 3.1, wpisz `hate=1`; jeśli choć jedno takie zdanie dotyczy migrantów, wpisz też `hate_migrants=1`.
4. **Osoba czy grupa?** Krytyka jednej osoby za to, co zrobiła, to `0/0`. Wyzwisko wobec niej to `1/0`. Uogólnienie na grupę („typowe dla nich”, „wszyscy tacy”) albo wyzwisko etniczne to `1/1`.
5. **Ludzie czy decyzja albo państwo?** Rzeczowa krytyka rządu, ustawy, paktu czy państwa ukraińskiego to `0/0`. Wyzwiska wobec władz to `1/0`. Jeśli autor przenosi wrogość na ludzi („…i Ukraińcy są tacy sami”), wpisz `1/1`.
6. **Ironia:** jeśli z tekstu jasno wynika, że ironia wyraża wrogość, oceniaj ją jak twierdzenie wprost. Jeśli ironia jest skierowana przeciwko rasistom bez wyzwisk albo jej kierunku nie da się ustalić, wpisz `0/0` (w drugim przypadku z `uncertain=1`).
7. **Pytania liczą się jak twierdzenia.** Pytanie retoryczne z uogólnieniem („czemu oni zawsze wyglądają na upośledzonych?”) to `1/1`. Pytanie zawierające wyzwisko grupy („popierasz wpuszczanie nachodźców?”) też.
8. **Forma nie przesądza.** Wulgaryzm nie wystarcza do `hate=1`, a jego brak nie wyklucza `hate=1`.
9. **Nie zgaduj ukrytych intencji.** Koduj to, co da się odczytać z tekstu. Nie dopowiadaj, „co autor na pewno miał na myśli”.
10. **Nie korzystaj z niczego poza arkuszem.** Nie szukaj wpisu na platformie i nie sprawdzaj autora. Platforma ani poglądy autora nie wpływają na kod.
11. **Wątpliwość:** wybierz najbardziej oczywiste odczytanie, wpisz `uncertain=1` i jednym zdaniem opisz problem w `note`. Nie zostawiaj pustego `hate` ani `hate_migrants`.

## 5. Kolejność decyzji

```
1. Czy AUTOR (nie cytat) atakuje jakąś osobę lub grupę: obelga, dehumanizacja,
   stereotyp, wykluczenie, przemoc, kod/ironia?           nie -> hate=0, hate_migrants=0 (koniec)
                                                           tak -> hate=1
2. Czy któryś z tych ataków jest skierowany do migrantów (pkt 3.2)
   ze względu na pochodzenie lub status,
   a nie za czyn konkretnej osoby?                          tak -> hate_migrants=1, nie -> hate_migrants=0
Jeśli uważasz, że nie da się rozstrzygnąć -> wybierz najbardziej oczywiste, intuicyjne odczytanie + uncertain=1
```

## 6. Przypadki graniczne: jak rozstrzygać

| Sytuacja | `hate` | `hate_migrants` | Uzasadnienie |
|---|---|---|---|
| Krytyka polityki („pakt migracyjny to błąd”, „granica musi być szczelna”) | 0 | 0 | dotyczy decyzji, nie ludzi |
| Opinia o skali migracji bez wrogości („są w porządku, ale jest ich za dużo”) | 0, `uncertain=1` | 0 | brak obelgi i uogólnienia, ale blisko granicy; do omówienia po pilotażu |
| Sam wulgaryzm bez adresata („kurwa, znowu to samo”) | 0 | 0 | nikt nie jest atakowany |
| Deportacja **konkretnego** sprawcy („za pobicie od razu deportacja”) | 0 | 0 | dotyczy czynu |
| Wyzwisko wobec **konkretnego** sprawcy bez odwołania do pochodzenia („bandyta, niech gnije w więzieniu”) | 1 | 0 | atak za czyn, nie za pochodzenie |
| Wydalenie **wszystkich** („niech wracają, skąd przyszli”) | 1 | 1 | wykluczenie grupy |
| Sprawca + uogólnienie („u nich to normalne”) | 1 | 1 | stereotyp |
| Wyzwisko etniczne wobec jednej osoby („kogo obchodzi jakiś banderowiec” o zmarłym Ukraińcu) | 1 | 1 | atak z powodu pochodzenia |
| Samo „wypierdalaj / won” jako **odpowiedź do użytkownika** (`@[user]:` albo jest `context_parent`) | 1 | 0 | atak na rozmówcę |
| Samo „wypierdalać / won” **bezpośrednio pod wpisem** o przybyciu migrantów albo o przestępstwie migranta | 1 | 1, `uncertain=1` | odnosi się do grupy z wpisu; wykluczenie |
| Jak wyżej, ale wpis jest o polityku lub decyzji („premier ogłasza strategię”) | 1 | 0, `uncertain=1` | najbliższym adresatem jest polityk |
| Atak na polityków lub aktywistów z dehumanizacją migrantów („zdrajcy wpuszczają tę dzicz”) | 1 | 1 | dehumanizacja migrantów, choć głównym adresatem jest kto inny |
| Kontrmowa cytująca obelgę („ci, co krzyczą do Ukraińców »wypierdalać«, nigdy nie pomogli”) | 0 | 0 | autor potępia nienawiść, sam nikogo nie wyzywa |
| Kontrmowa z wyzwiskiem wobec hejterów („faszyści”, „bydlaki”) | 1 | 0 | atak na sprawców, nie na migrantów |
| „Polska dla Polaków, stop ukrainizacji” | 1 | 1 | hasło wykluczenia |
| „Polska dla Polaków, Anglia dla Anglików… i Polaków” | 0 | 0 | ironia wobec nacjonalistów (podwójne standardy), bez wyzwisk |
| „Banderowcy”, „UPA” w dyskusji historycznej (Wołyń, ekshumacje) | 0 | 0 | temat historyczny, bez przenoszenia na dzisiejszych Ukraińców |
| „Banderowcy” jako nazwa dzisiejszych Ukraińców | 1 | 1 | obelga |
| „Banderowska onuca” albo „rublarz” jako wyzwisko dla użytkownika | 1 | 0 | wyzwisko polityczne wobec rozmówcy |
| Rzeczowa wrogość wobec państwa ukraińskiego („państwo, które nas nie szanuje”) | 0 | 0 | państwo, nie ludzie |
| Wyzwiska wobec władz Ukrainy („Zełenski to złodziej i błazen”) | 1 | 0 | atak na polityka, nie na migrantów |
| Rosjanie jako strona wojny („kacapy”, „orkowie”) | 1 | 0 | obelga, ale poza grupą migrantów |
| Statystyka przestępczości podana rzeczowo | 0 | 0 | informacja |
| Statystyka jako dowód, że „oni” są gorsi („liczby pokazują, że to dzikusy”) | 1 | 1 | dehumanizacja i stereotyp |
| Doświadczenie osobiste bez uogólnienia („pracowałem z Ukraińcami, różnie bywało”) | 0 | 0 | relacja |
| Doświadczenie osobiste z uogólnieniem („pracowałem z nimi, wszyscy leniwi”) | 1 | 1 | stereotyp |
| „Nie jestem rasistą, ale…” + stereotyp o migrantach | 1 | 1 | zastrzeżenie nie zmienia treści |
| Zastrzeżenie „nie wszyscy, ale większość z nich to…” + negatywna cecha | 1 | 1 | generalizacja na większość grupy |
| Nienawiść wobec innej grupy bez wątku migracji (np. osoby LGBT+) | 1 | 0 | hejt, ale nie wobec migrantów |

## 7. Przykłady

Przykłady są parafrazami komentarzy z danych.

### 7.1 Typowe

| Komentarz (kontekst) | `hate` | `hate_migrants` | Dlaczego |
|---|---|---|---|
| „Kolejni ciapaci na socjalu, a Polak haruje.” | 1 | 1 | obelga + stereotyp |
| (wpis o ataku nożem) „No i ubogacił kulturowo.” | 1 | 1 | kod / ironia |
| „To nie ludzie, to broń Łukaszenki. Wszystkich bez wyjątku won, dzieci też.” | 1 | 1 | dehumanizacja + wykluczenie |
| „Z Afryki nie przyjadą inżynierowie, tylko agresja i niskie IQ.” | 1 | 1 | stereotyp |
| „Ukry się panoszą i jeszcze wymagają.” | 1 | 1 | obelga + stereotyp |
| „@[user]: won za Ural, ruski trollu.” | 1 | 0 | wyzwisko wobec użytkownika |
| „Ci, co biją Ukraińców za akcent, to zwykłe bydlaki.” | 1 | 0 | kontrmowa z wyzwiskiem wobec sprawców |
| „Strategia migracyjna rządu to pic na wodę.” | 0 | 0 | krytyka polityki |
| „Pani w sklepie z Ukrainy zawsze miła, pozdrawiam.” | 0 | 0 | życzliwy |
| „W 2025 r. deportowano o 300% więcej osób niż w 2023.” | 0 | 0 | informacja |

### 7.2 Nietypowe

| Komentarz (kontekst) | `hate` | `hate_migrants` | Dlaczego |
|---|---|---|---|
| `context_quote`: „Dziś w mieście widziałem samych murzynów i ciapaków” · `text`: „@[user]: Ło matko, solidna podstawa światopoglądu xD” | 0 | 0 | obelgi są w cytacie; autor kpi z rozmówcy, ale go nie wyzywa |
| „Czemu oni zawsze siedzą w kapturach w pomieszczeniu?” | 0, `uncertain=1` | 0 | pytanie bez wyraźnego uogólnienia negatywnego; zależy od kontekstu |
| „Czemu oni zawsze wyglądają, jakby byli upośledzeni?” | 1 | 1 | pytanie retoryczne z dehumanizującym uogólnieniem |
| „@[user]: popierasz wpuszczanie tutaj nachodźców?” | 1 | 1 | pytanie do użytkownika, ale grupa nazwana obelgą |
| „Kogo obchodzi jakiś banderowiec.” (wpis: śmierć ukraińskiego biznesmena) | 1 | 1 | wyzwisko etniczne wobec osoby, adresat z kontekstu |
| „Mają farta, za pobicie Polaka zwalniają z aresztu, a za suma deportacja xD” | 0 | 0 | kpina z wymiaru sprawiedliwości, nikt nie jest wyzywany |
| „Psychoprawica nie wie, czy chwalić sprawcę za atak na LGBT, czy gnębić za islam – pewnie skleją »je**ć LGBT i ciapatych«.” | 1 | 0 | obelga wobec migrantów jest przytoczona; własne wyzwisko („psychoprawica”) dotyczy prawicy |
| „Ukraina to nasz wróg, tak samo jak Rosja, kraje mafijne.” | 0, `uncertain=1` | 0 | wrogość wobec państwa; granica z ludźmi niejasna |
| „Szkoda tych ludzi, ale to nie znaczy, że mają się tu panoszyć i wymagać.” | 1, `uncertain=1` | 1 | łagodny stereotyp „roszczeniowych” Ukraińców |
| „1. Wrocław 2. Ukrainiec 3. Pijany 4. Awantura 5. Robi z siebie ofiarę xD” | 1 | 1 | ironiczna „lista” sugerująca stały schemat zachowania grupy |

## 8. Słownik kodów spotykanych w danych

Te słowa **same nie przesądzają** o kodzie. Pomagają rozpoznać intencję i znaczą tyle, ile znaczą w zdaniu.

| Kod | Znaczenie w danych | Zwykle `hate` / `hate_migrants` |
|---|---|---|
| „ubogacenie (kulturowe)”, „ubogacać”, „ubogacacze” | ironiczne nazwanie przestępstw migrantów | 1 / 1 |
| „inżynierowie”, „lekarze” (z Afryki), „nowi Europejczycy” | ironiczne określenie migrantów | 1 / 1 |
| „śniadzi (książęta)”, „pigmentodatni”, „czarne …” o ludziach | określenie rasowe | 1 / 1 |
| „ciapaci”, „ciapaki”, „brudasy”, „kozojebcy”, „muzole” | wyzwiska etniczne lub religijne | 1 / 1 |
| „nachodźcy” | gra słów: uchodźcy jako najeźdźcy | 1 / 1 |
| „ukry”, „ukropy”, „ukraccy”, „banderowcy” (o dzisiejszych Ukraińcach) | wyzwiska wobec Ukraińców | 1 / 1 |
| „wdzięczność” (sarkastycznie), „panoszą się”, „roszczeniowi” | stereotyp niewdzięcznych Ukraińców | 1 / 1, gdy dotyczy grupy |
| „multikulti”, „kebaby” jako nazwa ludzi | pogardliwe określenie społeczeństwa wielokulturowego | zależy od zdania |
| „onuca”, „rublarz”, „kacap”, „ruski agent” | wyzwiska dla prorosyjskich użytkowników lub Rosjan | 1 / 0 |
| „faszyści”, „psychoprawica”, „lewactwo”, „lewaki” | wyzwiska polityczne | 1 / 0 |

## 9. Procedura i kontrola jakości

1. Wszystkie osoby kodują ten sam zestaw (po 50–100 komentarzy z każdej platformy).
2. Arkusz nie pokazuje platformy, wydarzenia ani trafień słownika. Nie ustalaj ich.
3. **Arkusz:** wartości wybieraj z listy rozwijanej. Nie zmieniaj kolumn z danymi ani nazwy pliku.
4. **Zgodność:** `scripts/annotation_agreement.py` liczy zgodność osobno dla `hate` i `hate_migrants`.
5. **Rozbieżności:** omawiane są na spotkaniu zespołu. Decyzję i ewentualną zmianę reguły zapisz poniżej.

## 10. Historia zmian

| Wersja | Data | Zmiana |
|---|---|---|
| 0.1 | 2026-10-14 | Szkic z kodowaniem binarnym, zakres, definicje kategorii 1 i 0, zasady kodowania, kolejność decyzji, przypadki graniczne, przykłady typowe i nietypowe |
| 0.2 | 2026-10-15 | Dwie zmienne: `hate` (mowa nienawiści wobec kogokolwiek) i `hate_migrants` (skierowana do migrantów); przypadki graniczne, przykłady i słownik z obiema etykietami |
