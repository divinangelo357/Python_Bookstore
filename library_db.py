"""Data-access layer for the Library Management System.

Pure functions only: no input()/print() here. Callers (CLI or GUI)
handle all user interaction. Every validation failure raises ValueError
with a human-readable message, so a caller can just catch ValueError
and show it however it likes (print(), a message box, etc).
"""
import os
import sqlite3
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'library.db')

STATUSES = ('Available', 'Issued')


def get_connection(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.execute(
        '''CREATE TABLE IF NOT EXISTS Library (
            BK_NAME TEXT NOT NULL,
            BK_ID TEXT PRIMARY KEY NOT NULL,
            AUTHOR_NAME TEXT,
            BK_STATUS TEXT NOT NULL DEFAULT 'Available',
            CARD_ID TEXT,
            PRICE REAL,
            YEAR INTEGER,
            BORROWER_NAME TEXT,
            RETURN_DATE TEXT
        )'''
    )
    conn.commit()


def _row_to_dict(row):
    return dict(row) if row is not None else None


def validate_date(value):
    """Raise ValueError if value isn't a YYYY-MM-DD date string."""
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except (ValueError, TypeError):
        raise ValueError('Return date must be in YYYY-MM-DD format.')


def _validate_common(name, bk_id, status, price, year):
    name = (name or '').strip()
    bk_id = (bk_id or '').strip()
    if not name:
        raise ValueError('Book name cannot be empty.')
    if not bk_id:
        raise ValueError('Book ID cannot be empty.')
    if status not in STATUSES:
        raise ValueError(f'Status must be one of {STATUSES}.')
    if price is not None and price < 0:
        raise ValueError('Price cannot be negative.')
    current_year = datetime.now().year
    if year is not None and not (0 < year <= current_year + 1):
        raise ValueError(f'Year must be between 1 and {current_year + 1}.')
    return name, bk_id


def _validate_issue_fields(status, borrower, return_date):
    """Returns (borrower, return_date) that are safe to store.
    Never silently falls back to a stale value - if status is Issued,
    borrower and return_date must be explicitly provided and valid."""
    if status == 'Issued':
        borrower = (borrower or '').strip()
        if not borrower:
            raise ValueError('Borrower name is required when status is Issued.')
        return_date = (return_date or '').strip()
        if not return_date:
            raise ValueError('Return date is required when status is Issued.')
        validate_date(return_date)
        return borrower, return_date
    return 'N/A', ''


def add_book(conn, name, bk_id, author, status, price, year,
             borrower=None, return_date=None, card_id=None):
    name, bk_id = _validate_common(name, bk_id, status, price, year)
    author = (author or '').strip() or 'Unknown'
    borrower, return_date = _validate_issue_fields(status, borrower, return_date)

    try:
        conn.execute(
            'INSERT INTO Library (BK_NAME, BK_ID, AUTHOR_NAME, BK_STATUS, '
            'CARD_ID, PRICE, YEAR, BORROWER_NAME, RETURN_DATE) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (name, bk_id, author, status, (card_id or '').strip() or 'N/A',
             price, year, borrower, return_date))
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(f'Book ID "{bk_id}" already exists.')


def get_all_books(conn, status_filter=None, search=None, overdue_only=False):
    query = 'SELECT * FROM Library WHERE 1=1'
    params = []
    if status_filter and status_filter != 'All':
        query += ' AND BK_STATUS = ?'
        params.append(status_filter)
    if search:
        query += ' AND (BK_NAME LIKE ? OR AUTHOR_NAME LIKE ? OR BK_ID LIKE ?)'
        like = f'%{search}%'
        params.extend([like, like, like])
    if overdue_only:
        query += " AND BK_STATUS = 'Issued' AND RETURN_DATE != '' AND RETURN_DATE < ?"
        params.append(date.today().isoformat())
    query += ' ORDER BY BK_NAME COLLATE NOCASE'
    cur = conn.execute(query, params)
    return [_row_to_dict(r) for r in cur.fetchall()]


def is_overdue(book, as_of=None):
    as_of = as_of or date.today().isoformat()
    return (book['BK_STATUS'] == 'Issued'
            and book['RETURN_DATE']
            and book['RETURN_DATE'] < as_of)


def get_book(conn, bk_id):
    cur = conn.execute('SELECT * FROM Library WHERE BK_ID = ?', (bk_id,))
    return _row_to_dict(cur.fetchone())


def update_book(conn, bk_id, name, author, year, price, status,
                borrower=None, return_date=None, card_id=None):
    existing = get_book(conn, bk_id)
    if not existing:
        raise ValueError(f'No book found with ID "{bk_id}".')

    name, _ = _validate_common(name or existing['BK_NAME'], bk_id, status, price, year)
    author = (author or '').strip() or existing['AUTHOR_NAME']
    borrower, return_date = _validate_issue_fields(status, borrower, return_date)
    card_id = (card_id or '').strip() or existing['CARD_ID'] or 'N/A'

    conn.execute(
        'UPDATE Library SET BK_NAME=?, AUTHOR_NAME=?, YEAR=?, PRICE=?, '
        'BK_STATUS=?, BORROWER_NAME=?, RETURN_DATE=?, CARD_ID=? WHERE BK_ID=?',
        (name, author, year, price, status, borrower, return_date, card_id, bk_id))
    conn.commit()


def set_status(conn, bk_id, status, borrower=None, return_date=None):
    """Explicit status toggle (mirrors the old 'change availability' action)."""
    existing = get_book(conn, bk_id)
    if not existing:
        raise ValueError(f'No book found with ID "{bk_id}".')
    borrower, return_date = _validate_issue_fields(status, borrower, return_date)
    conn.execute(
        'UPDATE Library SET BK_STATUS=?, BORROWER_NAME=?, RETURN_DATE=? WHERE BK_ID=?',
        (status, borrower, return_date, bk_id))
    conn.commit()


def delete_book(conn, bk_id):
    existing = get_book(conn, bk_id)
    if not existing:
        raise ValueError(f'No book found with ID "{bk_id}".')
    conn.execute('DELETE FROM Library WHERE BK_ID=?', (bk_id,))
    conn.commit()


def delete_all(conn):
    conn.execute('DELETE FROM Library')
    conn.commit()


def get_counts(conn):
    books = get_all_books(conn)
    total = len(books)
    issued = sum(1 for b in books if b['BK_STATUS'] == 'Issued')
    overdue = sum(1 for b in books if is_overdue(b))
    return {'total': total, 'issued': issued, 'overdue': overdue,
            'available': total - issued}