"""memex.encryption — encryption at rest for sensitive memories.

AliceLabs proprietary addition. Provides field-level encryption for
memory content stored in ChromaDB. Uses Fernet (AES-128-CBC + HMAC-SHA256)
from the cryptography library.

Features:
  - Per-memory encryption with a master key
  - Key derived from a passphrase via PBKDF2 (100k iterations)
  - Encrypted fields: memory text (payload.data)
  - Metadata stored in plaintext (for filtering)
  - Backward compatible: unencrypted memories still readable
  - Key rotation support

Configuration:
    MEMEX_ENCRYPTION_KEY=base64-key    — explicit Fernet key
    MEMEX_ENCRYPTION_PASSPHRASE=...    — derive key from passphrase
    MEMEX_ENCRYPTION_ENABLED=true      — enable encryption for new writes

If neither MEMEX_ENCRYPTION_KEY nor MEMEX_ENCRYPTION_PASSPHRASE is set,
encryption is disabled and the module is a no-op.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
from typing import Any

logger = logging.getLogger("memex.encryption")

_fernet = None
_enabled = None


def _get_fernet():
    """Get or create the Fernet instance."""
    global _fernet, _enabled

    if _fernet is not None:
        return _fernet

    try:
        from cryptography.fernet import Fernet
    except ImportError:
        logger.debug("[encryption] cryptography library not installed — encryption disabled")
        _enabled = False
        return None

    # Try explicit key first
    key = os.environ.get("MEMEX_ENCRYPTION_KEY")
    if key:
        try:
            _fernet = Fernet(key.encode() if isinstance(key, str) else key)
            _enabled = True
            logger.info("[encryption] Encryption enabled (explicit key)")
            return _fernet
        except Exception as e:
            logger.warning("[encryption] Invalid MEMEX_ENCRYPTION_KEY: %s", e)

    # Try passphrase
    passphrase = os.environ.get("MEMEX_ENCRYPTION_PASSPHRASE")
    if passphrase:
        # Derive key from passphrase using PBKDF2
        salt = b"memex-encryption-salt-v1"  # fixed salt (change in production via config)
        kdf = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, 100_000, dklen=32)
        key = base64.urlsafe_b64encode(kdf)
        _fernet = Fernet(key)
        _enabled = True
        logger.info("[encryption] Encryption enabled (passphrase-derived key)")
        return _fernet

    _enabled = False
    return None


def is_enabled() -> bool:
    """Check if encryption is enabled."""
    if _enabled is None:
        _get_fernet()
    return _enabled or False


def encrypt(text: str) -> str:
    """Encrypt a string. Returns the encrypted string with prefix 'enc:'.

    If encryption is disabled, returns the original text unchanged.
    """
    if not text:
        return text
    f = _get_fernet()
    if not f:
        return text
    try:
        encrypted = f.encrypt(text.encode())
        return "enc:" + encrypted.decode()
    except Exception as e:
        logger.warning("[encryption] Encrypt failed: %s", e)
        return text


def decrypt(text: str) -> str:
    """Decrypt a string. Handles both encrypted and plaintext.

    If the text doesn't have the 'enc:' prefix, returns it unchanged.
    """
    if not text or not text.startswith("enc:"):
        return text
    f = _get_fernet()
    if not f:
        logger.warning("[encryption] Encrypted data found but no key available")
        return text  # return encrypted text (will be unreadable but won't crash)
    try:
        return f.decrypt(text[4:].encode()).decode()
    except Exception as e:
        logger.warning("[encryption] Decrypt failed: %s", e)
        return text


def encrypt_memory(memory: dict[str, Any]) -> dict[str, Any]:
    """Encrypt the text field of a memory dict. Returns a new dict."""
    if not is_enabled():
        return memory
    result = dict(memory)
    if "text" in result and result["text"]:
        result["text"] = encrypt(result["text"])
    if "data" in result and result["data"]:
        result["data"] = encrypt(result["data"])
    return result


def decrypt_memory(memory: dict[str, Any]) -> dict[str, Any]:
    """Decrypt the text field of a memory dict. Returns a new dict."""
    result = dict(memory)
    if "text" in result and result["text"]:
        result["text"] = decrypt(result["text"])
    if "data" in result and result["data"]:
        result["data"] = decrypt(result["data"])
    return result


def generate_key() -> str:
    """Generate a new Fernet key for MEMEX_ENCRYPTION_KEY."""
    try:
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode()
    except ImportError:
        return ""


def rotate_key(old_key: str, new_key: str, memories: list[dict]) -> list[dict]:
    """Re-encrypt memories with a new key.

    Args:
        old_key: The current encryption key
        new_key: The new encryption key
        memories: List of memory dicts to re-encrypt

    Returns:
        List of re-encrypted memory dicts
    """
    import os as _os
    # Temporarily set old key
    _os.environ["MEMEX_ENCRYPTION_KEY"] = old_key
    global _fernet, _enabled
    _fernet = None
    _enabled = None

    decrypted = [decrypt_memory(m) for m in memories]

    # Switch to new key
    _os.environ["MEMEX_ENCRYPTION_KEY"] = new_key
    _fernet = None
    _enabled = None

    return [encrypt_memory(m) for m in decrypted]
