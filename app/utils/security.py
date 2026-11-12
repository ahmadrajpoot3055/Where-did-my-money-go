import hashlib
import uuid
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(password: str) -> str:
    """Hash password using Werkzeug's secure hash (scrypt/pbkdf2)."""
    return generate_password_hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """Verify plaintext password against stored hash."""
    return check_password_hash(password_hash, password)

def hash_token(token: str) -> str:
    """Hash a token using SHA-256 for secure lookup/storage."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def generate_secure_token() -> str:
    """Generate a high-entropy URL-safe token."""
    return secrets.token_urlsafe(32)

def generate_stored_filename(original_filename: str) -> str:
    """Generate a safe random filename keeping safe extension only."""
    import os
    _, ext = os.path.splitext(original_filename)
    clean_ext = ext.lower() if ext else ""
    return f"{uuid.uuid4().hex}{clean_ext}"

def hash_ip(ip_address: str) -> str:
    """Hash an IP address for privacy-preserving audit logs."""
    if not ip_address:
        return ""
    return hashlib.sha256(ip_address.encode('utf-8')).hexdigest()[:32]

