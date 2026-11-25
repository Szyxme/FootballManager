import random
from flask import Blueprint, render_template, request, session, redirect, url_for, abort, flash
from database import connect

bp = Blueprint('cups', __name__)


@bp.before_request
def require_login():
    if 'user_id' not in session:
        return redirect(url_for('login'))

@bp.route('/tournaments', methods=['GET', 'POST'])
def index():
    uid = session['user_id']
    with connect() as db:
        clubs = db.execute('SELECT id, name FROM clubs WHERE user_id=? ORDER BY name', (uid,)).fetchall()
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            try:
                ids = list(dict.fromkeys(map(int, request.form.getlist('clubs'))))
            except ValueError:
                abort(400)
            if not name or len(name) > 100 or len(ids) not in (4, 8, 16, 32) or not set(ids) <= {c['id'] for c in clubs}:
                flash('Podaj nazwę i wybierz 4, 8, 16 lub 32 własne kluby.')
                return redirect(url_for('cups.index'))
            random.shuffle(ids)
            tid = db.execute('INSERT INTO tournaments(user_id,name) VALUES (?,?)', (uid,name)).lastrowid
            db.executemany('INSERT INTO tournament_matches(tournament_id,stage,slot,home_id,away_id) VALUES (?,1,?,?,?)', [(tid,i//2,ids[i],ids[i+1]) for i in range(0,len(ids),2)])
            return redirect(url_for('cups.index'))
        cups = db.execute('SELECT t.*, c.name AS winner FROM tournaments t LEFT JOIN clubs c ON c.id=t.winner_id WHERE t.user_id=? ORDER BY t.id DESC', (uid,)).fetchall()
        brackets = {}
        for cup in cups:
            rounds = {}
            for m in db.execute('SELECT m.*, h.name AS home, a.name AS away FROM tournament_matches m JOIN clubs h ON h.id=m.home_id JOIN clubs a ON a.id=m.away_id WHERE tournament_id=? ORDER BY stage,slot', (cup['id'],)):
                rounds.setdefault(m['stage'], []).append(m)
            brackets[cup['id']] = rounds
        return render_template('tournaments.html', clubs=clubs, cups=cups, brackets=brackets)


def strength(db, club):
    return db.execute('SELECT COALESCE(AVG(rating),50) FROM players WHERE club_id=?', (club,)).fetchone()[0]


def goals(expected):
    return sum(random.random() < min(.95, expected / 12) for _ in range(12))


@bp.post('/tournaments/match/<int:mid>/simulate')
def simulate(mid):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        m = db.execute('SELECT m.* FROM tournament_matches m JOIN tournaments t ON t.id=m.tournament_id WHERE m.id=? AND t.user_id=?', (mid,session['user_id'])).fetchone()
        if not m:
            abort(404)
        if m['winner_id'] is not None:
            return redirect(url_for('cups.index'))
        diff = (strength(db,m['home_id']) - strength(db,m['away_id'])) / 25
        h = goals(max(.2, 1.5 + diff))
        a = goals(max(.2, 1.3 - diff))
        penalties = None
        if h == a:
            h += goals(max(.1, .5 + diff/3))
            a += goals(max(.1, .5 - diff/3))
        if h == a:
            ph, pa = random.choice([(5,4),(4,3),(3,2),(4,5),(3,4),(2,3)])
            penalties = f'{ph}:{pa}'
            winner = m['home_id'] if ph > pa else m['away_id']
        else:
            winner = m['home_id'] if h > a else m['away_id']
        db.execute('UPDATE tournament_matches SET home_score=?,away_score=?,winner_id=?,penalties=? WHERE id=?', (h,a,winner,penalties,mid))
        rows = db.execute('SELECT winner_id FROM tournament_matches WHERE tournament_id=? AND stage=? ORDER BY slot', (m['tournament_id'],m['stage'])).fetchall()
        if all(r['winner_id'] is not None for r in rows):
            if len(rows)==1:
                db.execute('UPDATE tournaments SET winner_id=? WHERE id=?', (winner,m['tournament_id']))
            else:
                db.executemany('INSERT INTO tournament_matches(tournament_id,stage,slot,home_id,away_id) VALUES (?,?,?,?,?)', [(m['tournament_id'],m['stage']+1,i//2,rows[i]['winner_id'],rows[i+1]['winner_id']) for i in range(0,len(rows),2)])
    return redirect(url_for('cups.index'))
