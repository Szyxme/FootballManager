
import os
import sqlite3
import secrets
import random
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort, jsonify
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database import connect, create_tables, calculate_overall


app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "local-development-only-change-me"
)


# TWORZENIE TABEL

with app.app_context():
    create_tables()


# OCHRONA FORMULARZY

def csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)

    return session["_csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def protect_forms():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        expected = session.get("_csrf_token", "")
        provided = request.form.get("_csrf_token", "")
        if request.path.startswith("/api/"):
            provided = request.headers.get("X-CSRF-Token", provided)

        if not expected or not secrets.compare_digest(
            expected, provided
        ):
            if request.path.startswith("/api/"):
                return jsonify(error="Nieprawidłowy token formularza."), 400
            abort(
                400,
                description="Nieprawidłowy token formularza."
            )


# SPRAWDZANIE LOGOWANIA

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated


# SPRAWDZANIE ADMINISTRATORA

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))

        db = connect()

        user = db.execute(
            "SELECT is_admin FROM users WHERE id = ?",
            (session["user_id"],)
        ).fetchone()

        db.close()

        if not user or user["is_admin"] != 1:
            return "Brak uprawnień administratora", 403

        return f(*args, **kwargs)

    return decorated


def api_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify(error="Wymagane jest zalogowanie."), 401

        return f(*args, **kwargs)

    return decorated


def api_payload():
    if not request.is_json:
        return None, (jsonify(error="Wymagany jest format JSON."), 400)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, (jsonify(error="Nieprawidłowe dane JSON."), 400)

    return payload, None


# USTAWIENIA STRONY

@app.context_processor
def inject_settings():
    db = connect()

    settings = db.execute(
        "SELECT * FROM settings WHERE id = 1"
    ).fetchone()

    is_admin = False

    if "user_id" in session:
        user = db.execute(
            "SELECT is_admin FROM users WHERE id = ?",
            (session["user_id"],)
        ).fetchone()

        is_admin = bool(
            user and user["is_admin"] == 1
        )

    db.close()

    return {
        "settings": settings,
        "is_admin": is_admin
    }


# STRONA GLOWNA

