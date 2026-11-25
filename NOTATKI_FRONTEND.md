# Notatki do odpowiedzi: frontend Football Manager

## Najważniejsze rozróżnienie w projekcie

Są tu dwa różne widoki:

- `index.html` to samodzielny, statyczny podgląd strony. Ładuje `static/app.js`, który zapisuje dane w `localStorage` przeglądarki.
- `templates/dashboard.html` to dashboard uruchamiany przez Flask. Dane są renderowane przez Jinja z bazy SQLite. Ten widok **nie ładuje `static/app.js`**. Zawiera kod pobierający tabelę ligi i finanse z backendu oraz ładuje `static/crest-editor.js` i `static/openligadb.js`.

Jeśli ktoś pyta o stronę działającą pod adresem lokalnego serwera Flask, opisuj przede wszystkim `templates/dashboard.html`, a nie statyczny podgląd `index.html`.

## Co robi `static/app.js`

`app.js` obsługuje interaktywny, lokalny podgląd z `index.html`:

1. Po zdarzeniu `DOMContentLoaded` podpina obsługę formularzy i wyświetla zapisane dane.
2. Odczytuje dane z `localStorage` pod kluczem `football_manager_data`.
3. Przechowuje cztery listy: `clubs`, `players`, `leagues` i `transfers`.
4. Tworzy identyfikatory przez `crypto.randomUUID()`.
5. `save()` zamienia obiekt na JSON przez `JSON.stringify`, zapisuje go w `localStorage` i wywołuje `render()`.
6. `render()` odświeża liczniki, listy i opcje w polach wyboru. Elementy HTML tworzy przez `document.createElement`, a tekst ustawia przez `textContent`.
7. Obsługuje dodawanie, edycję i usuwanie klubów oraz zawodników, tworzenie lig i przypisywanie do nich klubów.
8. Obsługuje lokalny transfer: sprawdza dane, przenosi zawodnika, odejmuje kwotę od budżetu kupującego, dodaje ją sprzedającemu i zapisuje wpis w historii transferów.
9. Sprawdza podstawowe dane formularzy, np. wiek 15–50, nieujemny budżet i kwotę transferu. Przy usuwaniu pyta o potwierdzenie.

### Czy `app.js` łączy się z zewnętrznymi danymi?

**Sam `app.js` nie.** W `app.js` nie ma `fetch()` ani połączenia z API. Dane zapisuje lokalnie w przeglądarce użytkownika. Nie trafiają stamtąd do serwera Flask ani do bazy SQLite i nie są współdzielone między różnymi użytkownikami lub przeglądarkami.

`localStorage` to proste trwałe przechowywanie danych w przeglądarce. Dane zwykle pozostają po odświeżeniu strony, ale są związane z konkretną przeglądarką i domeną/adresem.

### Gdzie jest zewnętrzne API?

Integrację z zewnętrznym API obsługuje `static/openligadb.js`, ładowany w `templates/dashboard.html`. Jest to OpenLigaDB — API z danymi piłkarskimi, które nie wymaga klucza. Dashboard pokazuje mecze Ligi Mistrzów UEFA i Ligi Europy UEFA.

1. Po otwarciu dashboardu skrypt uruchamia `loadMatches()`. Przycisk „Pobierz wyniki” uruchamia ją ponownie.
2. Skrypt wybiera rozgrywki i wylicza początek bieżącego sezonu. Dla Ligi Mistrzów używa skrótu `ucl`, a dla Ligi Europy buduje skrót sezonu, np. `uel2026`.
3. Pierwszy `fetch()` odpytuje `https://api.openligadb.de/getcurrentgroup/{liga}` o aktualną kolejkę.
4. Drugi `fetch()` odpytuje `https://api.openligadb.de/getmatchdata/{liga}/{sezon}/{kolejka}` o mecze tej kolejki.
5. Odpowiedź JSON jest sprawdzana, sortowana po dacie i wyświetlana w panelu. Jeśli API jest niedostępne albo zwróci błąd, użytkownik widzi komunikat.

To połączenie idzie **bezpośrednio z przeglądarki do zewnętrznego serwera OpenLigaDB**, a nie przez własny backend Flask. Automatyczne odświeżanie w pętli jest celowo wyłączone — dane pobierają się przy wejściu na stronę i po kliknięciu przycisku.

OpenLigaDB nie wymaga klucza API. Jej dokumentacja prosi o oszczędne pobieranie i podaje limit 60 zapytań na minutę z jednego adresu IP; dlatego skrypt nie odpytuje API cyklicznie.

## Jak działa frontend właściwej aplikacji Flask

### HTML i Jinja

`templates/dashboard.html` jest szablonem HTML. Flask przekazuje do niego dane z bazy, a Jinja wstawia je do strony:

