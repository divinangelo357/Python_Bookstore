"""Tkinter GUI for the Library Management System.

Run with:  python3 library_gui.py
Requires library_db.py (the data layer) in the same folder.
This file contains no SQL - all persistence goes through library_db,
so the underlying logic can still be unit tested without a display.
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import library_db as db

# --------------------------------------------------------------- palette --
BG = '#FAF8F3'
PANEL_BG = '#FFFFFF'
ACCENT = '#2E4057'
ACCENT_LIGHT = '#4C6B8A'
TEXT = '#22252B'
MUTED = '#6B7280'
AVAILABLE_FG = '#2F6F4F'
ISSUED_FG = '#B8860B'
OVERDUE_BG = '#FBE4E4'
OVERDUE_FG = '#9B2C2C'
ROW_ALT = '#F3F1EA'
DANGER = '#B3261E'

HEADER_FONT = ('Georgia', 20, 'bold')
SUB_FONT = ('Segoe UI', 10)
LABEL_FONT = ('Segoe UI', 10, 'bold')
BODY_FONT = ('Segoe UI', 10)

COLUMNS = [
    ('BK_NAME', 'Book Name', 220),
    ('BK_ID', 'Book ID', 90),
    ('AUTHOR_NAME', 'Author', 150),
    ('YEAR', 'Year', 60),
    ('PRICE', 'Price', 70),
    ('BK_STATUS', 'Status', 90),
    ('BORROWER_NAME', 'Borrower', 130),
    ('RETURN_DATE', 'Return Date', 100),
]
NUMERIC_COLS = {'YEAR', 'PRICE'}


def _center_on_parent(win, parent):
    win.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - win.winfo_width()) // 2
    y = parent.winfo_y() + (parent.winfo_height() - win.winfo_height()) // 2
    win.geometry(f'+{max(x, 0)}+{max(y, 0)}')


class LibraryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Library Management System')
        self.geometry('1080x620')
        self.minsize(860, 480)
        self.configure(bg=BG)

        self.conn = db.get_connection()
        db.init_db(self.conn)

        self.sort_column = 'BK_NAME'
        self.sort_reverse = False

        self._build_style()
        self._build_menu()
        self._build_layout()
        self.refresh()

    # ------------------------------------------------------------ style --
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass

        style.configure('TFrame', background=BG)
        style.configure('Panel.TFrame', background=PANEL_BG)
        style.configure('TLabel', background=BG, foreground=TEXT, font=BODY_FONT)
        style.configure('Header.TLabel', background=BG, foreground=ACCENT, font=HEADER_FONT)
        style.configure('Sub.TLabel', background=BG, foreground=MUTED, font=SUB_FONT)
        style.configure('Status.TLabel', background=BG, foreground=MUTED, font=SUB_FONT)

        style.configure('TButton', font=BODY_FONT, padding=6)
        style.configure('Primary.TButton', font=LABEL_FONT, padding=7,
                         background=ACCENT, foreground='white')
        style.map('Primary.TButton',
                  background=[('active', ACCENT_LIGHT)])
        style.configure('Danger.TButton', font=BODY_FONT, padding=6,
                         background=DANGER, foreground='white')
        style.map('Danger.TButton', background=[('active', '#8f1f19')])

        style.configure('Treeview', background=PANEL_BG, fieldbackground=PANEL_BG,
                         foreground=TEXT, rowheight=26, font=BODY_FONT, borderwidth=0)
        style.configure('Treeview.Heading', background=ACCENT, foreground='white',
                         font=LABEL_FONT, relief='flat')
        style.map('Treeview.Heading', background=[('active', ACCENT_LIGHT)])
        style.map('Treeview', background=[('selected', ACCENT_LIGHT)],
                  foreground=[('selected', 'white')])

    def _build_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='Refresh', command=self.refresh)
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self.destroy)
        menubar.add_cascade(label='File', menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label='About',
            command=lambda: messagebox.showinfo(
                'About', 'Library Management System\nTkinter GUI over the SQLite backend.'))
        menubar.add_cascade(label='Help', menu=help_menu)
        self.config(menu=menubar)

    # ----------------------------------------------------------- layout --
    def _build_layout(self):
        header = ttk.Frame(self, style='TFrame', padding=(20, 16, 20, 8))
        header.pack(fill='x')
        ttk.Label(header, text='Library', style='Header.TLabel').pack(side='left')
        ttk.Label(header, text='   Book inventory & lending',
                  style='Sub.TLabel').pack(side='left', pady=(8, 0))

        toolbar = ttk.Frame(self, style='TFrame', padding=(20, 4, 20, 8))
        toolbar.pack(fill='x')

        ttk.Label(toolbar, text='Search:', style='TLabel').pack(side='left')
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=26)
        search_entry.pack(side='left', padx=(6, 14))
        search_entry.bind('<Return>', lambda e: self.refresh())

        ttk.Label(toolbar, text='Status:', style='TLabel').pack(side='left')
        self.status_var = tk.StringVar(value='All')
        status_combo = ttk.Combobox(toolbar, textvariable=self.status_var,
                                     values=['All', 'Available', 'Issued'],
                                     state='readonly', width=11)
        status_combo.pack(side='left', padx=(6, 14))
        status_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh())

        self.overdue_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(toolbar, text='Overdue only', variable=self.overdue_var,
                        command=self.refresh).pack(side='left', padx=(0, 14))

        ttk.Button(toolbar, text='Search', command=self.refresh).pack(side='left', padx=4)
        ttk.Button(toolbar, text='Clear', command=self.clear_filters).pack(side='left')

        table_frame = ttk.Frame(self, style='TFrame', padding=(20, 0, 20, 0))
        table_frame.pack(fill='both', expand=True)

        cols = [c[0] for c in COLUMNS]
        self.tree = ttk.Treeview(table_frame, columns=cols, show='headings',
                                 selectmode='browse')
        for key, label, width in COLUMNS:
            self.tree.heading(key, text=label, command=lambda k=key: self.sort_by(k))
            anchor = 'w' if key in ('BK_NAME', 'AUTHOR_NAME', 'BORROWER_NAME') else 'center'
            self.tree.column(key, width=width, anchor=anchor)

        vsb = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self.tree.tag_configure('odd', background=PANEL_BG)
        self.tree.tag_configure('even', background=ROW_ALT)
        self.tree.tag_configure('overdue', background=OVERDUE_BG, foreground=OVERDUE_FG)

        self.tree.bind('<Double-1>', lambda e: self.edit_selected())

        actions = ttk.Frame(self, style='TFrame', padding=(20, 10, 20, 6))
        actions.pack(fill='x')
        ttk.Button(actions, text='+ Add Book', style='Primary.TButton',
                  command=self.add_book).pack(side='left')
        ttk.Button(actions, text='Edit', command=self.edit_selected).pack(side='left', padx=6)
        ttk.Button(actions, text='Toggle Issued/Available',
                  command=self.toggle_selected).pack(side='left', padx=6)
        ttk.Button(actions, text='Delete', command=self.delete_selected).pack(side='left', padx=6)
        ttk.Button(actions, text='Refresh', command=self.refresh).pack(side='left', padx=6)
        ttk.Button(actions, text='Delete All\u2026', style='Danger.TButton',
                  command=self.delete_all).pack(side='right')

        self.status_bar = ttk.Label(self, text='', style='Status.TLabel',
                                    padding=(20, 6, 20, 10))
        self.status_bar.pack(fill='x', side='bottom')

    # ---------------------------------------------------------- helpers --
    def clear_filters(self):
        self.search_var.set('')
        self.status_var.set('All')
        self.overdue_var.set(False)
        self.refresh()

    def selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('No selection', 'Select a book first.')
            return None
        return sel[0]

    def sort_by(self, key):
        if self.sort_column == key:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = key
            self.sort_reverse = False
        self.refresh()

    def refresh(self):
        books = db.get_all_books(
            self.conn,
            status_filter=self.status_var.get(),
            search=self.search_var.get().strip(),
            overdue_only=self.overdue_var.get(),
        )

        col = self.sort_column
        def sort_key(b):
            val = b[col]
            if col in NUMERIC_COLS:
                return val if val is not None else -1
            return (val or '').lower()
        books.sort(key=sort_key, reverse=self.sort_reverse)

        self.tree.delete(*self.tree.get_children())
        for i, book in enumerate(books):
            price = f"{book['PRICE']:.2f}" if book['PRICE'] is not None else ''
            values = [book['BK_NAME'], book['BK_ID'], book['AUTHOR_NAME'] or '',
                      book['YEAR'] if book['YEAR'] is not None else '', price,
                      book['BK_STATUS'], book['BORROWER_NAME'] or '',
                      book['RETURN_DATE'] or '']
            tag = 'overdue' if db.is_overdue(book) else ('even' if i % 2 else 'odd')
            self.tree.insert('', 'end', iid=book['BK_ID'], values=values, tags=(tag,))

        counts = db.get_counts(self.conn)
        self.status_bar.configure(
            text=(f"{counts['total']} books   \u2022   {counts['available']} available   \u2022   "
                  f"{counts['issued']} issued   \u2022   {counts['overdue']} overdue"))

    # ----------------------------------------------------------- actions --
    def add_book(self):
        BookDialog(self, self.conn, mode='add', on_saved=self.refresh)

    def edit_selected(self):
        bk_id = self.selected_id()
        if bk_id:
            BookDialog(self, self.conn, mode='edit', book_id=bk_id, on_saved=self.refresh)

    def toggle_selected(self):
        bk_id = self.selected_id()
        if not bk_id:
            return
        book = db.get_book(self.conn, bk_id)
        if book['BK_STATUS'] == 'Issued':
            if messagebox.askyesno('Mark returned', f"Mark \"{book['BK_NAME']}\" as returned?"):
                try:
                    db.set_status(self.conn, bk_id, 'Available')
                    self.refresh()
                except ValueError as e:
                    messagebox.showerror('Error', str(e))
        else:
            IssueDialog(self, self.conn, bk_id, on_saved=self.refresh)

    def delete_selected(self):
        bk_id = self.selected_id()
        if not bk_id:
            return
        book = db.get_book(self.conn, bk_id)
        if messagebox.askyesno('Delete book',
                               f"Delete \"{book['BK_NAME']}\" ({bk_id})? This cannot be undone."):
            try:
                db.delete_book(self.conn, bk_id)
                self.refresh()
            except ValueError as e:
                messagebox.showerror('Error', str(e))

    def delete_all(self):
        answer = simpledialog.askstring(
            'Delete entire inventory',
            'This deletes every book and cannot be undone.\nType DELETE to confirm:',
            parent=self)
        if answer == 'DELETE':
            db.delete_all(self.conn)
            self.refresh()
        elif answer is not None:
            messagebox.showinfo('Cancelled', 'Inventory was not deleted.')


class BookDialog(tk.Toplevel):
    """Add or edit a book. Stays open on validation errors so nothing typed is lost."""

    def __init__(self, parent, conn, mode='add', book_id=None, on_saved=None):
        super().__init__(parent)
        self.conn = conn
        self.mode = mode
        self.book_id = book_id
        self.on_saved = on_saved
        self.title('Add Book' if mode == 'add' else f'Edit Book \u2014 {book_id}')
        self.configure(bg=PANEL_BG)
        self.resizable(False, False)
        self.transient(parent)

        existing = db.get_book(conn, book_id) if mode == 'edit' else None

        form = ttk.Frame(self, style='Panel.TFrame', padding=20)
        form.pack(fill='both', expand=True)
        form.columnconfigure(1, weight=1)

        self.vars = {}
        self._entries = {}
        row = 0

        def add_field(key, label, default=''):
            nonlocal row
            ttk.Label(form, text=label, style='TLabel').grid(
                row=row, column=0, sticky='w', pady=6)
            var = tk.StringVar(value='' if default is None else str(default))
            entry = ttk.Entry(form, textvariable=var, width=32)
            entry.grid(row=row, column=1, sticky='ew', pady=6, padx=(10, 0))
            self.vars[key] = var
            self._entries[key] = entry
            row += 1
            return entry

        self.name_entry = add_field('name', 'Book Name',
                                    existing['BK_NAME'] if existing else '')
        add_field('bk_id', 'Book ID', book_id if mode == 'edit' else '')
        if mode == 'edit':
            self._entries['bk_id'].configure(state='disabled')
        add_field('author', 'Author', existing['AUTHOR_NAME'] if existing else '')
        add_field('year', 'Year', existing['YEAR'] if existing else '')
        add_field('price', 'Price', existing['PRICE'] if existing else '')

        ttk.Label(form, text='Status', style='TLabel').grid(
            row=row, column=0, sticky='w', pady=6)
        self.status_var = tk.StringVar(value=existing['BK_STATUS'] if existing else 'Available')
        status_combo = ttk.Combobox(form, textvariable=self.status_var, values=list(db.STATUSES),
                                    state='readonly', width=29)
        status_combo.grid(row=row, column=1, sticky='ew', pady=6, padx=(10, 0))
        status_combo.bind('<<ComboboxSelected>>', lambda e: self._toggle_issue_fields())
        row += 1

        borrower_default = ''
        if existing and existing['BORROWER_NAME'] not in (None, 'N/A'):
            borrower_default = existing['BORROWER_NAME']
        add_field('borrower', 'Borrower', borrower_default)
        add_field('return_date', 'Return Date (YYYY-MM-DD)',
                  existing['RETURN_DATE'] if existing else '')

        btns = ttk.Frame(form, style='Panel.TFrame')
        btns.grid(row=row, column=0, columnspan=2, pady=(16, 0), sticky='e')
        ttk.Button(btns, text='Cancel', command=self.destroy).pack(side='right', padx=(6, 0))
        ttk.Button(btns, text='Save', style='Primary.TButton', command=self.save).pack(side='right')

        self._toggle_issue_fields()
        self.name_entry.focus_set()
        _center_on_parent(self, parent)
        self.grab_set()

    def _toggle_issue_fields(self):
        issued = self.status_var.get() == 'Issued'
        state = 'normal' if issued else 'disabled'
        self._entries['borrower'].configure(state=state)
        self._entries['return_date'].configure(state=state)
        if not issued:
            self.vars['borrower'].set('')
            self.vars['return_date'].set('')

    def save(self):
        year_raw = self.vars['year'].get().strip()
        price_raw = self.vars['price'].get().strip()
        try:
            year = int(year_raw) if year_raw else None
            price = float(price_raw) if price_raw else None
        except ValueError:
            messagebox.showerror('Invalid input',
                                 'Year must be a whole number and price a plain number (e.g. 12.99).')
            return

        try:
            if self.mode == 'add':
                db.add_book(self.conn,
                           name=self.vars['name'].get(),
                           bk_id=self.vars['bk_id'].get(),
                           author=self.vars['author'].get(),
                           status=self.status_var.get(),
                           price=price, year=year,
                           borrower=self.vars['borrower'].get(),
                           return_date=self.vars['return_date'].get())
            else:
                db.update_book(self.conn, self.book_id,
                               name=self.vars['name'].get(),
                               author=self.vars['author'].get(),
                               year=year, price=price,
                               status=self.status_var.get(),
                               borrower=self.vars['borrower'].get(),
                               return_date=self.vars['return_date'].get())
        except ValueError as e:
            messagebox.showerror('Could not save', str(e))
            return

        if self.on_saved:
            self.on_saved()
        self.destroy()


class IssueDialog(tk.Toplevel):
    """Quick 'mark as Issued' dialog used by the toolbar toggle button."""

    def __init__(self, parent, conn, book_id, on_saved=None):
        super().__init__(parent)
        self.conn = conn
        self.book_id = book_id
        self.on_saved = on_saved
        self.title(f'Mark Issued \u2014 {book_id}')
        self.configure(bg=PANEL_BG)
        self.resizable(False, False)
        self.transient(parent)

        form = ttk.Frame(self, style='Panel.TFrame', padding=20)
        form.pack(fill='both', expand=True)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text='Borrower name', style='TLabel').grid(
            row=0, column=0, sticky='w', pady=6)
        self.borrower_var = tk.StringVar()
        entry = ttk.Entry(form, textvariable=self.borrower_var, width=30)
        entry.grid(row=0, column=1, pady=6, padx=(10, 0))

        ttk.Label(form, text='Return date (YYYY-MM-DD)', style='TLabel').grid(
            row=1, column=0, sticky='w', pady=6)
        self.date_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.date_var, width=30).grid(
            row=1, column=1, pady=6, padx=(10, 0))

        btns = ttk.Frame(form, style='Panel.TFrame')
        btns.grid(row=2, column=0, columnspan=2, pady=(16, 0), sticky='e')
        ttk.Button(btns, text='Cancel', command=self.destroy).pack(side='right', padx=(6, 0))
        ttk.Button(btns, text='Mark Issued', style='Primary.TButton',
                  command=self.save).pack(side='right')

        entry.focus_set()
        _center_on_parent(self, parent)
        self.grab_set()

    def save(self):
        try:
            db.set_status(self.conn, self.book_id, 'Issued',
                         borrower=self.borrower_var.get(),
                         return_date=self.date_var.get())
        except ValueError as e:
            messagebox.showerror('Could not save', str(e))
            return
        if self.on_saved:
            self.on_saved()
        self.destroy()


if __name__ == '__main__':
    app = LibraryApp()
    app.mainloop()