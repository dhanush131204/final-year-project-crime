from cryptography.fernet import Fernet
import os

# Generate or Load the Master Key
def get_master_key():
    # We will store this in a hidden file called .masterraw for security
    key_file = "database/.master_vault.key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
        return key

def encrypt_file(file_path):
    key = get_master_key()
    f = Fernet(key)
    with open(file_path, "rb") as file:
        file_data = file.read()
    encrypted_data = f.encrypt(file_data)
    with open(file_path, "wb") as file:
        file.write(encrypted_data)

def decrypt_file_to_bytes(file_path):
    key = get_master_key()
    f = Fernet(key)
    with open(file_path, "rb") as file:
        encrypted_data = file.read()
    return f.decrypt(encrypted_data)
