"""Authentication and authorization core module."""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config.database import get_connection
from app.models.users import TokenData, UserInDB
import mysql.connector
import bcrypt

# Hardcoded for demo/simplicity; in production this must be secure and loaded from env vars
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "b39a4891b6196b0c20a4b82d334e2c608a1e2f75a7c9383920c7d422a578351b")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


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
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_by_username(connection: mysql.connector.MySQLConnection, username: str) -> Optional[UserInDB]:
    """Look up a user by username. Returns None if not found."""
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT user_id, username, uid_linux, password_hash, created_at FROM users WHERE username = %s",
        (username,)
    )
    user_dict = cursor.fetchone()
    cursor.close()

    if user_dict:
        # If password_hash is None (for legacy data without passwords), set empty string.
        if user_dict.get("password_hash") is None:
            user_dict["password_hash"] = ""
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
    except JWTError:
        raise credentials_exception

    # Open a dedicated connection just for the auth lookup — do not share
    # this with the route handler's Depends(get_connection).
    connection = get_connection()
    try:
        user = get_user_by_username(connection, username=token_data.username)
        if user is None:
            raise credentials_exception
        return user
    finally:
        connection.close()


async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """FastAPI dependency: return authenticated user (extend to check active flag if needed)."""
    return current_user
