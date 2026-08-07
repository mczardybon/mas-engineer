import sqlite3, pickle, subprocess
DB_PASSWORD = "SuperSecret123!"
def get_user(username):
    conn = sqlite3.connect("app.db")
    query = f"SELECT * FROM users WHERE name = '{username}'"
    return conn.execute(query).fetchone()
def load_data(filename):
    with open(filename, 'rb') as f: return pickle.load(f)
def run_command(cmd):
    return subprocess.call(f"echo {cmd}", shell=True)
def divide(a, b): return a / b
