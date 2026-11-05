
import sqlite3

DATABASE = "football_manager.db"


def connect():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def create_tables():
    db = connect()

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
    """)

    columns = db.execute("PRAGMA table_info(users)").fetchall()
    names = [column["name"] for column in columns]

    if "is_admin" not in names:
        db.execute(
            "ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0"
        )

    db.execute("""
        INSERT OR IGNORE INTO settings (id, site_name, welcome_text)
        VALUES (
            1,
            'Football Manager',
            'Witaj w Football Manager!'
        )
    """)

    db.commit()
    db.close()
