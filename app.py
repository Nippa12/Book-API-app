from flask import Flask, jsonify, request, redirect, url_for, session
from functools import wraps
import os
import psycopg2

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ---------------------------
# PostgreSQL Connection Setup
# ---------------------------
def get_db_connection(): 
    return psycopg2.connect( 
        host=os.getenv("DATABASE_HOST", "localhost"), 
        port=int(os.getenv("DATABASE_PORT", 5432)),
        dbname=os.getenv("DATABASE_NAME", "app_db"), 
        user=os.getenv("DATABASE_USER", "app_user"), 
        password=os.getenv("DATABASE_PASSWORD") 
    )

# Create table if not exists
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            author VARCHAR(255) NOT NULL
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

init_db()

# Dummy credentials
USERNAME = 'admin'
PASSWORD = 'admin'

# ---------------------------
# Authentication Decorator
# ---------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ---------------------------
# Routes
# ---------------------------
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('get_books_page'))
    return '''
    <html>
        <head><title>Login</title></head>
        <body style="background-color:black; color:white; text-align:center; padding-top:100px;">
            <h1>Welcome to Book API!</h1>
            <form method="POST" action="/login">
                <input type="text" name="username" placeholder="Username" required><br>
                <input type="password" name="password" placeholder="Password" required><br>
                <button type="submit">Login</button>
            </form>
        </body>
    </html>
    '''

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    if username == USERNAME and password == PASSWORD:
        session['username'] = username
        return redirect(url_for('get_books_page'))
    return "Invalid credentials. <a href='/'>Try again</a>", 401

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/books', methods=['GET'])
@login_required
def get_books_page():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, title, author FROM books')
    books = cur.fetchall()
    cur.close()
    conn.close()

    books_html = ''.join(f'''
        <li>
            {title} by {author}
            <form action="/books/delete/{book_id}" method="POST" style="display:inline;">
                <button type="submit" onclick="return confirm('Are you sure you want to delete this book?');">Delete</button>
            </form>
            <form action="/books/edit/{book_id}" method="GET" style="display:inline;">
                <button type="submit">Edit</button>
            </form>
        </li>
    ''' for book_id, title, author in books)

    return f'''
    <html>
        <head><title>Books</title></head>
        <body style="background-color:black; color:white; text-align:center; padding-top:50px;">
            <h1>Books List</h1>
            <button onclick="window.location.href='/books/add'">Add Book</button>
            <ul>{books_html}</ul>
            <button onclick="window.location.href='/logout'" style="color:lightblue;">Logout</button>
        </body>
    </html>
    '''

@app.route('/books/add', methods=['GET'])
@login_required
def add_book_form():
    return '''
    <html>
        <head><title>Add Book</title></head>
        <body style="background-color:black; color:white; text-align:center; padding-top:50px;">
            <h1>Add a New Book</h1>
            <form action="/books/add" method="POST">
                <input type="text" name="title" placeholder="Title" required><br>
                <input type="text" name="author" placeholder="Author" required><br>
                <button type="submit">Add Book</button>
            </form>
        </body>
    </html>
    '''

@app.route('/books/add', methods=['POST'])
@login_required
def add_book():
    title = request.form.get('title')
    author = request.form.get('author')
    if not title or not author:
        return "Missing title or author", 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO books (title, author) VALUES (%s, %s)", (title, author))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('get_books_page'))

@app.route('/books/delete/<int:id>', methods=['POST'])
@login_required
def delete_book(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM books WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('get_books_page'))

@app.route('/books/edit/<int:id>', methods=['GET'])
@login_required
def edit_book_form(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT title, author FROM books WHERE id = %s", (id,))
    book = cur.fetchone()
    cur.close()
    conn.close()

    if book is None:
        return "Book not found", 404

    title, author = book
    return f'''
    <html>
        <head><title>Edit Book</title></head>
        <body style="background-color:black; color:white; text-align:center; padding-top:50px;">
            <h1>Edit Book</h1>
            <form action="/books/edit/{id}" method="POST">
                <input type="text" name="title" value="{title}" required><br>
                <input type="text" name="author" value="{author}" required><br>
                <button type="submit">Update Book</button>
            </form>
        </body>
    </html>
    '''

@app.route('/books/edit/<int:id>', methods=['POST'])
@login_required
def edit_book(id):
    title = request.form.get('title')
    author = request.form.get('author')
    if not title or not author:
        return "Missing title or author", 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE books SET title = %s, author = %s WHERE id = %s", (title, author, id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('get_books_page'))

# ---------------------------
# API Endpoints (no auth)
# ---------------------------
@app.route('/api/books', methods=['GET'])
def get_books_api():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, title, author FROM books')
    books = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"id": b[0], "title": b[1], "author": b[2]} for b in books])

@app.route('/api/books/<int:id>', methods=['GET'])
def get_book_api(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, author FROM books WHERE id = %s", (id,))
    book = cur.fetchone()
    cur.close()
    conn.close()
    if book is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify({"id": book[0], "title": book[1], "author": book[2]})

@app.route('/api/books/<int:id>', methods=['PUT'])
def update_book_api(id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    title = data.get("title")
    author = data.get("author")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE books SET title = %s, author = %s WHERE id = %s", (title, author, id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"id": id, "title": title, "author": author})

@app.route('/api/books/<int:id>', methods=['DELETE'])
def delete_book_api(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM books WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return '', 204

# ---------------------------
# Run the App
# ---------------------------
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
