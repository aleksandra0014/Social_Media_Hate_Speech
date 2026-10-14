# Dane w projekcie: instrukcja DVC

Dane projektu (komentarze z Bluesky, YouTube i Wykopu) **nie są w gicie**. Wersjonujemy je za pomocą **DVC** (Data Version Control), a przechowujemy na wspólnym **Google Drive**.

---

## 1. Jak to działa (w skrócie)

```
repozytorium (git → GitHub)              Google Drive (remote DVC "gdrive")
├── dvc.yaml     – jak powstają dane      files/md5/3f/a91c...   ← właściwe pliki CSV
├── dvc.lock     – hashe danych ──────►   files/md5/7b/02de...
├── params.yaml  – parametry (okna czasowe)
└── data/raw/    – dane (ignorowane przez gita, zarządza nimi DVC)
```

- **Git** przechowuje kod i małe pliki-wskaźniki (`dvc.lock`, `*.dvc`). Wskaźniki mówią, która dokładnie wersja danych jest aktualna.
- **Google Drive** przechowuje same dane. Na Drive zobaczysz foldery o nazwach z hashy zamiast `posts.csv` czy `comments.csv`. **Tak ma być**, bo DVC zapisuje pliki według ich zawartości. Na Drive niczego nie otwieramy ręcznie, dane pobieramy zawsze poleceniem `dvc pull`.
- **`dvc.yaml`** to pipeline. Każdy **etap** (stage) opisuje polecenie, jego wejścia (`deps`, `params`) i wyniki (`outs`).

Struktura danych:
```
data/raw/bluesky/   ← etap collect_bluesky (Ola)
data/raw/youtube/   ← YouTube
data/raw/wykop/     ← Wykop
```

---

## 2. Zanim zaczniesz

Ola musi najpierw:
1. udostępnić Ci folder DVC na Google Drive z rolą **Edytor**,
2. dodać Twój adres Gmail jako **użytkownika testowego** w Google Cloud (Google Auth Platform → Odbiorcy → Użytkownicy testowi),
3. przesłać Ci prywatnie **client secret**. Nigdy nie wklejaj go do repozytorium, README ani kodu.

Bez punktu 2 przy logowaniu zobaczysz błąd `403: access_denied`.

---

## 3. Pierwsza konfiguracja (jednorazowo)

W PowerShellu:

```powershell
git clone https://github.com/aleksandra0014/Social_Media_Hate_Speech.git
cd Social_Media_Hate_Speech

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

dvc remote modify --local gdrive gdrive_client_secret <SECRET_OD_OLI>
dvc pull
```

- `--local` zapisuje sekret w pliku `.dvc/config.local`, który **nie trafia do gita**.
- `dvc pull` otworzy przeglądarkę. Zaloguj się swoim Gmailem. Przy komunikacie „Google nie zweryfikował tej aplikacji” kliknij **Kontynuuj**, a potem zgódź się na dostęp do Google Drive. Logujesz się tylko raz.
- Po zakończeniu dane będą w `data/raw/bluesky/` (11 folderów z wydarzeniami).

Sprawdzenie:
```powershell
dvc status            # "Data and pipelines are up to date."
dvc status --cloud    # "Cache and remote 'gdrive' are in sync."
```

Plik `.env.local` (dane logowania do API) potrzebny jest tylko przy **uruchamianiu** skryptu, który pobiera dane z danej platformy. Do samego korzystania z danych nie jest potrzebny.

---

## 4. Dodawanie własnego skryptu i danych

Przykład dla YouTube. Wykop robisz analogicznie: `scripts/wykop.py`, etap `collect_wykop`, folder `data/raw/wykop`.

### 4.1. Nowa gałąź

```powershell
git checkout main
git pull
dvc pull
git checkout -b youtube
```

### 4.2. Skrypt `scripts/youtube.py`

Trzymamy się tych samych zasad co w `scripts/bluesky.py`:
- argument **`--out`** określa folder wynikowy (domyślnie `data/raw/youtube`);
- parametry, np. okna czasowe, skrypt czyta ze **swojej sekcji w `params.yaml`**;
- klucze API i hasła trzymamy w **`.env.local`**, nigdy w kodzie;
- skrypt pobiera wydarzenia z **`events.json`**.

### 4.3. Sekcja w `params.yaml`

Dopisz pod istniejącą sekcją `bluesky`:
```yaml
youtube:
  days_before: 28
  days_after: 28
```

### 4.4. Etap w `dvc.yaml`

Dopisz pod etapem `collect_bluesky`. Wcięcie musi być takie samo:
```yaml
  collect_youtube:
    cmd: python scripts/youtube.py events.json --out data/raw/youtube
    deps:
      - scripts/youtube.py
      - events.json
    params:
      - youtube
    outs:
      - data/raw/youtube:
          persist: true
```

- `deps` / `params`: gdy zmienisz skrypt, `events.json` albo parametry, DVC oznaczy etap jako nieaktualny.
- `persist: true`: DVC nie usunie istniejących danych przed ponownym uruchomieniem. Pobieranie z API trwa długo, a wyniki z API mogą się zmieniać, więc chcemy zachować to, co już pobrane.

Sprawdzenie: `dvc dag` powinien pokazać oba etapy.

### 4.5. Rejestracja danych w DVC

Wybierz **jedną** z opcji:
```powershell
dvc repro collect_youtube     # danych jeszcze nie ma: DVC uruchomi skrypt i zapisze wynik
dvc commit collect_youtube    # dane już leżą w data/raw/youtube: DVC tylko zapisze ich hashe
```

