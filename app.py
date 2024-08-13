from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
import sqlite3

# App configuration
app = Flask(__name__)
app.secret_key = '777'
socketio = SocketIO(app)
login_manager = LoginManager(app)

# Function to create the users database table
def create_user_table():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        username TEXT UNIQUE,
                        password TEXT
                     )''')
    conn.commit()
    conn.close()

# Function to create the spreadsheet database
def create_spreadsheet_table():
    conn = sqlite3.connect('spreadsheets.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS spreadsheets (
                        id INTEGER PRIMARY KEY,
                        row_index INTEGER,
                        col_index INTEGER,
                        value TEXT
                     )''')
    conn.commit()
    conn.close()

# Function to register a new user in the database
def register_user(username, password):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        hashed_password = generate_password_hash(password)
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# Function to verify if a username already exists
def username_exists(username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user is not None

# Function to verify the login credentials
def verify_login_credentials(username, password):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        hashed_password = user_data[0]
        return check_password_hash(hashed_password, password)
    return False

def get_user_from_database(username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return {'username': user_data[1]}
    else:
        return None
    
@login_manager.user_loader
def load_user(username):
    user_data = get_user_from_database(username)
    if user_data:
        user = User(user_data['username'])
        return user
    return None

# Function to create the spreadsheet if it does not exist
def create_spreadsheet():
    conn = sqlite3.connect('spreadsheets.db')
    cursor = conn.cursor()
    cursor.execute('SELECT row_index, col_index, value FROM spreadsheets')
    data = cursor.fetchall()
    if not data:
        default_data = [
            (row_index, col_index, f'{chr(65 + col_index)}{row_index + 1}')
            for row_index in range(10)
            for col_index in range(10)
        ]
        cursor.executemany('INSERT INTO spreadsheets (row_index, col_index, value) VALUES (?, ?, ?)', default_data)
        conn.commit()
        cursor.execute('SELECT row_index, col_index, value FROM spreadsheets')
        data = cursor.fetchall()
    conn.close()
    return data

# Function to store the spreadsheet data in the database
def store_data_in_db(data):
    conn = sqlite3.connect('spreadsheets.db')
    cursor = conn.cursor()
    try:
        for row_index, fila in enumerate(data):
            for col_index, value in enumerate(fila):
                cursor.execute('UPDATE spreadsheets SET value = ? WHERE row_index = ? AND col_index = ?', (value, row_index, col_index))
        
        conn.commit()
        return jsonify({'message': 'Data saved correctly in the database'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': 'An error occurred while saving the data in the database', 'details': str(e)})
    finally:
        conn.close()

@app.route('/')
def index():
    return render_template('index.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if verify_login_credentials(username, password):
            user = User(username)
            login_user(user)
            return redirect(url_for('principal'))
        else:
            error = "Incorrect data. Please try again."
    return render_template('login.html', error=error)

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username_exists(username):
            error = "The username is already in use. Please choose another one."
        else:
            if register_user(username, password):
                return redirect(url_for('login'))
            else:
                error = "An error occurred during registration."
    return render_template('register.html', error=error)

# Main page
@app.route('/spreadsheet', methods=['GET', 'POST'])
@login_required
def principal():
    if request.method == 'POST':
        data = request.json['data']
        store_data_in_db(data)
        return 'Data saved successfully'
    else:
        create_spreadsheet_table()
        spreadsheet_data = create_spreadsheet()
        return render_template('main.html', spreadsheet_data=spreadsheet_data)  

# Function to handle cell updates via Socket.IO
@socketio.on('update_cell')
def update_cell(data):
    id = data['id']
    text = data['text']
    label = data['label']
    user = current_user.username
    emit('update_cell', {'id': id, 'text': text, 'label': label, 'user': user}, broadcast=True)

class User(UserMixin):
    def __init__(self, username):
        self.username = username
    def get_id(self):
        return self.username
    @staticmethod
    def get(user_id):
        return User(user_id)

if __name__ == '__main__':
    create_user_table()
    create_spreadsheet_table()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)