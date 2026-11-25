"use strict";

(() => {
    const apiBase = "https://api.openligadb.de";
    const leagueSelect = document.getElementById("openliga-league");
    const loadButton = document.getElementById("openliga-load");
    const status = document.getElementById("openliga-status");
    const matchesContainer = document.getElementById("openliga-matches");

    if (!leagueSelect || !loadButton || !status || !matchesContainer) {
        return;
    }

    function currentSeasonStartYear() {
        const now = new Date();
        return now.getMonth() >= 6 ? now.getFullYear() : now.getFullYear() - 1;
    }

    async function getJson(url) {
        const response = await fetch(url, {
            headers: { Accept: "application/json" }
        });

        if (!response.ok) {
            throw new Error(`OpenLigaDB zwróciło błąd HTTP ${response.status}.`);
        }

        return response.json();
    }

    function renderMatches(matches) {
        matchesContainer.replaceChildren();

        if (!matches.length) {
            status.textContent = "Brak meczów dla aktualnej kolejki.";
            return;
        }

        matches
            .slice()
            .sort((a, b) => new Date(a.matchDateTime) - new Date(b.matchDateTime))
            .forEach((match) => {
                const row = document.createElement("div");
                row.className = "openliga-match";

                const home = document.createElement("span");
                home.className = "openliga-team";
                home.textContent = match.team1?.teamName || "Gospodarze";

                const score = document.createElement("strong");
                score.className = "openliga-score";
                const results = Array.isArray(match.matchResults) ? match.matchResults : [];
                const result = results.find(item => item.resultTypeID === 2) || results[results.length - 1];
                score.textContent = result
                    ? `${result.pointsTeam1} : ${result.pointsTeam2}`
                    : "– : –";

                const away = document.createElement("span");
                away.className = "openliga-team";
                away.textContent = match.team2?.teamName || "Goście";

                const matchState = document.createElement("small");
                matchState.className = "openliga-state";
                const date = new Date(match.matchDateTime);
                matchState.textContent = Number.isNaN(date.getTime())
                    ? (match.matchIsFinished ? "Zakończony" : "Zaplanowany")
                    : date.toLocaleString("pl-PL", {
                        day: "2-digit",
                        month: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit"
                    });

                row.append(home, score, away, matchState);
                matchesContainer.appendChild(row);
            });
    }

    async function loadMatches() {
        loadButton.disabled = true;
        matchesContainer.replaceChildren();
        status.textContent = "Pobieranie danych z OpenLigaDB...";

        try {
            const competition = leagueSelect.value;
            const season = currentSeasonStartYear();
            const league = competition === "uel" ? `uel${season}` : "ucl";
            const competitionName = competition === "uel"
                ? "Liga Europy UEFA"
                : "Liga Mistrzów UEFA";
            const group = await getJson(`${apiBase}/getcurrentgroup/${encodeURIComponent(league)}`);
            const round = Number(group.groupOrderID);

            if (!Number.isInteger(round) || round < 1) {
                throw new Error("OpenLigaDB nie zwróciło aktualnej kolejki.");
            }

            const matches = await getJson(
                `${apiBase}/getmatchdata/${encodeURIComponent(league)}/${season}/${round}`
            );

            if (!Array.isArray(matches)) {
                throw new Error("Otrzymano nieprawidłowy format danych z OpenLigaDB.");
            }

            status.textContent = `${competitionName} · sezon ${season}/${season + 1} · kolejka ${round}`;
            renderMatches(matches);
        } catch (error) {
            console.error("Nie udało się pobrać danych z OpenLigaDB:", error);
            status.textContent = error.message || "Nie udało się połączyć z OpenLigaDB. Sprawdź internet i spróbuj ponownie.";
        } finally {
            loadButton.disabled = false;
        }
    }

    loadButton.addEventListener("click", loadMatches);
    loadMatches();
})();
