from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import uuid
import datetime
import os

DB_PATH = 'database.db'
app = Flask(__name__)
app.secret_key = 'dev_secret_key_change_this'  # replace with a secure key in production


def get_conn():
    """Open a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create database and sample data if it doesn't exist yet."""
    if not os.path.exists(DB_PATH):
        conn = get_conn()
        cur = conn.cursor()

        # Movies table
        cur.execute('''
            CREATE TABLE movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT
            )
        ''')

        # Shows table
        cur.execute('''
            CREATE TABLE shows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id INTEGER,
                show_time TEXT,
                total_seats INTEGER,
                FOREIGN KEY(movie_id) REFERENCES movies(id)
            )
        ''')

        # Bookings table
        cur.execute('''
            CREATE TABLE bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id TEXT,
                movie_id INTEGER,
                show_id INTEGER,
                seat_no INTEGER,
                name TEXT,
                email TEXT,
                timestamp TEXT
            )
        ''')

        # Insert sample Malayalam movies
        cur.execute(
            'INSERT INTO movies (title, description) VALUES (?, ?)',
            ('Manjummel Boys', 'A survival thriller inspired by real events, with suspense and emotional drama.')
        )
        cur.execute(
            'INSERT INTO movies (title, description) VALUES (?, ?)',
            ('Aavesham', 'A stylish action-drama with memorable characters and punchy moments.')
        )
        cur.execute(
            'INSERT INTO movies (title, description) VALUES (?, ?)',
            ('2018: Everyone is a Hero', 'Stories of courage and unity from the 2018 Kerala floods.')
        )
        cur.execute(
            'INSERT INTO movies (title, description) VALUES (?, ?)',
            ('Premalu', 'A light-hearted romantic comedy about youth, friendship, and first love.')
        )

        # Insert sample shows (2 shows per movie)
        cur.execute(
            'INSERT INTO shows (movie_id, show_time, total_seats) VALUES (?, ?, ?)',
            (1, '2025-09-20 17:30', 40)
        )
        cur.execute(
            'INSERT INTO shows (movie_id, show_time, total_seats) VALUES (?, ?, ?)',
            (1, '2025-09-20 20:30', 40)
        )

        cur.execute(
            'INSERT INTO shows (movie_id, show_time, total_seats) VALUES (?, ?, ?)',
            (2, '2025-09-20 18:00', 35)
        )
        cur.execute(
            'INSERT INTO shows (movie_id, show_time, total_seats) VALUES (?, ?, ?)',
            (2, '2025-09-20 21:00', 35)
        )

        cur.execute(
            'INSERT INTO shows (movie_id, show_time, total_seats) VALUES (?, ?, ?)',
            (3, '2025-09-20 16:00', 50)
        )
        cur.execute(
            'INSERT INTO shows (movie_id, show_time, total_seats) VALUES (?, ?, ?)',
            (3, '2025-09-20 19:30', 50)
        )

        cur.execute(
            'INSERT INTO shows (movie_id, show_time, total_seats) VALUES (?, ?, ?)',
            (4, '2025-09-20 17:00', 30)
        )
        cur.execute(
            'INSERT INTO shows (movie_id, show_time, total_seats) VALUES (?, ?, ?)',
            (4, '2025-09-20 20:00', 30)
        )

        conn.commit()
        conn.close()
        print('Database created with sample Malayalam movies and shows.')


# Landing page (root) -> shows a simple front page (home.html)
@app.route('/')
def landing():
    return render_template('home.html')


# Optional route /home also points to same landing page
@app.route('/home')
def home():
    return render_template('home.html')


# Main movies page moved to /main (function name kept as index so url_for('index') works)
@app.route('/main')
def index():
    conn = get_conn()
    movies = conn.execute('SELECT * FROM movies').fetchall()
    shows = conn.execute('SELECT * FROM shows ORDER BY show_time').fetchall()
    shows_by_movie = {}
    for s in shows:
        shows_by_movie.setdefault(s['movie_id'], []).append(s)
    conn.close()
    return render_template('index.html', movies=movies, shows_by_movie=shows_by_movie)


@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    """Movie detail page: show description and seat map for selected show."""
    show_id = request.args.get('show_id', type=int)
    conn = get_conn()
    movie = conn.execute('SELECT * FROM movies WHERE id=?', (movie_id,)).fetchone()
    if not movie:
        conn.close()
        flash('Movie not found')
        return redirect(url_for('index'))

    shows = conn.execute(
        'SELECT * FROM shows WHERE movie_id=? ORDER BY show_time',
        (movie_id,)
    ).fetchall()

    if not show_id and shows:
        show_id = shows[0]['id']

    active_show = None
    booked_seats = []
    if show_id:
        active_show = conn.execute('SELECT * FROM shows WHERE id=?', (show_id,)).fetchone()
        if active_show:
            rows = conn.execute(
                'SELECT seat_no FROM bookings WHERE show_id=?',
                (active_show['id'],)
            ).fetchall()
            booked_seats = [int(r['seat_no']) for r in rows]

    conn.close()
    return render_template(
        'movie.html',
        movie=movie,
        shows=shows,
        active_show=active_show,
        booked_seats=booked_seats
    )


