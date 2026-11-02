"""Authentication and authorization core module."""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from app.config.database import get_connection
from app.models.users import TokenData, UserInDB
import mysql.connector
import bcrypt

_configured_secret = os.environ.get("JWT_SECRET_KEY")
if os.environ.get("ENVIRONMENT", "development").lower() == "production" and not _configured_secret:
    raise RuntimeError("JWT_SECRET_KEY must be configured in production")
if os.environ.get("ENVIRONMENT", "development").lower() in {"production", "prod"} and len(_configured_secret or "") < 32:
    raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters in production")
SECRET_KEY = _configured_secret or secrets.token_urlsafe(48)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12-hour session validity

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
oauth2_optional_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


_memory_users: dict[str, UserInDB] = {}
_memory_user_id_counter: int = 2


def _init_memory_admin():
    admin_pw = os.environ.get("ADMIN_PASSWORD", "DevAdminPassword123!")
    admin_user = UserInDB(
        user_id=1,
        username="admin",
        email="admin@osdbx.local",
        uid_linux=0,
        password_hash=get_password_hash(admin_pw),
        created_at=datetime.now(timezone.utc),
        is_admin=True,
    )
    _memory_users["admin"] = admin_user
    _memory_users["admin@osdbx.local"] = admin_user


_init_memory_admin()


def get_user_by_username(connection: Optional[mysql.connector.MySQLConnection], username: str) -> Optional[UserInDB]:

    uname = (username or "").strip().casefold()
    if connection is None:
        return _memory_users.get(uname)
    try:
        cursor = connection.cursor(dictionary=True)
    except Exception:
        return _memory_users.get(uname)


    cursor = connection.cursor(dictionary=True)
    try:
        try:
            cursor.execute(
                "SELECT user_id, username, email, uid_linux, password_hash, created_at, is_admin "
                "FROM users WHERE username = %s OR email = %s LIMIT 1",
                (username, username)
            )
            user_dict = cursor.fetchone()
        except Exception:
            cursor.execute(
                "SELECT user_id, username, uid_linux, password_hash, created_at, is_admin "
                "FROM users WHERE username = %s LIMIT 1",
                (username,)
            )
            user_dict = cursor.fetchone()
    finally:
        cursor.close()

    if user_dict:
        # If password_hash is None (for legacy data without passwords), set empty string.
        if user_dict.get("password_hash") is None:
            user_dict["password_hash"] = ""
        
        user_dict["is_admin"] = bool(user_dict.get("is_admin"))

        return UserInDB(**user_dict)
    return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """FastAPI dependency: decode JWT token and return current user.

    IMPORTANT: This function opens and closes its OWN DB connection
    independently to avoid closing the connection that route handlers
    use. Do NOT add 'connection = Depends(get_connection)' here.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise credentials_exception

    # Open a dedicated connection just for the auth lookup — do not share
    # this with the route handler's Depends(get_connection).
    try:
        connection = get_connection()
    except Exception:
        connection = None
    try:
        user = get_user_by_username(connection, username=token_data.username)
        if user is None:
            raise credentials_exception
        return user
    finally:
        if connection is not None:
            connection.close()


async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """FastAPI dependency: return authenticated user (extend to check active flag if needed)."""
    return current_user


async def get_optional_user(token: Optional[str] = Depends(oauth2_optional_scheme)) -> Optional[UserInDB]:
    if token is None:
        return None
    return await get_current_user(token)


async def require_admin(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Require the database-backed administrator flag for privileged endpoints."""
    is_admin = current_user.get("is_admin", False) if isinstance(current_user, dict) else current_user.is_admin
    if not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied: Administrator privileges required.")
    return current_user