> **Zawsze podawaj nazwę etapu.** Samo `dvc repro` uruchomi wszystkie nieaktualne etapy, w tym skrypty innych osób, do których nie masz loginów.

### 4.6. Wysłanie zmian

```powershell
git add dvc.yaml dvc.lock params.yaml data/raw/.gitignore scripts/youtube.py requirements.txt
git commit -m "Add YouTube collection stage"
dvc push
git push -u origin youtube
```
Następnie na GitHubie otwórz **Pull Request** do `main`.

### 4.7. Dane bez skryptu (np. ręczny eksport)

Jeśli dane nie pochodzą ze skryptu, zamiast etapu w `dvc.yaml` wystarczy:
```powershell
dvc add data/raw/wykop
git add data/raw/wykop.dvc data/raw/.gitignore
git commit -m "Add Wykop data"
dvc push
git push
```

---

## 5. Codzienna praca

| Kiedy | Polecenia |
|---|---|
| Początek pracy | `git pull` → `dvc pull` |
| Zmiana skryptu / danych / parametrów | `dvc repro <etap>` albo `dvc commit <etap>` |
| Wysyłanie zmian | `git commit` → **`dvc push`** → `git push` |
| Potrzebujesz danych tylko jednej platformy | `dvc pull collect_youtube` |
| Co się zmieniło? | `dvc status`, `dvc dag` |
| Powrót do starszej wersji | `git checkout <commit>` → `dvc checkout` |

> **Złota zasada: najpierw `dvc push`, potem `git push`.**
> W odwrotnej kolejności inni dostaną w gicie wskaźnik na dane, których jeszcze nie ma na Drive.

---

## 6. Konflikty przy scalaniu

Jeśli dwie osoby jednocześnie dodają etapy, przy scalaniu mogą pojawić się konflikty w `dvc.yaml`, `params.yaml` i `dvc.lock`:
1. W **`dvc.yaml`** i **`params.yaml`** zostaw **oba** etapy i obie sekcje.
2. **`dvc.lock`**: weź dowolną wersję, potem `dvc pull` i `dvc commit <brakujący_etap>`. DVC sam uzupełni brakujące hashe.
3. `git commit` → `dvc push` → `git push`.

Najprościej unikać konfliktów tak: scalamy gałęzie **po kolei**, a następna osoba przed dodaniem swojego etapu robi `git pull` i `dvc pull` na `main`.

---

## 7. Najczęstsze problemy

| Objaw | Rozwiązanie |
|---|---|
| `Błąd 403: access_denied` / „Dostęp zablokowany” przy logowaniu | Twojego Gmaila nie ma na liście użytkowników testowych. Napisz do Oli. |
| `ERROR: unexpected error - module 'lib' has no attribute 'GEN_EMAIL'` | Niezgodne wersje bibliotek: `pip install "pyopenssl==24.2.1" "cryptography>=41.0.5,<44"`, potem `pip check` |
| `dvc pull` zgłasza brakujące pliki (`missing cache files`) | Ktoś zrobił `git push` bez `dvc push`. Ta osoba musi wykonać `dvc push`. |
| `WARNING: Unable to find less in the PATH` | Nic się nie stało, można zignorować. |
| W terminalu pojawia się `>>` i polecenie nie działa | Wklejone polecenie zawierało znak nowej linii. Naciśnij Enter jeszcze raz albo wklej je bez nowej linii. |
| Git pokazuje pliki CSV jako nowe | Nie dodawaj ich do gita. Folder musi być śledzony przez DVC (`dvc add` albo etap w `dvc.yaml`). |

---

## 8. Preprocessing tekstów (Bluesky)

Dwa etapy uruchamiane osobno dla każdego wydarzenia z listy `preprocess.events` w `params.yaml` (`foreach` w `dvc.yaml`):

| Etap | Co robi | Wynik |
|---|---|---|
| `filter_bluesky` | odrzuca posty i komentarze: `no_text` (same linki/wzmianki/liczby), `emoji_only`, `very_short` (< `min_words` słów), `non_polish` (lingua, pewność PL < `min_pl_confidence`), `duplicate` (ten sam tekst w obrębie wydarzenia) | `data/interim/bluesky/<event>/filtered/` – `posts.csv`, `comments.csv`, `excluded_*.csv` (kolumna `drop_reason`), `filter_report.json` |
| `clean_bluesky` | z pozostałych tekstów usuwa emoji, linki, wzmianki, `#tag` → `tag`, normalizuje białe znaki | `data/interim/bluesky/<event>/clean/` – `text` oczyszczony, `text_raw` oryginał |

Kod jest wspólny dla platform (`src/preprocessing/`), skrypty: `scripts/preprocess_filter.py`, `scripts/preprocess_clean.py`.

```powershell
dvc repro filter_bluesky clean_bluesky                                  # wszystkie wydarzenia z listy
dvc repro "filter_bluesky@2024-04-10_Pakt_Azyl_PE" "clean_bluesky@2024-04-10_Pakt_Azyl_PE"   # jedno
```

- Żeby przetworzyć tylko część wydarzeń, zostaw na liście `preprocess.events` tylko je.
- Zmiana `preprocess.filter` w `params.yaml` przelicza oba etapy dla wszystkich wydarzeń z listy.
- Klasyfikacja tematu (migracja) i zapis do `data/processed/` dojdą jako kolejny etap.