@app.route('/book', methods=['POST'])
def book():
    """Handle ticket booking."""
    try:
        movie_id = int(request.form.get('movie_id'))
        show_id = int(request.form.get('show_id'))
    except (TypeError, ValueError):
        flash('Invalid movie or show.')
        return redirect(url_for('index'))

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    seats = request.form.getlist('seats')

    if not name or not email or not seats:
        flash('Please provide name, email and select at least one seat.')
        return redirect(url_for('movie_detail', movie_id=movie_id, show_id=show_id))

    try:
        seats = [int(s) for s in seats]
    except ValueError:
        flash('Invalid seat selection.')
        return redirect(url_for('movie_detail', movie_id=movie_id, show_id=show_id))

    conn = get_conn()
    existing = conn.execute(
        'SELECT seat_no FROM bookings WHERE show_id=?',
        (show_id,)
    ).fetchall()
    booked = set(int(r['seat_no']) for r in existing)

    for s in seats:
        if s in booked:
            conn.close()
            flash(f'Seat {s} is already booked — try different seats.')
            return redirect(url_for('movie_detail', movie_id=movie_id, show_id=show_id))

    booking_id = str(uuid.uuid4())[:8]
    timestamp = datetime.datetime.now().isoformat()

    for s in seats:
        conn.execute(
            'INSERT INTO bookings (booking_id, movie_id, show_id, seat_no, name, email, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (booking_id, movie_id, show_id, s, name, email, timestamp)
        )

    conn.commit()
    conn.close()

    flash(f'Booking successful — ID: {booking_id}. Check your booking history (use the same email).')
    return redirect(url_for('booking_history') + '?email=' + email)


@app.route('/booking_history')
def booking_history():
    """Show booking history for a given email."""
    email = request.args.get('email', '').strip()
    grouped = []
    if email:
        conn = get_conn()
        rows = conn.execute(
            'SELECT DISTINCT booking_id FROM bookings WHERE email=? ORDER BY timestamp DESC',
            (email,)
        ).fetchall()
        for r in rows:
            bid = r['booking_id']
            items = conn.execute(
                'SELECT * FROM bookings WHERE booking_id=?',
                (bid,)
            ).fetchall()
            if not items:
                continue
            first = items[0]
            movie = conn.execute('SELECT title FROM movies WHERE id=?', (first['movie_id'],)).fetchone()
            show = conn.execute('SELECT show_time FROM shows WHERE id=?', (first['show_id'],)).fetchone()
            seats = ', '.join(str(i['seat_no']) for i in items)
            grouped.append({
                'booking_id': bid,
                'movie': movie['title'] if movie else 'Unknown',
                'show_time': show['show_time'] if show else 'Unknown',
                'seats': seats,
                'timestamp': first['timestamp']
            })
        conn.close()

    return render_template('booking_history.html', bookings=grouped, email=email)


@app.route('/update_booking/<booking_id>', methods=['GET', 'POST'])
def update_booking(booking_id):
    conn = get_conn()
    # get all bookings with this ID
    bookings = conn.execute('SELECT * FROM bookings WHERE booking_id=?', (booking_id,)).fetchall()
    if not bookings:
        conn.close()
        flash('Booking not found.')
        return redirect(url_for('booking_history'))

    first = bookings[0]
    movie = conn.execute('SELECT * FROM movies WHERE id=?', (first['movie_id'],)).fetchone()
    show = conn.execute('SELECT * FROM shows WHERE id=?', (first['show_id'],)).fetchone()

    # get already booked seats for this show
    rows = conn.execute('SELECT seat_no FROM bookings WHERE show_id=? AND booking_id<>?', (show['id'], booking_id)).fetchall()
    booked_seats = [int(r['seat_no']) for r in rows]

    if request.method == 'POST':
        new_seats = request.form.getlist('seats')
        try:
            new_seats = [int(s) for s in new_seats]
        except ValueError:
            conn.close()
            flash('Invalid seat selection.')
            return redirect(url_for('update_booking', booking_id=booking_id))

        # replace old seats with new seats
        conn.execute('DELETE FROM bookings WHERE booking_id=?', (booking_id,))
        for s in new_seats:
            conn.execute(
                'INSERT INTO bookings (booking_id, movie_id, show_id, seat_no, name, email, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (booking_id, movie['id'], show['id'], s, first['name'], first['email'], datetime.datetime.now().isoformat())
            )
        conn.commit()
        conn.close()

        flash(f'Booking {booking_id} updated! New seats: {", ".join(map(str, new_seats))}')
        return redirect(url_for('booking_history') + '?email=' + first['email'])

    conn.close()
    return render_template('update_booking.html', booking=first, movie=movie, show=show, booked_seats=booked_seats)


@app.route('/cancel', methods=['POST'])
def cancel_booking():
    """Cancel an existing booking by booking_id and email."""
    booking_id = request.form.get('booking_id')
    email = request.form.get('email')

    if not booking_id or not email:
        flash('Missing booking id or email.')
        return redirect(url_for('booking_history'))

    conn = get_conn()
    row = conn.execute(
        'SELECT COUNT(*) as c FROM bookings WHERE booking_id=? AND email=?',
        (booking_id, email)
    ).fetchone()
    if row['c'] == 0:
        conn.close()
        flash('No matching booking found.')
        return redirect(url_for('booking_history') + '?email=' + email)

    conn.execute(
        'DELETE FROM bookings WHERE booking_id=? AND email=?',
        (booking_id, email)
    )
    conn.commit()
    conn.close()

    flash('Booking cancelled successfully.')
    return redirect(url_for('booking_history') + '?email=' + email)


if __name__ == '__main__':
    # Ensure DB exists before starting
    init_db()
    # Run the Flask app
    app.run(debug=True)
