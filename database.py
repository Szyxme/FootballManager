
import sqlite3
from pathlib import Path

DATABASE = Path(__file__).resolve().parent / "football_manager.db"


def connect():
    db = sqlite3.connect(str(DATABASE), timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 15000")
    return db


def add_column(db, table, column, definition):
    columns = {
        row["name"]
        for row in db.execute(f"PRAGMA table_info({table})")
    }

    if column not in columns:
        db.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def calculate_overall(position, stats):
    weights = {
        "BR": [0.10, 0.05, 0.15, 0.10, 0.35, 0.25],
        "OB": [0.10, 0.05, 0.10, 0.10, 0.40, 0.25],
        "PO": [0.15, 0.10, 0.30, 0.25, 0.10, 0.10],
        "NA": [0.20, 0.35, 0.10, 0.20, 0.05, 0.10]
    }

    position_names = {
        "Bramkarz": "BR",
        "Obrońca": "OB",
        "Pomocnik": "PO",
        "Napastnik": "NA"
    }

    position = position_names.get(position, position)
    selected = weights.get(position, weights["PO"])

    fields = (
        "pace", "shooting", "passing",
        "dribbling", "defending", "physical"
    )

    values = [int(stats[field]) for field in fields]

    overall = sum(
        value * weight
        for value, weight in zip(values, selected)
    )

    return max(1, min(99, round(overall)))


def create_tables():
    db = connect()

    try:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS clubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            budget INTEGER DEFAULT 1000000,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT NOT NULL,
            age INTEGER,
            rating INTEGER DEFAULT 50,
            club_id INTEGER NOT NULL,
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        );

        CREATE TABLE IF NOT EXISTS leagues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS league_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            club_id INTEGER NOT NULL,
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            FOREIGN KEY (club_id) REFERENCES clubs(id),
            UNIQUE (league_id, club_id)
        );

        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            home_club_id INTEGER NOT NULL,
            away_club_id INTEGER NOT NULL,
            home_score INTEGER,
            away_score INTEGER,
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            FOREIGN KEY (home_club_id) REFERENCES clubs(id),
            FOREIGN KEY (away_club_id) REFERENCES clubs(id)
        );

        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            from_club_id INTEGER,
            to_club_id INTEGER NOT NULL,
            price INTEGER DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (from_club_id) REFERENCES clubs(id),
            FOREIGN KEY (to_club_id) REFERENCES clubs(id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            site_name TEXT DEFAULT 'Football Manager',
            welcome_text TEXT DEFAULT 'Witaj w Football Manager!'
        );

        CREATE TABLE IF NOT EXISTS finances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            description TEXT NOT NULL,
            transaction_type TEXT NOT NULL
                CHECK (transaction_type IN ('income', 'expense')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        );
        """)

        add_column(db, "users", "is_admin", "INTEGER DEFAULT 0")

        # Statystyki zawodników
        for field in (
            "pace", "shooting", "passing",
            "dribbling", "defending", "physical"
        ):
            add_column(
                db, "players", field,
                "INTEGER DEFAULT 50"
            )

        add_column(db, "players", "last_training", "TEXT DEFAULT NULL")

        # Terminarz
        add_column(db, "matches", "round", "INTEGER DEFAULT 1")
        add_column(db, "matches", "played", "INTEGER DEFAULT 0")
        add_column(db, "matches", "played_at", "TEXT DEFAULT NULL")

        # Transfery
        add_column(db, "transfers", "created_at", "TEXT DEFAULT NULL")

        # Football Manager 4.0 - kreator herbów
        add_column(
            db, "clubs", "crest",
            "TEXT NOT NULL DEFAULT '{}'"
        )

        # Football Manager 4.0 - statystyki kariery
        for field in ("goals", "assists", "appearances"):
            add_column(
                db, "players", field,
                "INTEGER NOT NULL DEFAULT 0"
            )

        # Strzelcy bramek i asysty
        db.execute("""
            CREATE TABLE IF NOT EXISTS match_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                club_id INTEGER NOT NULL,
                player_id INTEGER,
                assist_player_id INTEGER,
                minute INTEGER NOT NULL,
                FOREIGN KEY (match_id)
                    REFERENCES matches(id) ON DELETE CASCADE,
                FOREIGN KEY (club_id)
                    REFERENCES clubs(id),
                FOREIGN KEY (player_id)
                    REFERENCES players(id) ON DELETE SET NULL,
                FOREIGN KEY (assist_player_id)
                    REFERENCES players(id) ON DELETE SET NULL
            )
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_match_events_match
            ON match_events(match_id)
        """)

        db.execute("""
            INSERT OR IGNORE INTO settings
            (id, site_name, welcome_text)
            VALUES (
                1,
                'Football Manager',
                'Witaj w Football Manager!'
            )
        """)

        db.execute("""
            UPDATE matches
            SET played = 1
            WHERE home_score IS NOT NULL
              AND away_score IS NOT NULL
              AND played = 0
        """)

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    create_tables()
    print("Baza Football Manager 4.0 jest gotowa.")
