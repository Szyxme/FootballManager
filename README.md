# ⚽ Football Manager 4.0

Projekt szkolny – aplikacja internetowa do zarządzania klubami piłkarskimi, przygotowywana w dwuosobowym zespole.

**Status:** projekt w trakcie rozwoju. Niektóre funkcje mogą wymagać dalszych poprawek.

## Technologie

- **Python + Flask** – backend i obsługa stron
- **SQLite** – lokalna baza danych
- **HTML, CSS i JavaScript** – interfejs użytkownika
- **GitHub** – przechowywanie i współpraca nad kodem

## Obecne funkcje

- Rejestracja i logowanie użytkowników
- Tworzenie klubów, zawodników i lig
- Dodawanie klubów do lig i generowanie terminarza
- Symulowanie meczów z uwzględnieniem statystyk zawodników
- Tabela ligowa, wyniki i historia meczów
- Gole, asysty i liczba występów zawodników
- Transfery, budżety klubów i finanse
- Trening i rozwijanie statystyk zawodników
- Kreator herbów: kształty, kolory, symbole i inicjały
- Panel administratora

## Wymagania

- Python 3.10 lub nowszy
- VS Code lub inny edytor
- Przeglądarka internetowa
- Git (opcjonalnie, jeśli pobierasz ZIP)

## Jak uruchomić projekt – krok po kroku

### 1. Pobierz projekt

Wejdź na: https://github.com/szyxme/FootballManager

Kliknij **Code → Download ZIP**, rozpakuj archiwum i otwórz folder w VS Code.

### 2. Otwórz terminal w VS Code

Wybierz **Terminal → New Terminal**. Upewnij się, że jesteś w folderze, w którym znajdują się `app.py`, `database.py` i `requirements.txt`.

### 3. Zainstaluj zależności

```bash
python -m pip install -r requirements.txt
```

Jeżeli nie ma jeszcze pliku `requirements.txt`, wystarczy zainstalować Flask:

```bash
python -m pip install Flask
```

### 4. Przygotuj bazę danych

```bash
python database.py
```

Program utworzy lokalny plik `football_manager.db` lub uzupełni istniejącą bazę o brakujące tabele i kolumny. **Przed aktualizacją istniejącego projektu zrób kopię pliku bazy.**

### 5. Uruchom serwer

```bash
python app.py
```

### 6. Otwórz stronę

W przeglądarce wpisz:

**http://127.0.0.1:5000/**

Zarejestruj konto i zaloguj się.

> Na Windows, jeżeli `python` nie działa, spróbuj `py`, np. `py app.py`.

## Jak korzystać z kreatora herbów?

1. Zaloguj się do aplikacji.
2. Przejdź do sekcji **Kluby**.
3. Przy swoim klubie wybierz **Edytuj herb**.
4. Ustaw kształt, kolory, symbol i inicjały.
5. Kliknij **Zapisz herb**.

## Struktura projektu

```text
FootballManager/
├── app.py
├── database.py
├── requirements.txt
├── README.md
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── admin.html
│   └── crest_editor.html
└── static/
    ├── style.css
    └── crest-editor.js
```


## Ważne informacje

- Aplikacja Flask działa lokalnie na komputerze, a nie jako samodzielna strona GitHub Pages.
- Każda osoba ma osobną lokalną bazę SQLite, dopóki nie skonfigurujecie wspólnego serwera i bazy.
- Starsze mecze nie otrzymają automatycznie danych o strzelcach i asystach.
- Ponowne generowanie terminarza może usunąć stare mecze i ich zdarzenia bramkowe; liczniki kariery zawodników pozostają.
- `debug=True` i domyślny klucz sesji w `app.py` są przeznaczone tylko do pracy lokalnej. Przed publicznym wdrożeniem trzeba wyłączyć debug i ustawić bezpieczny `FLASK_SECRET_KEY`.

## Autorzy

- **Szymon Chyliński** – backend, interfejs, baza danych, tabele i formularze
- **Przemysław Sosiński** – frontend, API, Python i JavaScript

Projekt edukacyjny rozwijany w ramach nauki programowania.
PROJEKT JEST JESZCZE WE WCZESNEJ FAZIE I BĘDZIE JESZCZE ROZBUDOWYWANY!
