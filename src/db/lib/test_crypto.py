from .crypto import encrypt
import pytest


def test_encrypt_decrypt():
    key = "f63ad764d0559b45b3c17370bd23a3143867998e12176bd0ca968ab13da706a0"[:32]
    enc = encrypt("test", key)
    assert enc.startswith("00019")
