import base64
import datetime
import hashlib
import hmac
import json
import secrets
import time
import requests
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from server.config import settings
from server.database import get_db
from server.models_db import AdminUser
from iyal_quality_analyzer.utils.logger import setup_logging

logger = setup_logging("iyal.auth")


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with 200,000 iterations."""
    if not salt:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    )
    return f"pbkdf2_sha256$200000${salt}${dk.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verifies a plaintext password against a stored PBKDF2-HMAC-SHA256 hash in constant time."""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = parts[2]
        expected_hex = parts[3]
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return secrets.compare_digest(dk.hex(), expected_hex)
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(user: AdminUser) -> str:
    """Creates a signed HMAC-SHA256 JWT token for an authenticated admin user."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": now + (settings.JWT_EXPIRE_HOURS * 3600),
    }
    h_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{h_b64}.{p_b64}".encode("ascii")
    sig = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    s_b64 = _b64url_encode(sig)
    return f"{h_b64}.{p_b64}.{s_b64}"


def decode_access_token(token: str) -> dict:
    """Verifies signature and expiration of a JWT token and returns its payload."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        h_b64, p_b64, s_b64 = parts
        signing_input = f"{h_b64}.{p_b64}".encode("ascii")
        expected_sig = hmac.new(
            settings.JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        actual_sig = _b64url_decode(s_b64)
        if not secrets.compare_digest(expected_sig, actual_sig):
            raise ValueError("Invalid token signature")
        payload = json.loads(_b64url_decode(p_b64).decode("utf-8"))
        if int(time.time()) >= int(payload.get("exp", 0)):
            raise ValueError("Token expired")
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {e}",
        )


def verify_google_id_token(id_token: str) -> dict:
    """
    Verifies a Google OAuth2 ID token against Google's tokeninfo endpoint
    and checks audience if GOOGLE_CLIENT_ID is configured.
    """
    try:
        resp = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=8,
        )
        if resp.status_code != 200:
            raise ValueError(f"Google token verification failed (HTTP {resp.status_code})")
        info = resp.json()
        if settings.GOOGLE_CLIENT_ID and info.get("aud") != settings.GOOGLE_CLIENT_ID:
            raise ValueError("Google ID token audience mismatch")
        if str(info.get("email_verified")).lower() != "true":
            raise ValueError("Google email is not verified")
        email = info.get("email", "").strip().lower()
        if not email:
            raise ValueError("No email present in Google ID token")
        return info
    except Exception as e:
        logger.warning(f"Google OAuth verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google Sign-In verification failed: {e}",
        )


def extract_token_from_request(request: Request) -> str:
    """Extracts Bearer token from Authorization header or HttpOnly session cookie."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    cookie_token = request.cookies.get("iyal_admin_token")
    if cookie_token:
        return cookie_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please log in at /admin.",
    )


def get_current_admin(
    request: Request, db: Session = Depends(get_db)
) -> AdminUser:
    """FastAPI dependency that returns the currently authenticated active Admin or Superadmin."""
    token = extract_token_from_request(request)
    payload = decode_access_token(token)
    user_id = int(payload.get("sub", 0))
    user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account not found or deactivated.",
        )
    return user


def require_superadmin(
    current_user: AdminUser = Depends(get_current_admin),
) -> AdminUser:
    """FastAPI dependency that strictly requires 'superadmin' role."""
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin privileges are required to manage admin users.",
        )
    return current_user


def seed_superadmin(db: Session):
    """Ensures the predefined superadmin account exists in the database on startup."""
    existing = (
        db.query(AdminUser)
        .filter(
            (AdminUser.role == "superadmin")
            | (AdminUser.email == settings.SUPERADMIN_EMAIL.lower())
            | (AdminUser.username == settings.SUPERADMIN_USERNAME.lower())
        )
        .first()
    )
    if not existing:
        superadmin = AdminUser(
            email=settings.SUPERADMIN_EMAIL.strip().lower(),
            username=settings.SUPERADMIN_USERNAME.strip().lower(),
            password_hash=hash_password(settings.SUPERADMIN_PASSWORD),
            role="superadmin",
            is_active=True,
            invited_by="system_bootstrap",
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(superadmin)
        db.commit()
        logger.info(
            f"Seeded predefined superadmin user: username='{superadmin.username}', email='{superadmin.email}'"
        )
    else:
        # Ensure predefined user retains superadmin role & active status
        if existing.role != "superadmin" or not existing.is_active:
            existing.role = "superadmin"
            existing.is_active = True
            db.commit()

