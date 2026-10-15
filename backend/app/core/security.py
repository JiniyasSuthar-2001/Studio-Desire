import os
import base64
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union
import bcrypt
import jwt
from cryptography.fernet import Fernet

try:
    from app.core.config import settings
except ImportError:
    from backend.app.core.config import settings

logger = logging.getLogger("studio_desire.security")


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    """
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against the stored bcrypt hash.
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.
    """
    now = datetime.now(timezone.utc)
    to_encode = data.copy()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None


def get_token_fernet() -> Fernet:
    """
    Derives a consistent 32-byte Fernet key from CREDENTIAL_ENCRYPTION_KEY or SECRET_KEY.
    """
    key_material = os.getenv("CREDENTIAL_ENCRYPTION_KEY") or settings.SECRET_KEY
    derived = base64.urlsafe_b64encode(hashlib.sha256(key_material.encode("utf-8")).digest())
    return Fernet(derived)


def encrypt_token(plain_token: Optional[str]) -> Optional[str]:
    """
    Encrypts sensitive tokens (OAuth access_token, refresh_token) for secure DB persistence.
    Prepends 'enc:' prefix to distinguish encrypted tokens from legacy plaintext.
    """
    if not plain_token:
        return None
    try:
        f = get_token_fernet()
        return "enc:" + f.encrypt(plain_token.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        logger.error(f"Error encrypting OAuth token: {exc}")
        return plain_token


def decrypt_token(cipher_token: Optional[str]) -> Optional[str]:
    """
    Decrypts persisted OAuth token.
    Transparently handles both 'enc:' prefixed ciphertext and legacy unencrypted plaintext.
    """
    if not cipher_token:
        return None
    if cipher_token.startswith("enc:"):
        raw_cipher = cipher_token[4:]
        try:
            f = get_token_fernet()
            return f.decrypt(raw_cipher.encode("utf-8")).decode("utf-8")
        except Exception as exc:
            logger.error(f"Error decrypting OAuth token: {exc}")
            return None
    # Legacy plaintext token fallback
    return cipher_token

