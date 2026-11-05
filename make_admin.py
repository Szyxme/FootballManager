
from database import connect, create_tables

create_tables()

username = input("Podaj login konta administratora: ").strip()

db = connect()

user = db.execute(
    "SELECT id FROM users WHERE username = ?",
    (username,)
).fetchone()

if user:
    db.execute(
        "UPDATE users SET is_admin = 1 WHERE id = ?",
        (user["id"],)
    )
    db.commit()
    print("Sukces! Konto ma teraz uprawnienia administratora.")
else:
    print("Nie znaleziono takiego konta.")

db.close()
