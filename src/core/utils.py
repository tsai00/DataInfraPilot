import bcrypt
import secrets
import string


def generate_password(length: int = 10):
    alphabet = string.ascii_letters + string.digits

    return ''.join(secrets.choice(alphabet) for _ in range(length))


def encrypt_password(username, password):
    bcrypted = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    return f"{username}:{bcrypted}"