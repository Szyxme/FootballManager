# Football Manager ⚽

Football Manager to projekt aplikacji internetowej do zarządzania klubami piłkarskimi, tworzony podczas praktyk.

## Autorzy projektu

- **Szymon Chyliński**
- **Przemysław Sosiński**

## Aktualnie wykonane

- Utworzenie podstawowej struktury projektu.
- Przygotowanie strony głównej (`index.html`).
- Stworzenie podstawowego wyglądu strony w CSS.
- Przygotowanie bazy danych SQLite.
- Utworzenie podstawowych tabel dla klubów i zawodników.
- Przygotowanie prostych formularzy do wprowadzania danych.

## Podział zadań

### Szymon Chyliński
- Backend aplikacji
- Wygląd strony (CSS)
- Baza danych SQLite
- Tabele i formularze

### Przemysław Sosiński
- Frontend aplikacji
- Tworzenie API
- Programowanie w Pythonie
- Obsługa JavaScript

## Wykorzystane technologie

- HTML
- CSS
- Python
- SQLite
- JavaScript

## API i JavaScript

Zalogowany użytkownik może korzystać z API zwracającego dane w formacie JSON:

| Metoda | Endpoint | Działanie |
|---|---|---|
| GET, POST | `/api/clubs` | Pobieranie i tworzenie klubów |
| GET, POST | `/api/players` | Pobieranie i dodawanie zawodników |
| DELETE | `/api/players/<id>` | Usuwanie zawodnika |
| GET, POST | `/api/leagues` | Pobieranie i tworzenie lig |

Żądania zmieniające dane wymagają tokenu CSRF w nagłówku `X-CSRF-Token`.
Formularze na pulpicie wysyłają dane do API przez JavaScript, a po udanym
zapisie odświeżają widok. Bez JavaScriptu formularze nadal korzystają
z tradycyjnych tras aplikacji.

## Planowane funkcje

- Zarządzanie klubami i zawodnikami
- System transferów
- Budżety klubów
- Tabele ligowe
- Rozgrywanie meczów
- Statystyki zawodników

## Status projektu

**Projekt znajduje się we wczesnej fazie rozwoju.** Obecnie przygotowywane są podstawowe elementy aplikacji, takie jak struktura projektu, baza danych oraz wygląd strony.

Większość funkcjonalności jest jeszcze w fazie planowania i będzie stopniowo wdrażana w kolejnych etapach pracy.