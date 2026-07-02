"""
Crypto service — AES-256-GCM encryption for API keys and sensitive data.

The application ships with a pre-configured Groq API key so users get AI
features immediately. The key is encrypted using AES-256-GCM with a
machine-bound derived key so it cannot simply be extracted from the binary.

Encryption scheme:
  - Algorithm  : AES-256-GCM
  - Key        : PBKDF2-HMAC-SHA256 from machine-bound secret + app salt
  - IV/Nonce   : 12 random bytes per encryption (prepended to ciphertext)
  - Auth tag   : 16 bytes (appended)
  - Output     : Base64 string: [iv(12)] + [ciphertext(n)] + [tag(16)]
"""

import os
import base64
import hashlib
import socket
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# Application salt — unique to Moltin TypeWriter
_APP_SALT = bytes.fromhex("4d6f6c74696e5479706557726974657253616c74")


def _derive_key() -> bytes:
    """
    Derives a 256-bit key from a stable machine identifier.
    Ties encrypted values to this installation without needing a password.
    """
    try:
        username = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
        hostname = socket.gethostname()
        machine_id = f"{username}@{hostname}".encode("utf-8")
    except Exception:
        machine_id = b"moltin-default-machine"

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_APP_SALT,
        iterations=100_000,
    )
    return kdf.derive(machine_id)


def encrypt(plaintext: str) -> str:
    """
    Encrypts a plaintext string using AES-256-GCM.
    Returns a Base64-encoded string containing: nonce + ciphertext + tag.
    """
    key = _derive_key()
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    # AESGCM.encrypt returns ciphertext + 16-byte tag concatenated
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt(encrypted_b64: str) -> str | None:
    """
    Decrypts a Base64 AES-256-GCM value.
    Returns the plaintext string, or None if decryption fails.
    """
    try:
        key = _derive_key()
        data = base64.b64decode(encrypted_b64)
        nonce = data[:12]
        ciphertext_with_tag = data[12:]
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext.decode("utf-8")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# API keys are now provided exclusively by the user via the Settings UI.
# ---------------------------------------------------------------------------
