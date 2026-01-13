import sqlite3  #To run SQL Database
import sys  #To exit program
from datetime import datetime  #for date handling

DB_PATH = 'library.db'

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db(conn):
    conn.execute(
        'CREATE TABLE IF NOT EXISTS Library (BK_NAME TEXT, BK_ID TEXT PRIMARY KEY NOT NULL, AUTHOR_NAME TEXT, BK_STATUS TEXT, CARD_ID TEXT, PRICE REAL, YEAR INTEGER, BORROWER_NAME TEXT, RETURN_DATE TEXT)'
    )
    conn.commit()

def display_records(conn):
    cur = conn.execute('SELECT BK_NAME, BK_ID, AUTHOR_NAME, YEAR, PRICE, BK_STATUS, BORROWER_NAME, RETURN_DATE FROM Library ORDER BY BK_NAME')
    rows = cur.fetchall()
    if not rows:
        print('\nNo records found.\n')
        return
    print('\n{:<30} {:<10} {:<12} {:<6} {:<8} {:<10} {:<12} {:<15}'.format('Book Name', 'Book ID', 'Author Name', 'Year', 'Price', 'Status', 'Borrower', 'Return Date'))
    # I used .format to make a table like output for easier reading
    # I Learned this method to help me print columns nicely in the terminal
    # To Align the text so it looks like a table in the console
    # https://www.w3schools.com/python/ref_string_format.asp

    print('-' * 120)
    for r in rows:
        name = (r[0] or '')[:29]
        bid = r[1] or ''
        author = (r[2] or '')[:19]
        year = str(r[3]) if r[3] is not None else ''
        price = f"{r[4]:.2f}" if r[4] is not None else ''
        status = r[5] or ''
        borrower = (r[6] or '')[:14]
        ret = (r[7] or '')
        print('{:<30} {:<10} {:<12} {:<6} {:<8} {:<10} {:<12} {:<15}'.format(name, bid, author, year, price, status, borrower, ret))
    print()

