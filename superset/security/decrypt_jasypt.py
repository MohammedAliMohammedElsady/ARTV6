"""Decrypt a Jasypt value using PBEWITHHMACSHA512ANDAES_256.

    pip install cryptography
    python3 jasypt_sha512_aes256.py
"""

import base64
import hashlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ITERATIONS = 100000
KEY_LEN = 32  # AES-256


def jasypt_decrypt(EncryptionKey, EncryptedValue):
    raw = base64.b64decode(EncryptedValue.strip())
    pw = EncryptionKey.encode("ascii")

    # PBEWITHHMACSHA512ANDAES_256: salt = first 16 bytes, IV = next 16 bytes
    salt = raw[:16]
    iv = raw[16:32]
    body = raw[32:]

    key = hashlib.pbkdf2_hmac("sha512", pw, salt, ITERATIONS, KEY_LEN)

    dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    out = dec.update(body) + dec.finalize()

    # strip PKCS7 padding
    n = out[-1]
    return out[:-n].decode("utf-8")
