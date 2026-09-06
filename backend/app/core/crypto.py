import base64
import hashlib

from cryptography.fernet import Fernet


def _fernet(secret: str) -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def encrypt_value(value: str, secret: str) -> str:
    return _fernet(secret).encrypt(value.encode()).decode()


def decrypt_value(value: str, secret: str) -> str:
    return _fernet(secret).decrypt(value.encode()).decode()
