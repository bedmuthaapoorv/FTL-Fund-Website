"""Credential primitives. Everything here delegates to vetted libraries:
pwdlib/argon2 for passwords, pyotp for TOTP, cryptography's Fernet for
encryption at rest, and `secrets` for randomness. No custom crypto."""

import hashlib
import secrets
import time
from functools import lru_cache

import pyotp
from cryptography.fernet import Fernet
from pwdlib import PasswordHash

from .config import get_settings

_pw = PasswordHash.recommended()  # Argon2id
# Verified against when the email is unknown, so timing doesn't reveal
# which accounts exist.
_DUMMY_HASH = _pw.hash(secrets.token_urlsafe(16))

MIN_PASSWORD_LEN = 12


def hash_password(password: str) -> str:
    return _pw.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    if not hashed:
        _pw.verify(password, _DUMMY_HASH)
        return False
    return _pw.verify(password, hashed)


def password_problem(password: str, email: str = "") -> str | None:
    if len(password) < MIN_PASSWORD_LEN:
        return f"Password must be at least {MIN_PASSWORD_LEN} characters."
    if len(password) > 256:
        return "Password is too long."
    local = email.split("@")[0].lower()
    if len(local) >= 4 and local in password.lower():
        return "Password must not contain your email address."
    return None


def new_token() -> str:
    return secrets.token_urlsafe(32)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@lru_cache
def _fernet() -> Fernet:
    key = get_settings().data_encryption_key
    if not key:
        raise RuntimeError("DATA_ENCRYPTION_KEY is not set (see .env.example)")
    return Fernet(key.encode())


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


# ---- TOTP ----

TOTP_ISSUER = "Frontier TradeLight"


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=TOTP_ISSUER)


def verify_totp(secret: str, code: str, last_step: int) -> int | None:
    """Returns the accepted time-step, or None. Allows +/-1 step of clock
    drift and rejects any step at or before `last_step` (no code reuse)."""
    code = "".join(c for c in code if c.isdigit())
    if len(code) != 6:
        return None
    totp = pyotp.TOTP(secret)
    now_step = int(time.time()) // totp.interval
    for step in (now_step - 1, now_step, now_step + 1):
        if step <= last_step:
            continue
        if secrets.compare_digest(totp.at(step * totp.interval), code):
            return step
    return None


# ---- Recovery codes ----

def new_recovery_codes(n: int = 10) -> list[str]:
    # 10 base32 chars = 50 bits each; high-entropy, so a plain SHA-256 at rest is adequate.
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    codes = []
    for _ in range(n):
        raw = "".join(secrets.choice(alphabet) for _ in range(10))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def normalize_recovery_code(code: str) -> str:
    raw = "".join(c for c in code.upper() if c.isalnum())
    return f"{raw[:5]}-{raw[5:]}"
