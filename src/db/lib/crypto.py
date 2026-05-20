import base64
import hashlib


def encrypt(raw, key):
    return hashlib.sha256((key + raw).encode()).hexdigest()