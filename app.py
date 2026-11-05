
import os
import sqlite3
import secrets
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database import connect, create_tables


app = Flask(__name__)

app.secret_key = os.environ["FLASK_SECRET_KEY"]

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
    if request.method == "POST":
        expected = session.get("_csrf_token", "")
        provided = request.form.get("_csrf_token", "")

        if not expected or not secrets.compare_digest(
            expected, provided
        ):
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

    db.close()

    return render_template(
        "dashboard.html",
        clubs=clubs,
        players=players,
        leagues=leagues
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


# URUCHOMIENIE APLIKACJI

if __name__ == "__main__":
    app.run(debug=True)
