
"use strict";

const STORAGE_KEY = "football_manager_data";

function loadData() {
    try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
        if (saved && Array.isArray(saved.clubs) &&
            Array.isArray(saved.players) &&
            Array.isArray(saved.leagues)) {
            return {
                clubs: saved.clubs,
                players: saved.players,
                leagues: saved.leagues,
                transfers: Array.isArray(saved.transfers) ? saved.transfers : []
            };
        }
    } catch (error) {
        console.error("Błąd odczytu:", error);
    }
    return { clubs: [], players: [], leagues: [], transfers: [] };
}

let db = loadData();

function id() {
    return crypto.randomUUID();
}

function save() {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
        render();
        return true;
    } catch (error) {
        alert("Błąd zapisywania danych.");
        console.error(error);
        return false;
    }
}

function el(tag, text) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = String(text);
    return node;
}

function button(text, callback) {
    const btn = el("button", text);
    btn.type = "button";
    btn.style.margin = "5px";
    btn.addEventListener("click", callback);
    return btn;
}

function money(value) {
    return Number(value).toLocaleString("pl-PL") + " €";
}

function clubName(clubId) {
    return db.clubs.find(c => c.id === clubId)?.name || "Nieznany klub";
}

function fillSelect(selectId, items, label) {
    const select = document.getElementById(selectId);
    const oldValue = select.value;
    select.replaceChildren();

    items.forEach(item => {
        const option = el("option", label(item));
        option.value = item.id;
        select.appendChild(option);
    });

    if (items.some(item => item.id === oldValue)) {
        select.value = oldValue;
    }
}

function renderList(containerId, items, callback, emptyMessage) {
    const container = document.getElementById(containerId);
    container.replaceChildren();

    if (!items.length) {
        container.appendChild(el("p", emptyMessage));
        return;
    }

    items.forEach(item => {
        const row = el("div");
        row.style.padding = "12px 0";
        row.style.borderBottom = "1px solid #555";
        callback(row, item);
        container.appendChild(row);
    });
}

function resetClubForm() {
    document.getElementById("club-form").reset();
    document.getElementById("club-edit-id").value = "";
    document.getElementById("club-cancel").hidden = true;
}

function resetPlayerForm() {
    document.getElementById("player-form").reset();
    document.getElementById("player-edit-id").value = "";
    document.getElementById("player-cancel").hidden = true;
}

function render() {
    document.getElementById("clubs-count").textContent = db.clubs.length;
    document.getElementById("players-count").textContent = db.players.length;
    document.getElementById("leagues-count").textContent = db.leagues.length;

    renderList("clubs-list", db.clubs, (row, club) => {
        row.appendChild(el("strong", club.name));
        row.appendChild(el("p", "Budżet: " + money(club.budget)));

        row.appendChild(button("Edytuj", () => {
            document.getElementById("club-edit-id").value = club.id;
            document.getElementById("club-name").value = club.name;
            document.getElementById("club-budget").value = club.budget;
            document.getElementById("club-cancel").hidden = false;
            document.getElementById("club-name").focus();
        }));

        row.appendChild(button("Usuń", () => {
            if (!confirm("Usunąć klub i jego zawodników?")) return;
            db.clubs = db.clubs.filter(c => c.id !== club.id);
            db.players = db.players.filter(p => p.clubId !== club.id);
            db.leagues.forEach(l => {
                l.clubIds = (l.clubIds || []).filter(cid => cid !== club.id);
            });
            resetClubForm();
            resetPlayerForm();
            save();
        }));
    }, "Brak klubów.");

    renderList("players-list", db.players, (row, player) => {
        row.appendChild(el("strong", player.name));
        row.appendChild(el("p",
            player.age + " lat · " + player.position +
            " · " + clubName(player.clubId)));

        row.appendChild(button("Edytuj", () => {
            document.getElementById("player-edit-id").value = player.id;
            document.getElementById("player-name").value = player.name;
            document.getElementById("player-age").value = player.age;
            document.getElementById("player-position").value = player.position;
            document.getElementById("player-club").value = player.clubId;
            document.getElementById("player-cancel").hidden = false;
            document.getElementById("player-name").focus();
        }));

        row.appendChild(button("Usuń", () => {
            if (!confirm("Usunąć zawodnika?")) return;
            db.players = db.players.filter(p => p.id !== player.id);
            resetPlayerForm();
            save();
        }));
    }, "Brak zawodników.");

    renderList("leagues-list", db.leagues, (row, league) => {
        row.appendChild(el("strong", league.name));
        const ids = league.clubIds || [];

        if (!ids.length) {
            row.appendChild(el("p", "Brak przypisanych klubów."));
        }

        ids.forEach(cid => {
            const line = el("div");
            line.appendChild(el("span", clubName(cid) + " "));
            line.appendChild(button("Usuń z ligi", () => {
                league.clubIds = league.clubIds.filter(x => x !== cid);
                save();
            }));
            row.appendChild(line);
        });

        row.appendChild(button("Usuń ligę", () => {
            if (!confirm("Usunąć ligę?")) return;
            db.leagues = db.leagues.filter(l => l.id !== league.id);
            save();
        }));
    }, "Brak lig.");

    renderList("transfers-list", [...db.transfers].reverse(),
        (row, transfer) => {
            row.appendChild(el("strong", transfer.playerName));
            row.appendChild(el("p",
                transfer.fromName + " → " + transfer.toName));
            row.appendChild(el("p", "Kwota: " + money(transfer.fee)));
        }, "Brak transferów.");

    fillSelect("player-club", db.clubs, c => c.name);
    fillSelect("transfer-club", db.clubs, c => c.name);
    fillSelect("league-club", db.clubs, c => c.name);
    fillSelect("league-select", db.leagues, l => l.name);
    fillSelect("transfer-player", db.players,
        p => p.name + " (" + clubName(p.clubId) + ")");
}

