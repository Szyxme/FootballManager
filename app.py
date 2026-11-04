
import os
import sqlite3
import secrets
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from database import connect, create_tables

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY", "local-development-only-change-me"
)

with app.app_context():
    create_tables()


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
        is_admin = bool(user and user["is_admin"] == 1)

    db.close()
    return dict(settings=settings, is_admin=is_admin)


@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

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


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if not username or not password:
            flash("Wypełnij wszystkie pola.")
            return redirect(url_for("register"))

        db = connect()

        try:
            db.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, generate_password_hash(password))
            )
            db.commit()
            flash("Konto zostało utworzone!")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Ta nazwa użytkownika jest zajęta.")

        finally:
            db.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        db = connect()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        db.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))

        flash("Nieprawidłowy login lub hasło.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/add_club", methods=["POST"])
def add_club():
    if "user_id" not in session:
        return redirect(url_for("login"))

    name = request.form["name"].strip()

    if name:
        db = connect()
        db.execute(
            "INSERT INTO clubs (name, user_id) VALUES (?, ?)",
            (name, session["user_id"])
        )
        db.commit()
        db.close()

    return redirect(url_for("index"))


@app.route("/add_player", methods=["POST"])
def add_player():
    if "user_id" not in session:
        return redirect(url_for("login"))

    name = request.form["name"].strip()
    position = request.form["position"]
    age = request.form.get("age", type=int)
    club_id = request.form.get("club_id", type=int)

    db = connect()

    club = db.execute(
        "SELECT id FROM clubs WHERE id = ? AND user_id = ?",
        (club_id, session["user_id"])
    ).fetchone()

    if (
        name and position in ("BR", "OB", "PO", "NA")
        and age is not None and 15 <= age <= 50 and club
    ):
        db.execute("""
            INSERT INTO players (name, position, age, club_id)
            VALUES (?, ?, ?, ?)
        """, (name, position, age, club_id))
        db.commit()

    db.close()
    return redirect(url_for("index"))


@app.route("/delete_player/<int:player_id>", methods=["POST"])
def delete_player(player_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = connect()

    db.execute("""
        DELETE FROM players
        WHERE id = ? AND club_id IN (
            SELECT id FROM clubs WHERE user_id = ?
        )
    """, (player_id, session["user_id"]))

    db.commit()
    db.close()

    return redirect(url_for("index"))


@app.route("/add_league", methods=["POST"])
def add_league():
    if "user_id" not in session:
        return redirect(url_for("login"))

    name = request.form["name"].strip()

    if name:
        db = connect()
        db.execute(
            "INSERT INTO leagues (name, user_id) VALUES (?, ?)",
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
        "SELECT id, username, is_admin FROM users"
    ).fetchall()

    clubs = db.execute("""
        SELECT clubs.*, users.username
        FROM clubs
        JOIN users ON clubs.user_id = users.id
        ORDER BY clubs.id DESC
    """).fetchall()

    players = db.execute("""
        SELECT players.*, clubs.name AS club_name
        FROM players
        JOIN clubs ON players.club_id = clubs.id
        ORDER BY players.id DESC
    """).fetchall()

    db.close()

    return render_template(
        "admin.html",
        users=users,
        clubs=clubs,
        players=players
    )


@app.route("/admin/settings", methods=["POST"])
@admin_required
def admin_settings():
    site_name = request.form.get("site_name", "").strip()
    welcome_text = request.form.get("welcome_text", "").strip()

    if not site_name or not welcome_text:
        flash("Wypełnij wszystkie pola.")
        return redirect(url_for("admin"))

    if len(site_name) > 80 or len(welcome_text) > 200:
        flash("Podany tekst jest za długi.")
        return redirect(url_for("admin"))

    db = connect()

    db.execute("""
        UPDATE settings
        SET site_name = ?, welcome_text = ?
        WHERE id = 1
    """, (site_name, welcome_text))

    db.commit()
    db.close()

    flash("Zapisano ustawienia strony.")
    return redirect(url_for("admin"))


@app.route("/admin/club/<int:club_id>", methods=["POST"])
@admin_required
def admin_edit_club(club_id):
    name = request.form.get("name", "").strip()
    budget = request.form.get("budget", type=int)

    if name and len(name) <= 80 and budget is not None and budget >= 0:
        db = connect()

        db.execute("""
            UPDATE clubs SET name = ?, budget = ?
            WHERE id = ?
        """, (name, budget, club_id))

        db.commit()
        db.close()
        flash("Zaktualizowano klub.")
    else:
        flash("Nieprawidłowe dane klubu.")

    return redirect(url_for("admin"))


@app.route("/admin/player/<int:player_id>", methods=["POST"])
@admin_required
def admin_edit_player(player_id):
    name = request.form.get("name", "").strip()
    rating = request.form.get("rating", type=int)

    if name and len(name) <= 100 and rating is not None and 1 <= rating <= 99:
        db = connect()

        db.execute("""
            UPDATE players SET name = ?, rating = ?
            WHERE id = ?
        """, (name, rating, player_id))

        db.commit()
        db.close()
        flash("Zaktualizowano zawodnika.")
    else:
        flash("Nieprawidłowe dane zawodnika.")

    return redirect(url_for("admin"))


# JEDNORAZOWA AKTYWACJA ADMINISTRATORA

@app.route("/setup-admin", methods=["GET", "POST"])
def setup_admin():
    if request.method == "GET":
        return """
        <!DOCTYPE html>
        <html lang="pl">
        <head>
            <meta charset="UTF-8">
            <title>Aktywacja administratora</title>
        </head>
        <body style="background:#0b1018;color:white;
                     font-family:Arial;text-align:center;
                     padding:80px 20px;">
            <h1>Football Manager</h1>
            <h2>Aktywacja administratora</h2>
            <form method="POST">
                <input type="password" name="token"
                       placeholder="Sekret administratora"
                       required
                       style="padding:12px;width:260px;">
                <button type="submit"
                        style="padding:12px;background:#19e66d;
                               border:0;cursor:pointer;">
                    Aktywuj
                </button>
            </form>
        </body>
        </html>
        """

    token = os.environ.get("ADMIN_SETUP_TOKEN", "")
    provided = request.form.get("token", "")

    if not token or not secrets.compare_digest(token, provided):
        return "Nieprawidłowy sekret administratora", 403

    db = connect()
    cursor = db.execute(
        "UPDATE users SET is_admin = 1 WHERE username = ?",
        ("Szyxme",)
    )
    db.commit()
    db.close()

    if cursor.rowcount == 0:
        return "Nie znaleziono konta Szyxme", 404

    return """
    <h2>Administrator aktywowany!</h2>
    <a href="/admin">Przejdź do panelu administratora</a>
    """


if __name__ == "__main__":
    app.run(debug=True)
