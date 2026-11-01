"""Authentication routes."""

from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordRequestForm
import mysql.connector

from app.config.database import get_connection
from app.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_password_hash,
    get_user_by_username,
    verify_password,
    get_current_active_user,
    get_optional_user,
)
from app.models.users import Token, UserCreate, UserOut, UserInDB
from app.config.settings import settings
from app.services.email_service import send_signin_notification, send_signup_notification

router = APIRouter(prefix="/auth", tags=["auth"])

import time
import threading

_login_failed_attempts: dict[str, list[float]] = {}
_rate_limit_lock = threading.Lock()

def check_rate_limit(keys: tuple[str, ...], max_attempts: int, window_seconds: int, detail: str = "Too many requests. Try again later.") -> None:
    now = time.monotonic()
    with _rate_limit_lock:
        for key in keys:
            recent = [t for t in _login_failed_attempts.get(key, []) if now - t < window_seconds]
            _login_failed_attempts[key] = recent
            if len(recent) >= max_attempts:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)

def record_rate_limited_attempt(keys: tuple[str, ...], window_seconds: int) -> None:
    now = time.monotonic()
    with _rate_limit_lock:
        for key in keys:
            recent = [t for t in _login_failed_attempts.get(key, []) if now - t < window_seconds]
            recent.append(now)
            _login_failed_attempts[key] = recent
        if len(_login_failed_attempts) > 10000:
            for key, attempts in list(_login_failed_attempts.items()):
                if not attempts or now - attempts[-1] >= window_seconds:
                    _login_failed_attempts.pop(key, None)
            while len(_login_failed_attempts) > 10000:
                _login_failed_attempts.pop(next(iter(_login_failed_attempts)))

def clear_rate_limit(keys: tuple[str, ...]) -> None:
    with _rate_limit_lock:
        for key in keys:
            _login_failed_attempts.pop(key, None)


def get_dbms_connection():
    if settings.event_storage.strip().lower() == "memory":
        yield None
        return
    try:
        connection = get_connection()
    except Exception:
        connection = None
    try:
        yield connection
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: UserInDB | None = Depends(get_optional_user),
    connection: mysql.connector.MySQLConnection = Depends(get_dbms_connection)
) -> Any:
    """Register a new user in the system."""
    if not settings.allow_public_registration and not (current_user and current_user.is_admin):
        raise HTTPException(status_code=403, detail="Account creation is restricted to administrators.")
    if user_in.username.strip().lower() in {"admin", "root"}:
        raise HTTPException(status_code=400, detail="This username is reserved.")
    registration_key = (f"register:{request.client.host if request.client else 'unknown'}",)
    check_rate_limit(registration_key, max_attempts=10, window_seconds=3600)
    record_rate_limited_attempt(registration_key, window_seconds=3600)
    existing_user = get_user_by_username(connection, user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    if user_in.email:
        existing_email = get_user_by_username(connection, user_in.email)
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="An account with this email address already exists.",
            )
    
    hashed_password = get_password_hash(user_in.password)
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT COALESCE(MAX(uid_linux), 1000) + 1 FROM users WHERE uid_linux >= 1000")
        row = cursor.fetchone()
        uid_linux = int(row[0]) if row and row[0] is not None else 1001

        try:
            cursor.execute(
                """
                INSERT INTO users (username, email, uid_linux, password_hash)
                VALUES (%s, %s, %s, %s)
                """,
                (user_in.username, user_in.email, uid_linux, hashed_password)
            )
        except mysql.connector.Error as col_err:
            if col_err.errno == 1054:  # Unknown column 'email'
                cursor.execute(
                    """
                    INSERT INTO users (username, uid_linux, password_hash)
                    VALUES (%s, %s, %s)
                    """,
                    (user_in.username, uid_linux, hashed_password)
                )
            else:
                raise
        user_id = int(cursor.lastrowid)
        cursor.execute(
            "INSERT INTO workspaces (name, created_by) VALUES (%s, %s)",
            (f"{user_in.username}'s workspace", user_id),
        )
        workspace_id = int(cursor.lastrowid)
        cursor.execute(
            """
            INSERT INTO workspace_memberships (workspace_id, user_id, role, invited_by)
            VALUES (%s, %s, 'owner', %s)
            """,
            (workspace_id, user_id, current_user.user_id if current_user else None),
        )
        connection.commit()
        cursor.close()
        
        # Fetch the newly created user
        new_user = get_user_by_username(connection, user_in.username)
        if user_in.email:
            background_tasks.add_task(send_signup_notification, user_in.email, user_in.username)
        if new_user:
            out_data = new_user.model_dump()
            out_data["email_notification_sent"] = bool(user_in.email)
            return UserOut(**out_data)
        raise HTTPException(status_code=500, detail="User created but could not be loaded.")
    except mysql.connector.Error as err:
        if err.errno == 1062: # Duplicate entry (maybe uid_linux or email)
            raise HTTPException(status_code=400, detail="UID Linux, Email, or Username already exists")
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/token", response_model=Token)
def login_access_token(
    background_tasks: BackgroundTasks,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    connection: mysql.connector.MySQLConnection = Depends(get_dbms_connection)
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests."""
    keys = (
        f"login-user:{form_data.username.casefold()}",
        f"login-ip:{request.client.host if request.client else 'unknown'}",
    )
    check_rate_limit(keys, max_attempts=15, window_seconds=60, detail="Too many failed login attempts. Try again later.")
    user = get_user_by_username(connection, username=form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        record_rate_limited_attempt(keys, window_seconds=60)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    clear_rate_limit(keys)
    recipient_email = user.email or (form_data.username if "@" in form_data.username else None)
    if recipient_email:
        background_tasks.add_task(send_signin_notification, recipient_email, user.username)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "email_notification_sent": bool(recipient_email),
    }


@router.get("/me", response_model=UserOut)
def read_users_me(
    current_user: UserInDB = Depends(get_current_active_user)
) -> Any:
    """Get current user details."""
    return current_user
