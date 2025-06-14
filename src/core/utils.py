import logging

import bcrypt
import secrets
import string


def setup_logger(logger_name: str) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                  datefmt='%d-%b-%y %H:%M:%S')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level=logging.INFO)
    console_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(console_handler)

    return logger


def generate_password(length: int = 10):
    alphabet = string.ascii_letters + string.digits

    return ''.join(secrets.choice(alphabet) for _ in range(length))


def encrypt_password(username, password):
    bcrypted = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    return f"{username}:{bcrypted}"