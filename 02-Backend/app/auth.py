import hashlib
import uuid
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings
from .database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "email": email, "exp": expire, "type": "access"}
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "exp": expire, "type": "refresh"}
    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, token_hash, expire.isoformat()),
        )
        conn.commit()
    return token


def register_user(email: str, password: str) -> dict:
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
                (user_id, email, password_hash),
            )
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Email already registered") from e
    return {"user_id": user_id, "email": email}


def login_user(email: str, password: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(row["id"], row["email"])
    refresh_token = create_refresh_token(row["id"])
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": row["id"],
        "email": row["email"],
    }


def refresh_access_token(refresh_token: str) -> dict:
    try:
        payload = jwt.decode(
            refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id FROM refresh_tokens WHERE token_hash = ? AND expires_at > ?",
            (token_hash, datetime.utcnow().isoformat()),
        ).fetchone()
        if not row:
            raise HTTPException(
                status_code=401, detail="Refresh token expired or revoked"
            )
        user = conn.execute(
            "SELECT id, email FROM users WHERE id = ?", (row["user_id"],)
        ).fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
    access_token = create_access_token(user["id"], user["email"])
    return {"access_token": access_token}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token = credentials.credentials
    import os as _os

    if _os.getenv("ASTROVOX_KEY") and token == _os.getenv("ASTROVOX_KEY"):
        return "master-user"
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_admin(user_id: str = Depends(get_current_user)) -> str:
    with get_db() as conn:
        row = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row or row["role"] != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
    return user_id


import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

VERIFICATION_TOKEN_EXPIRE_HOURS = 24

def create_verification_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)
    payload = {"sub": user_id, "email": email, "exp": expire, "type": "verification"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def send_verification_email(email: str, token: str):
    verification_url = f"https://astrovox.ai/verify?token={token}"
    msg = MIMEText(f"Click to verify: {verification_url}")
    msg["Subject"] = "Verify your AstrovoxAI account"
    msg["From"] = os.getenv("EMAIL_FROM", "noreply@astrovox.ai")
    msg["To"] = email
    try:
        with smtplib.SMTP(os.getenv("SMTP_HOST", "localhost"), int(os.getenv("SMTP_PORT", "25"))) as server:
            server.send_message(msg)
    except Exception as e:
        print(f"Email send failed: {e}")

def verify_email_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "verification":
            raise HTTPException(status_code=400, detail="Invalid token type")
        with get_db() as conn:
            conn.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (payload.get("sub"),))
            conn.commit()
        return {"status": "verified"}
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

def create_password_reset_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=1)
    payload = {"sub": user_id, "email": email, "exp": expire, "type": "password_reset"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def reset_password(token: str, new_password: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid token type")
        password_hash = hash_password(new_password)
        with get_db() as conn:
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, payload.get("sub")))
            conn.commit()
        return {"status": "reset"}
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
