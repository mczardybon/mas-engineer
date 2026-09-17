import hashlib
def hash_password(pwd):
    return hashlib.md5(pwd.encode()).hexdigest()
password = input("Enter password: ")
print(hash_password(password))