document.addEventListener("DOMContentLoaded", () => {

    document.getElementById("club-form").addEventListener("submit", e => {
        e.preventDefault();

        const name = document.getElementById("club-name").value.trim();
        const budget = Number(document.getElementById("club-budget").value);
        const editId = document.getElementById("club-edit-id").value;

        if (!name || !Number.isSafeInteger(budget) || budget < 0) return;

        if (editId) {
            const club = db.clubs.find(c => c.id === editId);
            if (!club) return;
            club.name = name;
            club.budget = budget;
        } else {
            db.clubs.push({ id: id(), name, budget });
        }

        if (save()) resetClubForm();
    });

    document.getElementById("club-cancel").addEventListener("click", resetClubForm);

    document.getElementById("player-form").addEventListener("submit", e => {
        e.preventDefault();

        const name = document.getElementById("player-name").value.trim();
        const age = Number(document.getElementById("player-age").value);
        const position = document.getElementById("player-position").value;
        const clubId = document.getElementById("player-club").value;
        const editId = document.getElementById("player-edit-id").value;

        if (!name || !Number.isInteger(age) || age < 15 || age > 50 ||
            !db.clubs.some(c => c.id === clubId)) {
            alert("Uzupełnij dane i wybierz klub.");
            return;
        }

        if (editId) {
            const player = db.players.find(p => p.id === editId);
            if (!player) return;
            Object.assign(player, { name, age, position, clubId });
        } else {
            db.players.push({ id: id(), name, age, position, clubId });
        }

        if (save()) resetPlayerForm();
    });

    document.getElementById("player-cancel").addEventListener("click", resetPlayerForm);

    document.getElementById("league-form").addEventListener("submit", e => {
        e.preventDefault();
        const name = document.getElementById("league-name").value.trim();
        if (!name) return;

        db.leagues.push({ id: id(), name, clubIds: [] });
        if (save()) e.target.reset();
    });

    document.getElementById("league-club-form").addEventListener("submit", e => {
        e.preventDefault();

        const leagueId = document.getElementById("league-select").value;
        const clubId = document.getElementById("league-club").value;
        const league = db.leagues.find(l => l.id === leagueId);

        if (!league || !db.clubs.some(c => c.id === clubId)) {
            alert("Najpierw utwórz klub i ligę.");
            return;
        }

        if (!Array.isArray(league.clubIds)) league.clubIds = [];

        if (league.clubIds.includes(clubId)) {
            alert("Ten klub jest już w tej lidze.");
            return;
        }

        league.clubIds.push(clubId);
        save();
    });

    document.getElementById("transfer-form").addEventListener("submit", e => {
        e.preventDefault();

        const playerId = document.getElementById("transfer-player").value;
        const toId = document.getElementById("transfer-club").value;
        const fee = Number(document.getElementById("transfer-fee").value);

        const player = db.players.find(p => p.id === playerId);
        const toClub = db.clubs.find(c => c.id === toId);
        const fromClub = player && db.clubs.find(c => c.id === player.clubId);

        if (!player || !fromClub || !toClub) {
            alert("Wybierz zawodnika i kluby.");
            return;
        }

        if (fromClub.id === toClub.id) {
            alert("Wybierz inny klub.");
            return;
        }

        if (!Number.isSafeInteger(fee) || fee < 0) {
            alert("Nieprawidłowa kwota.");
            return;
        }

        if (toClub.budget < fee) {
            alert("Nowy klub nie ma wystarczającego budżetu.");
            return;
        }

        toClub.budget -= fee;
        fromClub.budget += fee;

        db.transfers.push({
            id: id(),
            playerName: player.name,
            fromName: fromClub.name,
            toName: toClub.name,
            fee
        });

        player.clubId = toClub.id;

        if (save()) {
            document.getElementById("transfer-fee").value = 0;
            alert("Transfer zakończony!");
        }
    });

    render();
});