def add_record(conn):
    print('\nAdd new record:')
    name = input('Book Name: ').strip()
    if not name:
        print('Book name cannot be empty.')
        return
    bid = input('Book ID: ').strip()
    if not bid:
        print('Book ID cannot be empty.')
        return
    author = input('Author Name: ').strip() or 'Unknown'
    status = ''
    while status not in ('Available', 'Issued'):
        status = input("Status (Available/Issued) [Available]: ").strip() or 'Available'
    # price and year
    price = None
    p_in = input('Price (e.g. 12.99) [optional]: ').strip()
    if p_in:
        try:
            price = float(p_in)
        except ValueError:
            print('Invalid price format. Use numeric value like 12.99')
            return
    year = None
    y_in = input('Year published [optional]: ').strip()
    if y_in:
        try:
            year = int(y_in)
        except ValueError:
            print('Invalid year. Use a whole number.')
            return
    borrower = None
    return_date = None
    if status == 'Issued':
        borrower = input('Borrower name: ').strip()
        if not borrower:
            print('Borrower name required when status is Issued.')
            return
        rd = input('Return date (YYYY-MM-DD): ').strip()
        try:
            datetime.strptime(rd, '%Y-%m-%d')
            return_date = rd
        except Exception:
            print('Invalid return date. Use YYYY-MM-DD.')
            return
    confirm = input('Confirm add record? (y/N): ').strip().lower() == 'y'
    if not confirm:
        print('Cancelled.')
        return
    try:
        conn.execute(
            'INSERT INTO Library (BK_NAME, BK_ID, AUTHOR_NAME, BK_STATUS, CARD_ID, PRICE, YEAR, BORROWER_NAME, RETURN_DATE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (name, bid, author, status, 'N/A', price, year, borrower or 'N/A', return_date or ''))
        conn.commit()
        print('Record added.')
    except sqlite3.IntegrityError:
        print('Error: Book ID already exists.')

def view_record(conn):
    bid = input('\nEnter Book ID to view: ').strip()
    if not bid:
        print('Book ID required.')
        return
    cur = conn.execute('SELECT BK_NAME, BK_ID, AUTHOR_NAME, YEAR, PRICE, BK_STATUS, BORROWER_NAME, RETURN_DATE FROM Library WHERE BK_ID=?', (bid,))
    r = cur.fetchone()
    if not r:
        print('No record found for Book ID:', bid)
        return
    print('\nBook Name :', r[0])
    print('Book ID   :', r[1])
    print('Author    :', r[2])
    print('Year      :', r[3])
    print('Price     :', f"{r[4]:.2f}" if r[4] is not None and r[4] != '' else r[4])
    print('Status    :', r[5])
    print('Borrower  :', r[6])
    print('Return on :', r[7])

def update_record(conn):
    bid = input('\nEnter Book ID to update: ').strip()
    if not bid:
        print('Book ID required.')
        return
    cur = conn.execute('SELECT BK_NAME, BK_ID, AUTHOR_NAME, YEAR, PRICE, BK_STATUS, BORROWER_NAME, RETURN_DATE FROM Library WHERE BK_ID=?', (bid,))
    r = cur.fetchone()
    if not r:
        print('No record found for Book ID:', bid)
        return
    print('\nLeave field empty to keep current value.')
    name = input(f'Book Name [{r[0]}]: ').strip() or r[0]
    author = input(f'Author [{r[2]}]: ').strip() or r[2]
    year_in = input(f'Year [{r[3] if r[3] is not None else ""}]: ').strip()
    if year_in:
        try:
            year = int(year_in)
        except ValueError:
            print('Invalid year. Keeping current value.')
            year = r[3]
    else:
        year = r[3]
    price_in = input(f'Price [{r[4] if r[4] is not None else ""}]: ').strip()
    if price_in:
        try:
            price = float(price_in)
        except ValueError:
            print('Invalid price. Keeping current value.')
            price = r[4]
    else:
        price = r[4]
    status = input(f'Status (Available/Issued) [{r[5]}]: ').strip() or r[5]
    if status not in ('Available', 'Issued'):
        print('Invalid status. Keeping current value.')
        status = r[5]
    borrower = r[6]
    return_date = r[7]
    if status == 'Issued':
        borrower = input(f'Borrower name [{r[6] if r[6] else ""}]: ').strip() or r[6]
        if not borrower:
            print('Borrower name required when status is Issued.')
            return
        rd = input(f'Return date (YYYY-MM-DD) [{r[7] if r[7] else ""}]: ').strip() or r[7]
        try:
            datetime.strptime(rd, '%Y-%m-%d')
            return_date = rd
        except Exception:
            print('Invalid return date. Use YYYY-MM-DD.')
            return
    else:
        borrower = 'N/A'
        return_date = ''
    conn.execute('UPDATE Library SET BK_NAME=?, AUTHOR_NAME=?, YEAR=?, PRICE=?, BK_STATUS=?, BORROWER_NAME=?, RETURN_DATE=? WHERE BK_ID=?',
                 (name, author, year, price, status, borrower, return_date, bid))
    conn.commit()
    print('Record updated.')

def remove_record(conn):
    bid = input('\nEnter Book ID to remove: ').strip()
    if not bid:
        print('Book ID required.')
        return
    cur = conn.execute('SELECT 1 FROM Library WHERE BK_ID=?', (bid,))
    if not cur.fetchone():
        print('No record found for Book ID:', bid)
        return
    confirm = input('Confirm delete record? (y/N): ').strip().lower() == 'y'
    if not confirm:
        print('Cancelled.')
        return
    conn.execute('DELETE FROM Library WHERE BK_ID=?', (bid,))
    conn.commit()
    print('Record deleted.')

def delete_inventory(conn):
    confirm = input('\nAre you sure you want to delete the entire inventory? This cannot be undone. (type DELETE to confirm): ')
    if confirm == 'DELETE':
        conn.execute('DELETE FROM Library')
        conn.commit()
        print('Inventory cleared.')
    else:
        print('Cancelled.')

def change_availability(conn):
    bid = input('\nEnter Book ID to change availability: ').strip()
    if not bid:
        print('Book ID required.')
        return
    cur = conn.execute('SELECT BK_STATUS FROM Library WHERE BK_ID=?', (bid,))
    r = cur.fetchone()
    if not r:
        print('No record found for Book ID:', bid)
        return
    current = r[0]
    if current == 'Issued':
        confirm = input('Mark as returned (set Available)? (y/N): ').strip().lower() == 'y'
        if confirm:
            conn.execute('UPDATE Library SET BK_STATUS=?, BORROWER_NAME=?, RETURN_DATE=? WHERE BK_ID=?', ('Available', 'N/A', '', bid))
            conn.commit()
            print('Book marked Available.')
        else:
            print('No change made.')
    else:
        borrower = input('Borrower name to mark Issued: ').strip()
        if not borrower:
            print('Borrower name required to mark Issued.')
            return
        rd = input('Return date (YYYY-MM-DD): ').strip()
        try:
            datetime.strptime(rd, '%Y-%m-%d')
        except Exception:
            print('Invalid return date. Use YYYY-MM-DD.')
            return
        conn.execute('UPDATE Library SET BK_STATUS=?, BORROWER_NAME=?, RETURN_DATE=? WHERE BK_ID=?', ('Issued', borrower, rd, bid))
        conn.commit()
        print('Book marked Issued.')

def menu():
    conn = get_connection()
    init_db(conn)
    actions = {
        '1': ('List all books', display_records),
        '2': ('Add a new book', add_record),
        '3': ('View a book by ID', view_record),
        '4': ('Update a book by ID', update_record),
        '5': ('Remove a book by ID', remove_record),
        '6': ('Change availability', change_availability),
        '7': ('Delete entire inventory', delete_inventory),
        '0': ('Exit', None),
    }
    while True:
        print('\nLibrary Management — Menu:')
        for k, v in actions.items():
            print(f' {k}. {v[0]}')
        choice = input('\nChoose an option: ').strip()
        if choice == '0':
            print('Goodbye.')
            conn.close()
            sys.exit(0)
        action = actions.get(choice)
        if not action:
            print('Invalid choice.')
            continue
        # call the function with connection
        func = action[1]
        try:
            func(conn)
        except Exception as e:
            print('Error:', e)

if __name__ == '__main__':
    menu()