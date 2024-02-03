from flask import Flask, render_template, request, g
import sqlite3
import os
from werkzeug.utils import secure_filename
from flask import send_file

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'home/ubuntu/flaskapp/files')

conn = sqlite3.connect("/var/www/html/flaskapp/user_data.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL
    )
""")
conn.commit()

DATABASE = "/var/www/html/flaskapp/user_data.db"


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

ALLOWED_EXTENSIONS = {'txt'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def count_words_in_file(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            words = content.split()
            return len(words)
    except FileNotFoundError:
        return 0


def get_user_files(username):
    files = []
    user_files_path = os.path.join(app.config['UPLOAD_FOLDER'], username)
    if os.path.exists(user_files_path):
        files = [f for f in os.listdir(user_files_path) if os.path.isfile(os.path.join(user_files_path, f))]
    return files


@app.route("/register", methods=["GET", "POST"])
def register():
    error_message = None
    if request.method == "POST":
        username = request.form["username"]
        file = request.files.get('file')

        if file and allowed_file(file.filename):
            user_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
            os.makedirs(user_upload_folder, exist_ok=True)

            filename = secure_filename(file.filename)
            file_path = os.path.join(user_upload_folder, filename)
            file.save(file_path)

        existing_user = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)

        if existing_user is not None:
            error_message = "Invalid username. Please try again with a new username or log in."
            return render_template('register.html', error_message=error_message)

        else:
            password = request.form["password"]
            first_name = request.form["first_name"]
            last_name = request.form["last_name"]
            email = request.form["email"]

            try:
                conn = get_db()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO users (username, password, first_name, last_name, email)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (username, password, first_name, last_name, email),
                )

                conn.commit()

                row = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)

                user_files = get_user_files(username)
                word_counts = {}

                for file in user_files:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], username + "/" + file)
                    word_count = count_words_in_file(file_path)
                    word_counts[file] = word_count

                return render_template("display_info.html", user_info=row, word_counts=word_counts)

            except sqlite3.Error as e:
                print(f"SQLite error: {e}")

            finally:
                cursor.close()

    return render_template("register.html", error_message=error_message)


@app.route("/login", methods=["GET", "POST"])
def retrieve_info():
    error_message = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        row = query_db("SELECT * FROM users WHERE username = ?", (username,))
        user_files = get_user_files(username)
        word_counts = {}

        for file in user_files:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], username + "/" + file)
            word_count = count_words_in_file(file_path)
            word_counts[file] = word_count

        if row and len(row) > 0 and password == row[0][2]:
            user_info = row[0]
            return render_template("display_info.html", user_info=user_info, word_counts=word_counts)
        else:
            error_message = "Invalid credentials. Please try again."
    return render_template("login.html", error_message=error_message)


@app.route('/files', methods=['POST'])
def download_file():
    try:
        username = request.form.get('username')
        filename = request.form.get('filename')

        if not username or not filename:
            return 'Username and filename are required.', 400

        full_path = f"{app.config['UPLOAD_FOLDER']}/{username}/{filename}"

        return send_file(full_path, as_attachment=True)
    except Exception as e:
        return str(e)


@app.route("/")
def hello():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)

