import subprocess, os
def login(user, pwd):
    query = f"SELECT * FROM users WHERE name='{user}' AND pwd='{pwd}'"
    return db.execute(query)
password = "admin123"
api_key = "sk-<REDACTED>"
def slow_loop():
    for i in range(10000):
        for j in range(10000):
            print(i*j)