@app.route("/")
@login_required
def index():
    db = connect()

    clubs = db.execute(
        "SELECT * FROM clubs WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()

    players = db.execute("""
        SELECT players.*, clubs.name AS club_name
        FROM players
        JOIN clubs ON players.club_id = clubs.id
        WHERE clubs.user_id = ?
    """, (session["user_id"],)).fetchall()

    leagues = db.execute(
        "SELECT * FROM leagues WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()

    matches = db.execute("""
        SELECT matches.*, home.name AS home_name, away.name AS away_name
        FROM matches
        JOIN leagues ON leagues.id = matches.league_id
        JOIN clubs AS home ON home.id = matches.home_club_id
        JOIN clubs AS away ON away.id = matches.away_club_id
        WHERE leagues.user_id = ?
        ORDER BY matches.league_id, matches.round, matches.id
    """, (session["user_id"],)).fetchall()

    club_overalls = {}
    last_matches = {}
    for club in clubs:
        row = db.execute("SELECT ROUND(AVG(rating)) AS overall FROM players WHERE club_id=?", (club["id"],)).fetchone()
        club_overalls[club["id"]] = int(row["overall"] or 50)
        recent = db.execute("""SELECT m.*, h.name AS home_name, a.name AS away_name
            FROM matches m JOIN clubs h ON h.id=m.home_club_id
            JOIN clubs a ON a.id=m.away_club_id
            JOIN leagues l ON l.id=m.league_id
            WHERE l.user_id=? AND m.played=1 AND (m.home_club_id=? OR m.away_club_id=?)
            ORDER BY m.id DESC LIMIT 5""", (session["user_id"],club["id"],club["id"])).fetchall()
        history=[]
        for m in recent:
            home = m["home_club_id"] == club["id"]
            scored = m["home_score"] if home else m["away_score"]
            conceded = m["away_score"] if home else m["home_score"]
            history.append({"opponent":m["away_name"] if home else m["home_name"],
                            "score":f"{scored}:{conceded}",
                            "result":"W" if scored>conceded else "P" if scored<conceded else "R"})
        last_matches[club["id"]] = history

    match_events = {}
    for m in matches:
        events = db.execute("""SELECT e.minute, e.club_id, p.name AS scorer,
            a.name AS assister FROM match_events e
            LEFT JOIN players p ON p.id=e.player_id
            LEFT JOIN players a ON a.id=e.assist_player_id
            WHERE e.match_id=? ORDER BY e.minute, e.id""", (m["id"],)).fetchall()
        match_events[m["id"]] = [dict(event) for event in events]

    db.close()

    return render_template(
        "dashboard.html",
        clubs=clubs,
        players=players,
        leagues=leagues,
        matches=matches,
        club_overalls=club_overalls,
        last_matches=last_matches,
        match_events=match_events
    )


# REJESTRACJA

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get(
            "username", ""
        ).strip()

        password = request.form.get(
            "password", ""
        )

        if not username or not password:
            flash("Wypełnij wszystkie pola.")
            return redirect(url_for("register"))

        db = connect()

        try:
            db.execute(
                """
                INSERT INTO users (username, password)
                VALUES (?, ?)
                """,
                (
                    username,
                    generate_password_hash(password)
                )
            )

            db.commit()

            flash("Konto utworzone!")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Ta nazwa użytkownika jest zajęta.")

        finally:
            db.close()

    return render_template("register.html")


# LOGOWANIE

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get(
            "username", ""
        ).strip()

        password = request.form.get(
            "password", ""
        )

        db = connect()

        user = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        db.close()

        if user and check_password_hash(
            user["password"], password
        ):
            session.clear()

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(url_for("index"))

        flash("Nieprawidłowy login lub hasło.")

    return render_template("login.html")


# WYLOGOWANIE

@app.route("/logout")
def logout():
    session.clear()

    return redirect(url_for("login"))


# DODAWANIE KLUBU

@app.route("/add_club", methods=["POST"])
@login_required
def add_club():
    name = request.form.get(
        "name", ""
    ).strip()

    if name:
        db = connect()

        db.execute(
            """
            INSERT INTO clubs (name, user_id)
            VALUES (?, ?)
            """,
            (name, session["user_id"])
        )

        db.commit()
        db.close()

    return redirect(url_for("index"))


# DODAWANIE ZAWODNIKA

@app.route("/add_player", methods=["POST"])
@login_required
def add_player():
    name = request.form.get(
        "name", ""
    ).strip()

    position = request.form.get(
        "position", ""
    )

    age = request.form.get(
        "age", type=int
    )

    club_id = request.form.get(
        "club_id", type=int
    )

    db = connect()

    club = db.execute(
        """
        SELECT id FROM clubs
        WHERE id = ? AND user_id = ?
        """,
        (club_id, session["user_id"])
    ).fetchone()

    if (
        name
        and position
        and age is not None
        and club
    ):
        db.execute(
            """
            INSERT INTO players
            (name, position, age, club_id)
            VALUES (?, ?, ?, ?)
            """,
            (name, position, age, club_id)
        )

        db.commit()

    db.close()

    return redirect(url_for("index"))


# USUWANIE ZAWODNIKA

@app.route(
    "/delete_player/<int:player_id>",
    methods=["POST"]
)
@login_required
def delete_player(player_id):
    db = connect()

    db.execute(
        """
        DELETE FROM players
        WHERE id = ?
        AND club_id IN (
            SELECT id FROM clubs
            WHERE user_id = ?
        )
        """,
        (player_id, session["user_id"])
    )

    db.commit()
    db.close()

    return redirect(url_for("index"))


# DODAWANIE LIGI

@app.route("/add_league", methods=["POST"])
@login_required
def add_league():
    name = request.form.get(
        "name", ""
    ).strip()

    if name:
        db = connect()

        db.execute(
            """
            INSERT INTO leagues (name, user_id)
            VALUES (?, ?)
            """,
            (name, session["user_id"])
        )

        db.commit()
        db.close()

    return redirect(url_for("index"))


# API

@app.route("/api/clubs", methods=["GET", "POST"])
@api_login_required
def api_clubs():
    db = connect()

    if request.method == "GET":
        clubs = db.execute(
            """
            SELECT id, name, budget
            FROM clubs
            WHERE user_id = ?
            ORDER BY id
            """,
            (session["user_id"],)
        ).fetchall()
        db.close()
        return jsonify(data=[dict(club) for club in clubs])

    payload, error = api_payload()
    if error:
        db.close()
        return error

    name = payload.get("name", "")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
        db.close()
        return jsonify(error="Nazwa klubu jest wymagana (maks. 80 znaków)."), 400

    cursor = db.execute(
        "INSERT INTO clubs (name, user_id) VALUES (?, ?)",
        (name.strip(), session["user_id"])
    )
    db.commit()
    club = db.execute(
        "SELECT id, name, budget FROM clubs WHERE id = ?",
        (cursor.lastrowid,)
    ).fetchone()
    db.close()
    return jsonify(data=dict(club)), 201


@app.route("/api/players", methods=["GET", "POST"])
@api_login_required
def api_players():
    db = connect()

    if request.method == "GET":
        players = db.execute(
            """
            SELECT players.id, players.name, players.position,
                   players.age, players.rating, players.club_id,
                   clubs.name AS club_name
            FROM players
            JOIN clubs ON players.club_id = clubs.id
            WHERE clubs.user_id = ?
            ORDER BY players.id
            """,
            (session["user_id"],)
        ).fetchall()
        db.close()
        return jsonify(data=[dict(player) for player in players])

    payload, error = api_payload()
    if error:
        db.close()
        return error

    name = payload.get("name", "")
    position = payload.get("position", "")
    age = payload.get("age")
    club_id = payload.get("club_id")
    valid_positions = {"BR", "OB", "PO", "NA"}

    if (
        not isinstance(name, str)
        or not name.strip()
        or len(name.strip()) > 100
        or not isinstance(position, str)
        or position not in valid_positions
        or not isinstance(age, int)
        or isinstance(age, bool)
        or not 15 <= age <= 50
        or not isinstance(club_id, int)
        or isinstance(club_id, bool)
    ):
        db.close()
        return jsonify(error="Sprawdź dane zawodnika."), 400

    club = db.execute(
        "SELECT id FROM clubs WHERE id = ? AND user_id = ?",
        (club_id, session["user_id"])
    ).fetchone()
    if not club:
        db.close()
        return jsonify(error="Nie znaleziono klubu."), 404

    cursor = db.execute(
        """
        INSERT INTO players (name, position, age, club_id)
        VALUES (?, ?, ?, ?)
        """,
        (name.strip(), position, age, club_id)
    )
    db.commit()
    player = db.execute(
        """
        SELECT players.id, players.name, players.position,
               players.age, players.rating, players.club_id,
               clubs.name AS club_name
        FROM players
        JOIN clubs ON players.club_id = clubs.id
        WHERE players.id = ?
        """,
        (cursor.lastrowid,)
    ).fetchone()
    db.close()
    return jsonify(data=dict(player)), 201


@app.route("/api/players/<int:player_id>", methods=["DELETE"])
@api_login_required
def api_delete_player(player_id):
    db = connect()
    cursor = db.execute(
        """
        DELETE FROM players
        WHERE id = ?
        AND club_id IN (
            SELECT id FROM clubs WHERE user_id = ?
        )
        """,
        (player_id, session["user_id"])
    )
    db.commit()
    db.close()

    if cursor.rowcount == 0:
        return jsonify(error="Nie znaleziono zawodnika."), 404
    return jsonify(message="Zawodnik został usunięty.")


@app.route("/api/leagues", methods=["GET", "POST"])
@api_login_required
def api_leagues():
    db = connect()

    if request.method == "GET":
        leagues = db.execute(
            """
            SELECT id, name
            FROM leagues
            WHERE user_id = ?
            ORDER BY id
            """,
            (session["user_id"],)
        ).fetchall()
        db.close()
        return jsonify(data=[dict(league) for league in leagues])

    payload, error = api_payload()
    if error:
        db.close()
        return error

    name = payload.get("name", "")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
        db.close()
        return jsonify(error="Nazwa ligi jest wymagana (maks. 80 znaków)."), 400

    cursor = db.execute(
        "INSERT INTO leagues (name, user_id) VALUES (?, ?)",
        (name.strip(), session["user_id"])
    )
    db.commit()
    league = db.execute(
        "SELECT id, name FROM leagues WHERE id = ?",
        (cursor.lastrowid,)
    ).fetchone()
    db.close()
    return jsonify(data=dict(league)), 201


# PANEL ADMINISTRATORA

@app.route("/admin")
@admin_required
def admin():
    db = connect()

    users = db.execute(
        """
        SELECT id, username, is_admin
        FROM users
        ORDER BY id
        """
    ).fetchall()

    clubs = db.execute(
        """
        SELECT clubs.*, users.username
        FROM clubs
        JOIN users ON clubs.user_id = users.id
        ORDER BY clubs.id DESC
        """
    ).fetchall()

    players = db.execute(
        """
        SELECT players.*, clubs.name AS club_name
        FROM players
        JOIN clubs ON players.club_id = clubs.id
        ORDER BY players.id DESC
        """
    ).fetchall()

    db.close()

    return render_template(
        "admin.html",
        users=users,
        clubs=clubs,
        players=players
    )


# NADAWANIE I ODBIERANIE ADMINA

@app.route(
    "/admin/user/<int:user_id>/toggle-admin",
    methods=["POST"]
)
@admin_required
def toggle_admin(user_id):
    if user_id == session["user_id"]:
        flash(
            "Nie możesz odebrać admina samemu sobie."
        )
        return redirect(url_for("admin"))

    db = connect()

    user = db.execute(
        """
        SELECT id, username, is_admin
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    if user is None:
        db.close()

        flash("Nie znaleziono użytkownika.")
        return redirect(url_for("admin"))

    new_status = (
        0 if user["is_admin"] == 1 else 1
    )

    db.execute(
        """
        UPDATE users
        SET is_admin = ?
        WHERE id = ?
        """,
        (new_status, user_id)
    )

    db.commit()
    db.close()

    if new_status == 1:
        flash(
            "Nadano administratora użytkownikowi "
            + user["username"]
        )
    else:
        flash(
            "Odebrano administratora użytkownikowi "
            + user["username"]
        )

    return redirect(url_for("admin"))


# EDYCJA USTAWIEN STRONY

@app.route("/admin/settings", methods=["POST"])
@admin_required
def admin_settings():
    site_name = request.form.get(
        "site_name", ""
    ).strip()

    welcome_text = request.form.get(
        "welcome_text", ""
    ).strip()

    if not site_name or not welcome_text:
        flash("Wypełnij wszystkie pola.")
        return redirect(url_for("admin"))

    db = connect()

    db.execute(
        """
        UPDATE settings
        SET site_name = ?, welcome_text = ?
        WHERE id = 1
        """,
        (site_name, welcome_text)
    )

    db.commit()
    db.close()

    flash("Zapisano ustawienia.")

    return redirect(url_for("admin"))


# EDYCJA KLUBU PRZEZ ADMINA

@app.route(
    "/admin/club/<int:club_id>",
    methods=["POST"]
)
@admin_required
def admin_edit_club(club_id):
    name = request.form.get(
        "name", ""
    ).strip()

    budget = request.form.get(
        "budget", type=int
    )

    if name and budget is not None and budget >= 0:
        db = connect()

        db.execute(
            """
            UPDATE clubs
            SET name = ?, budget = ?
            WHERE id = ?
            """,
            (name, budget, club_id)
        )

        db.commit()
        db.close()

        flash("Zaktualizowano klub.")

    return redirect(url_for("admin"))


# EDYCJA ZAWODNIKA PRZEZ ADMINA

@app.route(
    "/admin/player/<int:player_id>",
    methods=["POST"]
)
@admin_required
def admin_edit_player(player_id):
    name = request.form.get(
        "name", ""
    ).strip()

    rating = request.form.get(
        "rating", type=int
    )

    if (
        name
        and rating is not None
        and 1 <= rating <= 99
    ):
        db = connect()

        db.execute(
            """
            UPDATE players
            SET name = ?, rating = ?
            WHERE id = ?
            """,
            (name, rating, player_id)
        )

        db.commit()
        db.close()

        flash("Zaktualizowano zawodnika.")

    return redirect(url_for("admin"))


# AKTYWACJA ADMINISTRATORA

@app.route(
    "/setup-admin",
    methods=["GET", "POST"]
)
@login_required
def setup_admin():
    token = os.environ.get(
        "ADMIN_SETUP_TOKEN", ""
    )

    if not token:
        return (
            "Aktywacja administratora jest wyłączona.",
            403
        )

    if request.method == "GET":
        return """
        <html lang="pl">
        <head>
            <meta charset="UTF-8">
            <title>Aktywacja administratora</title>
        </head>
        <body style="
            background:#0b1018;
            color:white;
            font-family:Arial;
            text-align:center;
            padding:80px;
        ">
            <h1>Football Manager</h1>
            <h2>Aktywacja administratora</h2>

            <form method="POST">
                <input
                    type="hidden"
                    name="_csrf_token"
                    value="TOKEN"
                >

                <input
                    type="password"
                    name="token"
                    placeholder="Sekret administratora"
                    required
                >

                <button type="submit">
                    Aktywuj
                </button>
            </form>
        </body>
        </html>
        """.replace("TOKEN", csrf_token())

    provided = request.form.get(
        "token", ""
    )

    if not secrets.compare_digest(
        token, provided
    ):
        return "Nieprawidłowy sekret.", 403

    db = connect()

    db.execute(
        """
        UPDATE users
        SET is_admin = 1
        WHERE id = ?
        """,
        (session["user_id"],)
    )

    db.commit()
    db.close()

    return redirect(url_for("admin"))



# =========================================
# FOOTBALL MANAGER 2.0 - NOWE FUNKCJE
# =========================================

def owned_club(db, club_id):
    return db.execute("SELECT * FROM clubs WHERE id = ? AND user_id = ?", (club_id, session["user_id"])).fetchone()


def owned_league(db, league_id):
    return db.execute("SELECT * FROM leagues WHERE id = ? AND user_id = ?", (league_id, session["user_id"])).fetchone()


@app.route("/player/<int:player_id>/stats", methods=["POST"])
@login_required
def update_player_stats(player_id):
    db = connect()
    player = db.execute("""SELECT players.* FROM players JOIN clubs ON players.club_id = clubs.id
                           WHERE players.id = ? AND clubs.user_id = ?""", (player_id, session["user_id"])).fetchone()
    if not player:
        db.close()
        abort(404)
    fields = ("pace", "shooting", "passing", "dribbling", "defending", "physical")
    stats = {field: request.form.get(field, type=int) for field in fields}
    if any(value is None or not 1 <= value <= 99 for value in stats.values()):
        db.close()
        flash("Statystyki muszą być od 1 do 99.")
        return redirect(url_for("index"))
    overall = calculate_overall(player["position"], stats)
    db.execute("""UPDATE players SET pace=?, shooting=?, passing=?, dribbling=?, defending=?,
                  physical=?, rating=? WHERE id=?""", (*stats.values(), overall, player_id))
    db.commit()
    db.close()
    flash("Zapisano statystyki zawodnika.")
    return redirect(url_for("index"))


@app.route("/league/add-team", methods=["POST"])
@login_required
def league_add_team():
    league_id = request.form.get("league_id", type=int)
    club_id = request.form.get("club_id", type=int)
    db = connect()
    if not owned_league(db, league_id) or not owned_club(db, club_id):
        db.close()
        abort(403)
    try:
        db.execute("INSERT INTO league_teams (league_id, club_id) VALUES (?, ?)", (league_id, club_id))
        db.commit()
        flash("Dodano klub do ligi.")
    except sqlite3.IntegrityError:
        flash("Ten klub jest już w tej lidze.")
    finally:
        db.close()
    return redirect(url_for("index"))


@app.route("/transfer", methods=["POST"])
@login_required
def make_transfer():
    player_id = request.form.get("player_id", type=int)
    to_club_id = request.form.get("to_club_id", type=int)
    price = request.form.get("price", type=int)
    if price is None or price < 0:
        flash("Nieprawidłowa kwota transferu.")
        return redirect(url_for("index"))
    db = connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        player = db.execute("""SELECT players.* FROM players JOIN clubs ON players.club_id=clubs.id
                               WHERE players.id=? AND clubs.user_id=?""", (player_id, session["user_id"])).fetchone()
        destination = owned_club(db, to_club_id)
        if not player or not destination:
            abort(403)
        from_club_id = player["club_id"]
        if from_club_id == to_club_id:
            flash("Wybierz inny klub.")
            return redirect(url_for("index"))
        if destination["budget"] < price:
            flash("Klub nie ma wystarczającego budżetu.")
            return redirect(url_for("index"))
        db.execute("UPDATE clubs SET budget=budget-? WHERE id=?", (price, to_club_id))
        db.execute("UPDATE clubs SET budget=budget+? WHERE id=?", (price, from_club_id))
        db.execute("UPDATE players SET club_id=? WHERE id=?", (to_club_id, player_id))
        db.execute("""INSERT INTO transfers (player_id,from_club_id,to_club_id,price,created_at)
                      VALUES (?,?,?,?,CURRENT_TIMESTAMP)""", (player_id,from_club_id,to_club_id,price))
        for cid, kind, description in ((from_club_id,"income","Sprzedaż zawodnika"),
                                        (to_club_id,"expense","Zakup zawodnika")):
            db.execute("""INSERT INTO finances (club_id,amount,description,transaction_type)
                          VALUES (?,?,?,?)""", (cid,price,description,kind))
        db.commit()
        flash("Transfer zakończony!")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return redirect(url_for("index"))


@app.route("/league/<int:league_id>/schedule", methods=["POST"])
@login_required


def generate_schedule(league_id):
    db = connect()

    try:
        if not owned_league(db, league_id):
            abort(403)

        teams = [
            row["club_id"]
            for row in db.execute(
                """SELECT club_id FROM league_teams
                   WHERE league_id = ?
                   ORDER BY club_id""",
                (league_id,)
            )
        ]

        if len(teams) < 2:
            flash("Liga musi mieć minimum dwa kluby.")
            return redirect(url_for("index"))

        unfinished = db.execute(
            """SELECT COUNT(*) AS total
               FROM matches
               WHERE league_id = ? AND played = 0""",
            (league_id,)
        ).fetchone()["total"]

        if unfinished > 0:
            flash("Najpierw rozegraj wszystkie mecze!")
            return redirect(url_for("index"))

        # Usuwamy stary terminarz, ale nie kluby ani zawodników.
        db.execute(
            "DELETE FROM matches WHERE league_id = ?",
            (league_id,)
        )

        round_number = 1
        new_matches = 0

        for home in teams:
            for away in teams:
                if home == away:
                    continue

                db.execute(
                    """INSERT INTO matches
                       (league_id, home_club_id, away_club_id,
                        round, played)
                       VALUES (?, ?, ?, ?, 0)""",
                    (league_id, home, away, round_number)
                )

                round_number += 1
                new_matches += 1

        db.commit()

        flash(
            f"Wygenerowano nowy terminarz! "
            f"Liczba meczów: {new_matches}"
        )

    finally:
        db.close()

    return redirect(url_for("index"))



@app.route("/match/<int:match_id>/simulate", methods=["POST"])
@login_required
def simulate_match(match_id):
    db = connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        match = db.execute("""SELECT m.* FROM matches m JOIN leagues l ON l.id=m.league_id
                              WHERE m.id=? AND l.user_id=?""", (match_id, session["user_id"])).fetchone()
        if not match:
            abort(404)
        if match["played"]:
            db.rollback()
            flash("Ten mecz został już rozegrany.")
            return redirect(url_for("index") + "#leagues")

        def squad(club_id):
            return [dict(p) for p in db.execute("SELECT * FROM players WHERE club_id=?", (club_id,)).fetchall()]

        home_players = squad(match["home_club_id"])
        away_players = squad(match["away_club_id"])
        home_ovr = sum(p["rating"] for p in home_players) / len(home_players) if home_players else 50
        away_ovr = sum(p["rating"] for p in away_players) / len(away_players) if away_players else 50
        # Wpływ siły drużyny, przewaga własnego boiska i losowość.
        diff = home_ovr - away_ovr
        home_chance = max(.06, min(.82, .28 + diff * .009 + .045))
        away_chance = max(.06, min(.82, .28 - diff * .009))
        home_score = sum(random.random() < home_chance for _ in range(5))
        away_score = sum(random.random() < away_chance for _ in range(5))
        db.execute("UPDATE matches SET home_score=?, away_score=?, played=1 WHERE id=?",
                   (home_score, away_score, match_id))

        for club_id, count, players in (
            (match["home_club_id"], home_score, home_players),
            (match["away_club_id"], away_score, away_players),
        ):
            for p in players:
                db.execute("UPDATE players SET appearances=appearances+1 WHERE id=?", (p["id"],))
            for _ in range(count):
                scorer = choose_scorer(players)
                assister = choose_assister(players, scorer["id"]) if scorer else None
                minute = random.randint(1, 90)
                db.execute("""INSERT INTO match_events
                    (match_id, club_id, player_id, assist_player_id, minute)
                    VALUES (?, ?, ?, ?, ?)""",
                    (match_id, club_id, scorer["id"] if scorer else None,
                     assister["id"] if assister else None, minute))
                if scorer:
                    db.execute("UPDATE players SET goals=goals+1 WHERE id=?", (scorer["id"],))
                if assister:
                    db.execute("UPDATE players SET assists=assists+1 WHERE id=?", (assister["id"],))
        db.commit()
        flash(f"Wynik meczu: {home_score}:{away_score}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return redirect(url_for("index") + "#leagues")



@app.route("/league/<int:league_id>/table")
@login_required
def league_table(league_id):
    db = connect()
    try:
        if not owned_league(db, league_id):
            abort(404)
        teams = db.execute("""SELECT clubs.id,clubs.name FROM league_teams
                              JOIN clubs ON clubs.id=league_teams.club_id
                              WHERE league_teams.league_id=?""", (league_id,)).fetchall()
        matches = db.execute("SELECT * FROM matches WHERE league_id=? AND played=1", (league_id,)).fetchall()
        table = {t["id"]:{"club":t["name"],"played":0,"wins":0,"draws":0,"losses":0,
                          "goals_for":0,"goals_against":0,"points":0} for t in teams}
        for match in matches:
            home = table.get(match["home_club_id"])
            away = table.get(match["away_club_id"])
            if home is None or away is None:
                continue
            hs,aws = match["home_score"],match["away_score"]
            home["played"]+=1
            away["played"]+=1
            home["goals_for"]+=hs
            home["goals_against"]+=aws
            away["goals_for"]+=aws
            away["goals_against"]+=hs
            if hs>aws:
                home["wins"]+=1
                home["points"]+=3
                away["losses"]+=1
            elif hs<aws:
                away["wins"]+=1
                away["points"]+=3
                home["losses"]+=1
            else:
                home["draws"]+=1
                away["draws"]+=1
                home["points"]+=1
                away["points"]+=1
        result = sorted(table.values(),key=lambda t:(t["points"],t["goals_for"]-t["goals_against"],t["goals_for"]),reverse=True)
        return jsonify(result)
    finally:
        db.close()


@app.route("/club/<int:club_id>/finances")
@login_required
def club_finances(club_id):
    db = connect()
    try:
        club = owned_club(db,club_id)
        if not club:
            abort(404)
        history = db.execute("""SELECT amount,description,transaction_type,created_at
                                FROM finances WHERE club_id=? ORDER BY id DESC""", (club_id,)).fetchall()
        return jsonify({"club":club["name"],"budget":club["budget"],
                        "history":[dict(item) for item in history]})
    finally:
        db.close()


@app.route("/admin/player/<int:player_id>/stats", methods=["POST"])
@admin_required
def admin_player_stats(player_id):
    db = connect()
    try:
        player = db.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
        if not player:
            abort(404)
        fields = ("pace","shooting","passing","dribbling","defending","physical")
        stats = {field:request.form.get(field,type=int) for field in fields}
        if any(value is None or not 1<=value<=99 for value in stats.values()):
            flash("Wszystkie statystyki muszą być od 1 do 99.")
            return redirect(url_for("admin"))
        overall = calculate_overall(player["position"],stats)
        db.execute("""UPDATE players SET pace=?,shooting=?,passing=?,dribbling=?,defending=?,
                      physical=?,rating=? WHERE id=?""", (*stats.values(),overall,player_id))
        db.commit()
        flash("Zapisano statystyki i przeliczono overall.")
        return redirect(url_for("admin"))
    finally:
        db.close()



@app.route("/player/<int:player_id>/train", methods=["POST"])
@login_required
def train_player(player_id):
    fields = ("pace", "shooting", "passing", "dribbling", "defending", "physical")
    labels = {"pace":"tempo", "shooting":"strzały", "passing":"podania",
              "dribbling":"drybling", "defending":"obrona", "physical":"fizyczność"}
    db = connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        player = db.execute("""SELECT p.* FROM players p JOIN clubs c ON c.id=p.club_id
            WHERE p.id=? AND c.user_id=?""", (player_id,session["user_id"])).fetchone()
        if not player:
            abort(404)
        today = db.execute("SELECT date('now','localtime') AS day").fetchone()["day"]
        if player["last_training"] == today:
            db.rollback()
            flash("Ten zawodnik już dzisiaj trenował. Spróbuj jutro.")
            return redirect(url_for("index")+"#players")
        available = [f for f in fields if player[f] < 99]
        if not available:
            db.rollback()
            flash("Ten zawodnik ma już wszystkie statystyki na 99.")
            return redirect(url_for("index")+"#players")
        field = random.choice(available)
        gain = min(random.randint(1,3),99-player[field])
        stats = {f:player[f] for f in fields}
        stats[field] += gain
        overall = calculate_overall(player["position"],stats)
        db.execute(f"UPDATE players SET {field}=?, rating=?, last_training=? WHERE id=?",
                   (stats[field],overall,today,player_id))
        db.commit()
        flash(f"Trening {player['name']}: {labels[field]} +{gain}! Overall: {overall}.")
    finally:
        db.close()
    return redirect(url_for("index")+"#players")


@app.route("/admin/player/<int:player_id>/profile", methods=["POST"])
@admin_required
def admin_player_profile(player_id):
    name=request.form.get("name", "").strip()
    age=request.form.get("age", type=int)
    position=request.form.get("position", "")
    club_id=request.form.get("club_id", type=int)
    if not name or len(name)>80 or age is None or not 15<=age<=50 or position not in ("Bramkarz","Obrońca","Pomocnik","Napastnik"):
        flash("Nieprawidłowe dane zawodnika.")
        return redirect(url_for("admin")+"#players")
    db=connect()
    try:
        if not db.execute("SELECT 1 FROM clubs WHERE id=?", (club_id,)).fetchone():
            abort(400)
        player=db.execute("SELECT * FROM players WHERE id=?",(player_id,)).fetchone()
        if not player: abort(404)
        stats={f:player[f] for f in ("pace","shooting","passing","dribbling","defending","physical")}
        overall=calculate_overall(position,stats)
        db.execute("UPDATE players SET name=?,age=?,position=?,club_id=?,rating=? WHERE id=?",
                   (name,age,position,club_id,overall,player_id))
        db.commit()
        flash("Zapisano dane zawodnika.")
    finally: db.close()
    return redirect(url_for("admin")+"#players")


# FOOTBALL MANAGER 4.0: HERBY I STRZELCY
CREST_SHAPES = {"shield", "round", "circle", "hex"}
CREST_SYMBOLS = {"ball", "star", "crown", "letters", "stripes"}
CREST_DEFAULT = {"shape": "shield", "color": "#1765d1", "accent": "#f7c948", "symbol": "ball", "initials": "FC"}


def validate_crest(data):
    if not isinstance(data, dict):
        return None
    shape = data.get("shape")
    symbol = data.get("symbol")
    color = data.get("color")
    accent = data.get("accent")
    initials = data.get("initials", "")
    import re
    if shape not in CREST_SHAPES or symbol not in CREST_SYMBOLS:
        return None
    if not all(isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v) for v in (color, accent)):
        return None
    if not isinstance(initials, str) or len(initials) > 3 or not re.fullmatch(r"[A-Za-z0-9ĄĆĘŁŃÓŚŹŻąćęłńóśźż]*", initials):
        return None
    return {"shape": shape, "symbol": symbol, "color": color, "accent": accent,
            "initials": initials.upper() or "FC"}


def choose_scorer(players):
    if not players:
        return None
    weights = []
    for p in players:
        position = {"Napastnik": "NA", "Pomocnik": "PO", "Obrońca": "OB", "Bramkarz": "BR"}.get(p["position"], p["position"])
        position_bonus = {"NA": 2.4, "PO": 1.4, "OB": 0.55, "BR": 0.06}.get(position, 1.0)
        weights.append(max(1, p["shooting"]) * position_bonus)
    return random.choices(players, weights=weights, k=1)[0]


def choose_assister(players, scorer_id):
    candidates = [p for p in players if p["id"] != scorer_id]
    if not candidates or random.random() > 0.68:
        return None
    return random.choices(candidates, weights=[max(1, p["passing"]) for p in candidates], k=1)[0]



@app.route("/club/<int:club_id>/crest", methods=["GET", "POST"])
@login_required
def edit_crest(club_id):
    db = connect()
    try:
        club = owned_club(db, club_id)
        if not club:
            abort(404)
        if request.method == "POST":
            try:
                data = __import__("json").loads(request.form.get("crest", ""))
            except (ValueError, TypeError):
                data = None
            validated = validate_crest(data)
            if validated is None:
                flash("Nieprawidłowy projekt herbu.")
                return redirect(url_for("edit_crest", club_id=club_id))
            db.execute("UPDATE clubs SET crest=? WHERE id=? AND user_id=?",
                       (__import__("json").dumps(validated), club_id, session["user_id"]))
            db.commit()
            flash("Herb klubu został zapisany!")
            return redirect(url_for("index") + "#clubs")
        try:
            current = validate_crest(__import__("json").loads(club["crest"] or "{}")) or CREST_DEFAULT
        except (ValueError, TypeError):
            current = CREST_DEFAULT
        return render_template("crest_editor.html", club=club, crest=current)
    finally:
        db.close()


# URUCHOMIENIE APLIKACJI

if __name__ == "__main__":
    app.run(debug=True)