- `{{ ... }}` wyświetla wartość, np. nazwę klubu lub liczbę zawodników.
- `{% for ... %}` tworzy elementy dla kolejnych rekordów.
- `{% if ... %}` pokazuje różne treści zależnie od danych, np. przycisk administratora lub komunikat o pustej liście.
- `url_for(...)` tworzy adresy do tras Flask i plików statycznych.

Większość formularzy dashboardu wysyła zwykłe żądania `POST` do tras Flask: dodawanie klubu, zawodnika i ligi, transfer, generowanie terminarza oraz symulowanie meczu. Ukryte pole `_csrf_token` zabezpiecza te operacje.

### JavaScript w `dashboard.html`

Wbudowana funkcja `loadLeague(id)`:

1. Wysyła `fetch('/league/' + id + '/table')` do **własnej aplikacji Flask**.
2. Oczekuje odpowiedzi JSON z tabelą ligi.
3. Wyświetla stan „Ładowanie...”, sprawdza `response.ok`, odczytuje JSON przez `response.json()` i tworzy wiersze tabeli.

Funkcja `loadFinances()` pobiera wybrany identyfikator klubu i wysyła `fetch('/club/' + id + '/finances')`. Flask zwraca budżet i historię operacji jako JSON, a JavaScript pokazuje je na stronie.

To są żądania do **backendu tej samej aplikacji**, nie do zewnętrznego API. Backend kontroluje zalogowanie i to, czy wybrana liga/klub należy do użytkownika.

`safeText()` zamienia znaki specjalne HTML na bezpieczne encje przed wstawieniem tekstu do fragmentu tabeli przez `innerHTML`. `innerHTML` interpretuje tekst jako HTML, dlatego dane tekstowe wymagają takiego zabezpieczenia.

Ważne rozróżnienie: te dwa `fetch()`-e korzystają z tras własnego backendu Flask. Zewnętrzne `fetch()` do OpenLigaDB jest w osobnym pliku `static/openligadb.js`.

### `static/crest-editor.js`

Ten skrypt obsługuje kreator herbów:

- rysuje herb jako SVG bez pobierania obrazka z zewnątrz;
- odświeża podgląd po zmianie kształtu, kolorów, symbolu lub inicjałów;
- odczytuje wartości początkowe przekazane przez Jinja;
- przed wysłaniem formularza zapisuje ustawienia jako JSON w ukrytym polu `crest-json`;
- formularz wysyła dane do Flask metodą `POST`, wraz z tokenem CSRF; backend sprawdza dane i zapisuje herb w SQLite.

## CSS i zewnętrzne połączenia

`static/style.css` odpowiada za kolory, układ, odstępy, przyciski i wygląd strony. Reguły `@media` dopasowują układ do mniejszych ekranów.

W CSS jest `@import` do Google Fonts (`fonts.googleapis.com`) po czcionkę Inter. To zewnętrzny zasób sieciowy frontendu. Nie jest to połączenie wykonywane przez `app.js`. Jeśli internet jest niedostępny, CSS ma zapasowe czcionki, np. Arial.

## Pojęcia, które warto umieć wyjaśnić

- **DOM** — struktura elementów HTML, którą JavaScript może odczytywać i zmieniać.
- **Zdarzenie** — informacja o akcji użytkownika, np. `submit`, `click` lub `input`; obsługuje je `addEventListener`.
- **`preventDefault()`** — zatrzymuje domyślne zachowanie formularza; w lokalnym `app.js` pozwala zapisać dane bez przeładowania strony.
- **JSON** — tekstowy format wymiany/przechowywania danych; `JSON.stringify` tworzy JSON, a `JSON.parse` odtwarza z niego obiekt.
- **`fetch()`** — wysyła żądanie HTTP z przeglądarki. W dashboardzie pobiera dane z tras Flask tej aplikacji.
- **`async` / `await`** — pozwala poczekać na odpowiedź `fetch()` bez blokowania całej strony.
- **Frontend / backend** — frontend to część widoczna i obsługiwana w przeglądarce; backend Flask przetwarza żądania i pracuje z SQLite.
- **CSRF token** — ukryty token dodawany do formularzy zmieniających dane, który backend sprawdza przed wykonaniem operacji.

## Krótka odpowiedź ustna

„Frontend jest zrobiony w HTML, CSS i JavaScript. Statyczny `index.html` korzysta z `app.js`, który zapisuje dane w `localStorage`. Dashboard Flask jest osobnym widokiem: Flask wstawia dane z SQLite przez Jinja, formularze wysyłają POST-y do backendu, a jego JavaScript pobiera tabelę ligi i finanse z własnych tras. Dodatkowy `openligadb.js` łączy się bezpośrednio przez `fetch()` z zewnętrznym API OpenLigaDB, pobiera aktualną kolejkę i wyniki Ligi Mistrzów albo Ligi Europy. `crest-editor.js` rysuje herb jako SVG. API OpenLigaDB nie wymaga klucza; zewnętrzna czcionka Inter jest ładowana z Google Fonts.”
