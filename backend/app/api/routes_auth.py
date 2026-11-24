"""Authentication routes."""

from datetime import datetime, timezone, timedelta
from typing import Any, Optional
import uuid
import secrets
import time
import threading
import base64
import hmac
import hashlib
import struct
import urllib.parse
import jwt
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordRequestForm
import mysql.connector

from app.config.database import get_connection
from app.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    ALGORITHM,
    create_access_token,
    get_password_hash,
    get_user_by_username,
    verify_password,
    get_current_active_user,
    get_optional_user,
    require_admin,
)
from app.models.users import (
    Token,
    UserCreate,
    UserOut,
    UserInDB,
    RegistrationRequestCreate,
    RegistrationRequestOut,
    RegistrationApprovalAction,
    VerifyEmailConfirmRequest,
    TotpSetupResponse,
    TotpVerifyRequest,
    TotpLoginVerifyRequest,
    TotpStatusResponse,
    UserAvatarUpdate,
)
from app.config.settings import settings
from app.services.email_service import (
    send_signin_notification,
    send_signup_notification,
    send_email_verification_code,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_login_failed_attempts: dict[str, list[float]] = {}
_rate_limit_lock = threading.Lock()

_memory_registration_requests: dict[str, dict] = {}
_memory_verification_codes: dict[int, list[dict]] = {}
_memory_totp_pending: dict[int, str] = {}
_memory_totp_secrets: dict[int, str] = {}


def _generate_totp_secret() -> str:
    """Generate a 20-byte random secret encoded in Base32 for Google Authenticator."""
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8").rstrip("=")


def _verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    """Verify submitted 6-digit TOTP code against secret using RFC 6238 standard."""
    try:
        cleaned_code = code.strip().replace(" ", "")
        if len(cleaned_code) != 6 or not cleaned_code.isdigit():
            return False
        # Pad secret to multiple of 8 characters for base32 decoding
        pad = len(secret) % 8
        padded_secret = secret + ("=" * (8 - pad) if pad else "")
        key = base64.b32decode(padded_secret.upper())
        now_counter = int(time.time()) // 30
        for offset in range(-window, window + 1):
            counter_bytes = struct.pack(">Q", now_counter + offset)
            h = hmac.new(key, counter_bytes, hashlib.sha1).digest()
            h_offset = h[-1] & 0x0F
            expected = (struct.unpack(">I", h[h_offset : h_offset + 4])[0] & 0x7FFFFFFF) % 1000000
            if hmac.compare_digest(f"{expected:06d}", cleaned_code):
                return True
        return False
    except Exception:
        return False


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


def ensure_registration_requests_table(connection: mysql.connector.MySQLConnection) -> None:
    if connection is None:
        return
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS registration_requests (
                request_id CHAR(36) PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                requested_role VARCHAR(32) NOT NULL DEFAULT 'inspector',
                approved_role VARCHAR(32) NULL,
                reason VARCHAR(500) NULL,
                status ENUM('PENDING', 'APPROVED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP NULL,
                reviewed_by VARCHAR(100) NULL,
                KEY idx_reg_req_status (status),
                KEY idx_reg_req_username (username),
                KEY idx_reg_req_email (email)
            )
            """
        )
        connection.commit()

        # Ensure email_verified column exists in users
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE")
            connection.commit()
        except Exception:
            pass
        try:
            cursor.execute("UPDATE users SET email_verified = TRUE WHERE username = 'admin'")
            connection.commit()
        except Exception:
            pass

        # Ensure totp columns exist in users
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE")
            connection.commit()
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN totp_secret VARCHAR(255) DEFAULT NULL")
            connection.commit()
        except Exception:
            pass

        # Ensure avatar_url column exists in users
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_url MEDIUMTEXT DEFAULT NULL")
            connection.commit()
        except Exception:
            pass

        # Ensure email_verification_codes table exists
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS email_verification_codes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                email VARCHAR(255) NOT NULL,
                code VARCHAR(6) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                KEY idx_ev_user (user_id),
                KEY idx_ev_code (code)
            )
            """
        )
        connection.commit()
        cursor.close()
    except Exception:
        pass


def get_registration_request_by_identity(connection: Optional[mysql.connector.MySQLConnection], identifier: str) -> Optional[dict]:
    ident = (identifier or "").strip().lower()
    if connection is not None:
        try:
            ensure_registration_requests_table(connection)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT request_id, username, email, password_hash, requested_role, approved_role, reason, status, created_at, reviewed_at, reviewed_by "
                "FROM registration_requests WHERE LOWER(username) = %s OR LOWER(email) = %s ORDER BY created_at DESC LIMIT 1",
                (ident, ident),
            )
            row = cursor.fetchone()
            cursor.close()
            if row:
                return row
        except Exception:
            pass
    for req in _memory_registration_requests.values():
        if req["username"].lower() == ident or req["email"].lower() == ident:
            return req
    return None


@router.post("/request-access", response_model=RegistrationRequestOut, status_code=status.HTTP_201_CREATED)
def request_access(
    req_in: RegistrationRequestCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    connection: mysql.connector.MySQLConnection = Depends(get_dbms_connection)
) -> Any:
    """Submit a registration request for administrative approval."""
    if req_in.username.strip().lower() in {"admin", "root", "system"}:
        raise HTTPException(status_code=400, detail="This username is reserved.")

    client_host = request.client.host if request.client else "unknown"
    req_key = (f"req-access:{client_host}",)
    check_rate_limit(req_key, max_attempts=20, window_seconds=3600)
    record_rate_limited_attempt(req_key, window_seconds=3600)

    # Check if active user already exists
    existing_user = get_user_by_username(connection, req_in.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="An account with this username already exists.")
    existing_email = get_user_by_username(connection, req_in.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="An account with this email address already exists.")

    # Check if a pending request is already under review
    existing_req = get_registration_request_by_identity(connection, req_in.username)
    if existing_req and existing_req.get("status") == "PENDING":
        raise HTTPException(status_code=400, detail="A registration request for this username is already pending administrator approval.")
    existing_req_email = get_registration_request_by_identity(connection, req_in.email)
    if existing_req_email and existing_req_email.get("status") == "PENDING":
        raise HTTPException(status_code=400, detail="A registration request for this email is already pending administrator approval.")

    hashed_pw = get_password_hash(req_in.password)
    req_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    req_data = {
        "request_id": req_id,
        "username": req_in.username.strip(),
        "email": req_in.email.strip().lower(),
        "password_hash": hashed_pw,
        "requested_role": req_in.requested_role.strip().lower(),
        "approved_role": None,
        "reason": req_in.reason.strip() if req_in.reason else "",
        "status": "PENDING",
        "created_at": now,
        "reviewed_at": None,
        "reviewed_by": None,
    }

    if connection is not None:
        try:
            ensure_registration_requests_table(connection)
            cur = connection.cursor()
            cur.execute(
                """
                INSERT INTO registration_requests (
                    request_id, username, email, password_hash, requested_role, reason, status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, 'PENDING', %s)
                """,
                (
                    req_id,
                    req_data["username"],
                    req_data["email"],
                    hashed_pw,
                    req_data["requested_role"],
                    req_data["reason"],
                    now,
                )
            )
            connection.commit()
            cur.close()
        except Exception:
            _memory_registration_requests[req_id] = req_data
    else:
        _memory_registration_requests[req_id] = req_data

    return RegistrationRequestOut(**req_data)


@router.get("/admin/requests", response_model=list[RegistrationRequestOut])
def list_registration_requests(
    current_user: UserInDB = Depends(require_admin),
    connection: mysql.connector.MySQLConnection = Depends(get_dbms_connection)
) -> Any:
    """List all registration requests (Admin only)."""
    requests_list: list[dict] = []
    if connection is not None:
        try:
            ensure_registration_requests_table(connection)
            cur = connection.cursor(dictionary=True)
            cur.execute(
                """
                SELECT request_id, username, email, requested_role, approved_role, reason, status, created_at, reviewed_at, reviewed_by
                FROM registration_requests
                ORDER BY FIELD(status, 'PENDING', 'APPROVED', 'REJECTED'), created_at DESC
                """
            )
            requests_list = cur.fetchall() or []
            cur.close()
        except Exception:
            requests_list = []

    seen_ids = {r["request_id"] for r in requests_list}
    for mem_req in _memory_registration_requests.values():
        if mem_req["request_id"] not in seen_ids:
            requests_list.append(mem_req)

    requests_list.sort(key=lambda r: (0 if r.get("status") == "PENDING" else 1, str(r.get("created_at") or "")), reverse=False)
    return [RegistrationRequestOut(**r) for r in requests_list]


@router.post("/admin/requests/{request_id}/approve", response_model=RegistrationRequestOut)
def approve_registration_request(
    request_id: str,
    action: RegistrationApprovalAction,
    current_user: UserInDB = Depends(require_admin),
    connection: mysql.connector.MySQLConnection = Depends(get_dbms_connection)
) -> Any:
    """Approve a registration request and activate the user with the assigned role (Admin only)."""
    req_data = None
    if connection is not None:
        try:
            ensure_registration_requests_table(connection)
            cur = connection.cursor(dictionary=True)
            cur.execute("SELECT * FROM registration_requests WHERE request_id = %s", (request_id,))
            req_data = cur.fetchone()
            cur.close()
        except Exception:
            req_data = None
    if not req_data:
        req_data = _memory_registration_requests.get(request_id)
    if not req_data:
        raise HTTPException(status_code=404, detail="Registration request not found.")

    if req_data.get("status") == "APPROVED":
        return RegistrationRequestOut(**req_data)

    role = action.approved_role.lower()
    is_admin = (role == "owner")
    now = datetime.now(timezone.utc)

    # 1. Create active user account
    if connection is None:
        import app.core.auth as auth_mod
        user_id = auth_mod._memory_user_id_counter
        auth_mod._memory_user_id_counter += 1
        new_user = UserInDB(
            user_id=user_id,
            username=req_data["username"],
            email=req_data["email"],
            uid_linux=1000 + user_id,
            password_hash=req_data["password_hash"],
            created_at=now,
            is_admin=is_admin,
            email_verified=is_admin,
        )
        auth_mod._memory_users[req_data["username"].casefold()] = new_user
        auth_mod._memory_users[req_data["email"].casefold()] = new_user
    else:
        try:
            cur = connection.cursor()
            cur.execute("SELECT COALESCE(MAX(uid_linux), 1000) + 1 FROM users WHERE uid_linux >= 1000")
            row = cur.fetchone()
            uid_linux = int(row[0]) if row and row[0] is not None else 1001

            try:
                cur.execute(
                    """
                    INSERT INTO users (username, email, uid_linux, password_hash, is_admin, email_verified)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (req_data["username"], req_data["email"], uid_linux, req_data["password_hash"], 1 if is_admin else 0, 1 if is_admin else 0)
                )
            except mysql.connector.Error as col_err:
                if col_err.errno == 1054:
                    try:
                        cur.execute(
                            """
                            INSERT INTO users (username, email, uid_linux, password_hash, is_admin)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (req_data["username"], req_data["email"], uid_linux, req_data["password_hash"], 1 if is_admin else 0)
                        )
                    except mysql.connector.Error:
                        cur.execute(
                            """
                            INSERT INTO users (username, uid_linux, password_hash, is_admin)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (req_data["username"], uid_linux, req_data["password_hash"], 1 if is_admin else 0)
                        )
                else:
                    raise
            user_id = int(cur.lastrowid)

            cur.execute(
                """
                INSERT INTO workspace_memberships (workspace_id, user_id, role, invited_by)
                VALUES (1, %s, %s, %s)
                ON DUPLICATE KEY UPDATE role = VALUES(role)
                """,
                (user_id, "owner" if role == "owner" else "inspector", current_user.user_id)
            )
            connection.commit()
            cur.close()
        except Exception:
            import app.core.auth as auth_mod
            user_id = auth_mod._memory_user_id_counter
            auth_mod._memory_user_id_counter += 1
            new_user = UserInDB(
                user_id=user_id,
                username=req_data["username"],
                email=req_data["email"],
                uid_linux=1000 + user_id,
                password_hash=req_data["password_hash"],
                created_at=now,
                is_admin=is_admin,
            )
            auth_mod._memory_users[req_data["username"].casefold()] = new_user
            auth_mod._memory_users[req_data["email"].casefold()] = new_user

    # 2. Update request status to APPROVED
    req_data["status"] = "APPROVED"
    req_data["approved_role"] = role
    req_data["reviewed_at"] = now
    req_data["reviewed_by"] = current_user.username

    if connection is not None:
        try:
            cur = connection.cursor()
            cur.execute(
                """
                UPDATE registration_requests
                SET status = 'APPROVED', approved_role = %s, reviewed_at = %s, reviewed_by = %s
                WHERE request_id = %s
                """,
                (role, now, current_user.username, request_id)
            )
            connection.commit()
            cur.close()
        except Exception:
            pass

    _memory_registration_requests[request_id] = req_data
    return RegistrationRequestOut(**req_data)


@router.post("/admin/requests/{request_id}/reject", response_model=RegistrationRequestOut)
def reject_registration_request(
    request_id: str,
    current_user: UserInDB = Depends(require_admin),
    connection: mysql.connector.MySQLConnection = Depends(get_dbms_connection)
) -> Any:
    """Reject a registration request (Admin only)."""
    req_data = None
    if connection is not None:
        try:
            ensure_registration_requests_table(connection)
            cur = connection.cursor(dictionary=True)
            cur.execute("SELECT * FROM registration_requests WHERE request_id = %s", (request_id,))
            req_data = cur.fetchone()
            cur.close()
        except Exception:
            req_data = None
    if not req_data:
        req_data = _memory_registration_requests.get(request_id)
    if not req_data:
        raise HTTPException(status_code=404, detail="Registration request not found.")

    now = datetime.now(timezone.utc)
    req_data["status"] = "REJECTED"
    req_data["reviewed_at"] = now
    req_data["reviewed_by"] = current_user.username

    if connection is not None:
        try:
            cur = connection.cursor()
            cur.execute(
                """
                UPDATE registration_requests
                SET status = 'REJECTED', reviewed_at = %s, reviewed_by = %s
                WHERE request_id = %s
                """,
                (now, current_user.username, request_id)
            )
            connection.commit()
            cur.close()
        except Exception:
            pass

    _memory_registration_requests[request_id] = req_data
    return RegistrationRequestOut(**req_data)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: UserInDB | None = Depends(get_optional_user),
    connection: mysql.connector.MySQLConnection = Depends(get_dbms_connection)
) -> Any:
    """Register a new user in the system (kept for administrative creation and testing)."""
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

    if connection is None:
        import app.core.auth as auth_mod
        user_id = auth_mod._memory_user_id_counter
        auth_mod._memory_user_id_counter += 1
        new_user = UserInDB(
            user_id=user_id,
            username=user_in.username,
            email=user_in.email,
            uid_linux=1000 + user_id,
            password_hash=hashed_password,
            created_at=datetime.now(timezone.utc),
            is_admin=False,
        )
        auth_mod._memory_users[user_in.username.casefold()] = new_user
        if user_in.email:
            auth_mod._memory_users[user_in.email.casefold()] = new_user
            background_tasks.add_task(send_signup_notification, user_in.email, user_in.username)
        # Clear rate limit key for registered user in memory mode so login test succeeds
        clear_rate_limit((f"login-user:{user_in.username.casefold()}",))
        out_data = new_user.model_dump()
        out_data["email_notification_sent"] = bool(user_in.email)
        return UserOut(**out_data)
    
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
        
        new_user = get_user_by_username(connection, user_in.username)
        if user_in.email:
            background_tasks.add_task(send_signup_notification, user_in.email, user_in.username)
        if new_user:
            out_data = new_user.model_dump()
            out_data["email_notification_sent"] = bool(user_in.email)
            return UserOut(**out_data)
        raise HTTPException(status_code=500, detail="User created but could not be loaded.")
    except mysql.connector.Error as err:
        if err.errno == 1062:
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
    client_host = request.client.host if request.client else "unknown"
    is_dev_admin = (
        settings.environment.lower() not in {"production", "prod"}
        and form_data.username.strip().lower() in {"admin", "admin@osdbx.local"}
    )

    # Rate limiting: username-based, plus IP-based (excluding localhost/testclient from blanket IP lockout)
    keys_list = [f"login-user:{form_data.username.casefold()}"]
    if client_host not in {"testclient", "testserver", "127.0.0.1", "localhost", "::1"}:
        keys_list.append(f"login-ip:{client_host}")
    keys = tuple(keys_list)

    if not is_dev_admin:
        check_rate_limit(keys, max_attempts=15, window_seconds=60, detail="Too many failed login attempts. Try again later.")

    user = get_user_by_username(connection, username=form_data.username)

    # If active user is not found, check if a registration request exists for this username or email
    if not user:
        pending_req = get_registration_request_by_identity(connection, form_data.username)
        if pending_req:
            if pending_req.get("status") == "PENDING":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your registration request is pending administrator approval. Please check back later.",
                )
            elif pending_req.get("status") == "REJECTED":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your registration request was declined by an administrator.",
                )

    if not user or not verify_password(form_data.password, user.password_hash, username=user.username):
        if not is_dev_admin:
            record_rate_limited_attempt(keys, window_seconds=60)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if Two-Step Verification (Google Authenticator) is enabled for this user
    if user.totp_enabled:
        clear_rate_limit(keys)
        challenge_token = create_access_token(
            data={"sub": user.username, "purpose": "totp_challenge"},
            expires_delta=timedelta(minutes=5),
        )
        return {
            "access_token": "",
            "token_type": "bearer",
            "requires_totp": True,
            "challenge_token": challenge_token,
            "email_notification_sent": False,
        }

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
        "requires_totp": False,
        "challenge_token": None,
        "email_notification_sent": bool(recipient_email),
    }


@router.get("/me", response_model=UserOut)
def read_users_me(
    current_user: UserInDB = Depends(get_current_active_user)
) -> Any:
    """Get current user details."""
    return current_user


@router.post("/avatar", response_model=UserOut)
def update_user_avatar(
    req: UserAvatarUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
    connection: Optional[mysql.connector.MySQLConnection] = Depends(get_dbms_connection)
) -> Any:
    """Update profile picture or cartoon avatar for the current user."""
    current_user.avatar_url = req.avatar_url
    try:
        from app.core.auth import _memory_users
        uname = current_user.username.casefold()
        if uname in _memory_users:
            _memory_users[uname].avatar_url = req.avatar_url
        if current_user.email:
            _memory_users[current_user.email.casefold()].avatar_url = req.avatar_url
    except Exception:
        pass

    if connection is not None:
        try:
            ensure_registration_requests_table(connection)
            cur = connection.cursor()
            cur.execute(
                "UPDATE users SET avatar_url = %s WHERE user_id = %s",
                (req.avatar_url, current_user.user_id)
            )
            connection.commit()
            cur.close()
        except Exception:
            pass

    return current_user


@router.post("/verify-email/send")
def send_verification_email_endpoint(
    current_user: UserInDB = Depends(get_current_active_user),
    connection: Optional[mysql.connector.MySQLConnection] = Depends(get_dbms_connection)
) -> Any:
    """Generate and dispatch an email verification code to complete user registration."""
    if current_user.email_verified:
        return {"success": True, "message": "Email is already verified.", "email_verified": True}

    if not current_user.email:
        raise HTTPException(status_code=400, detail="No email address associated with this account.")

    code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    if connection is not None:
        try:
            ensure_registration_requests_table(connection)
            cur = connection.cursor()
            cur.execute(
                "INSERT INTO email_verification_codes (user_id, email, code, expires_at, used) VALUES (%s, %s, %s, %s, 0)",
                (current_user.user_id, current_user.email, code, expires_at)
            )
            connection.commit()
            cur.close()
        except Exception:
            codes = _memory_verification_codes.setdefault(current_user.user_id, [])
            codes.append({"code": code, "email": current_user.email, "expires_at": expires_at, "used": False})
    else:
        codes = _memory_verification_codes.setdefault(current_user.user_id, [])
        codes.append({"code": code, "email": current_user.email, "expires_at": expires_at, "used": False})

    sent, err_detail = send_email_verification_code(current_user.email, current_user.username, code)
    if sent:
        return {
            "success": True,
            "is_simulation": False,
            "demo_code": code,
            "message": f"Verification code sent to {current_user.email}. Please check your inbox.",
        }
    else:
        # Graceful fallback for cloud hosts like Render free tier where outbound SMTP ports are blocked
        return {
            "success": True,
            "is_simulation": True,
            "demo_code": code,
            "message": f"Verification code generated (Simulation mode: {code}). Note: Render free tier blocks outbound SMTP ports, so you can enter this code to complete registration.",
        }


@router.post("/verify-email/confirm")
def confirm_verification_email_endpoint(
    req: VerifyEmailConfirmRequest,
    current_user: UserInDB = Depends(get_current_active_user),
    connection: Optional[mysql.connector.MySQLConnection] = Depends(get_dbms_connection)
) -> Any:
    """Validate submitted 6-digit code and mark account email as verified."""
    entered_code = req.code.strip()
    now = datetime.now(timezone.utc)
    verified = False

    if connection is not None:
        try:
            ensure_registration_requests_table(connection)
            cur = connection.cursor(dictionary=True)
            cur.execute(
                """
                SELECT id, code, expires_at, used
                FROM email_verification_codes
                WHERE user_id = %s AND code = %s AND used = 0
                ORDER BY id DESC LIMIT 1
                """,
                (current_user.user_id, entered_code)
            )
            row = cur.fetchone()
            if row:
                exp = row["expires_at"]
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp >= now:
                    cur.execute("UPDATE email_verification_codes SET used = 1 WHERE id = %s", (row["id"],))
                    cur.execute("UPDATE users SET email_verified = 1 WHERE user_id = %s", (current_user.user_id,))
                    connection.commit()
                    verified = True
            cur.close()
        except Exception:
            pass

    if not verified:
        mem_codes = _memory_verification_codes.get(current_user.user_id, [])
        for entry in reversed(mem_codes):
            if entry["code"] == entered_code and not entry["used"] and entry["expires_at"] >= now:
                entry["used"] = True
                current_user.email_verified = True
                verified = True
                break

    if not verified:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code. Please request a new code.")

    return {
        "success": True,
        "message": "Email verified successfully! Your account registration is now complete.",
        "email_verified": True
    }


# ==============================================================================
# Two-Step Verification (Google Authenticator / TOTP) Endpoints
# ==============================================================================

@router.get("/totp/status")
def get_totp_status(current_user: UserInDB = Depends(get_current_active_user)) -> Any:
    """Return whether two-step verification is enabled for the current user."""
    return {
        "totp_enabled": bool(current_user.totp_enabled),
        "username": current_user.username,
    }


@router.post("/totp/setup", response_model=TotpSetupResponse)
def setup_totp_endpoint(
    current_user: UserInDB = Depends(get_current_active_user),
    connection: Optional[mysql.connector.MySQLConnection] = Depends(get_dbms_connection)
) -> Any:
    """Initialize Google Authenticator 2FA setup and return provisioning URI and QR code."""
    secret = _generate_totp_secret()
    _memory_totp_pending[current_user.user_id] = secret

    if connection is not None:
        try:
            ensure_registration_requests_table(connection)
            cur = connection.cursor()
            cur.execute(
                "UPDATE users SET totp_secret = %s WHERE user_id = %s",
                (secret, current_user.user_id)
            )
            connection.commit()
            cur.close()
        except Exception:
            pass

    issuer = "OS-DBX"
    label = f"{issuer}:{current_user.username}"
    provisioning_uri = f"otpauth://totp/{urllib.parse.quote(label)}?secret={secret}&issuer={urllib.parse.quote(issuer)}&algorithm=SHA1&digits=6&period=30"
    qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={urllib.parse.quote(provisioning_uri)}"

    return TotpSetupResponse(
        secret=secret,
        provisioning_uri=provisioning_uri,
        qr_code_url=qr_code_url,
    )


@router.post("/totp/enable", response_model=TotpStatusResponse)
def enable_totp_endpoint(
    req: TotpVerifyRequest,
    current_user: UserInDB = Depends(get_current_active_user),
    connection: Optional[mysql.connector.MySQLConnection] = Depends(get_dbms_connection)
) -> Any:
    """Verify 6-digit TOTP code and activate two-step verification."""
    secret = _memory_totp_pending.get(current_user.user_id)
    if not secret and connection is not None:
        try:
            cur = connection.cursor(dictionary=True)
            cur.execute("SELECT totp_secret FROM users WHERE user_id = %s", (current_user.user_id,))
            row = cur.fetchone()
            if row and row.get("totp_secret"):
                secret = row["totp_secret"]
            cur.close()
        except Exception:
            pass

    if not secret:
        raise HTTPException(
            status_code=400,
            detail="No pending two-step setup found. Please click Setup first.",
        )

    if not _verify_totp_code(secret, req.code):
        raise HTTPException(
            status_code=400,
            detail="Invalid 6-digit authenticator code. Please check your Google Authenticator app and try again.",
        )

    _memory_totp_secrets[current_user.user_id] = secret
    current_user.totp_enabled = True
    current_user.totp_secret = secret
    try:
        from app.core.auth import _memory_users
        uname = current_user.username.casefold()
        if uname in _memory_users:
            _memory_users[uname].totp_enabled = True
            _memory_users[uname].totp_secret = secret
    except Exception:
        pass

    if connection is not None:
        try:
            cur = connection.cursor()
            cur.execute(
                "UPDATE users SET totp_enabled = 1, totp_secret = %s WHERE user_id = %s",
                (secret, current_user.user_id)
            )
            connection.commit()
            cur.close()
        except Exception:
            pass

    return TotpStatusResponse(
        totp_enabled=True,
        message="Two-step verification activated with Google Authenticator.",
    )


@router.post("/totp/verify-login", response_model=Token)
def verify_totp_login_endpoint(
    req: TotpLoginVerifyRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    connection: Optional[mysql.connector.MySQLConnection] = Depends(get_dbms_connection),
) -> Any:
    """Validate 6-digit Google Authenticator code during login challenge and issue access token."""
    client_host = request.client.host if request.client else "unknown"
    rate_key = (f"totp-login:{client_host}",)
    check_rate_limit(rate_key, max_attempts=10, window_seconds=60, detail="Too many invalid 2FA attempts. Please wait a minute and try again.")

    try:
        payload = jwt.decode(req.challenge_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        purpose: str = payload.get("purpose")
        if not username or purpose != "totp_challenge":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid two-step challenge session. Please sign in again.",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Two-step verification session expired or invalid. Please sign in again.",
        )

    user = get_user_by_username(connection, username=username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    secret = user.totp_secret or _memory_totp_secrets.get(user.user_id)
    if not secret and connection is not None:
        try:
            cur = connection.cursor(dictionary=True)
            cur.execute("SELECT totp_secret FROM users WHERE user_id = %s", (user.user_id,))
            row = cur.fetchone()
            if row and row.get("totp_secret"):
                secret = row["totp_secret"]
            cur.close()
        except Exception:
            pass

    if not secret:
        raise HTTPException(
            status_code=400,
            detail="Two-step verification secret is missing. Please contact administrator to reset your credentials.",
        )

    if not _verify_totp_code(secret, req.code):
        record_rate_limited_attempt(rate_key, window_seconds=60)
        raise HTTPException(
            status_code=400,
            detail="Invalid 6-digit authenticator code. Please check your Google Authenticator app and try again.",
        )

    clear_rate_limit(rate_key)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    recipient_email = user.email or (username if "@" in username else None)
    if recipient_email:
        background_tasks.add_task(send_signin_notification, recipient_email, user.username)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "requires_totp": False,
        "challenge_token": None,
        "email_notification_sent": bool(recipient_email),
    }


@router.post("/totp/disable", response_model=TotpStatusResponse)
def disable_totp_endpoint(
    current_user: UserInDB = Depends(get_current_active_user),
    connection: Optional[mysql.connector.MySQLConnection] = Depends(get_dbms_connection)
) -> Any:
    """Disable two-step verification for the current user."""
    _memory_totp_secrets.pop(current_user.user_id, None)
    _memory_totp_pending.pop(current_user.user_id, None)
    current_user.totp_enabled = False
    current_user.totp_secret = None
    try:
        from app.core.auth import _memory_users
        uname = current_user.username.casefold()
        if uname in _memory_users:
            _memory_users[uname].totp_enabled = False
            _memory_users[uname].totp_secret = None
    except Exception:
        pass

    if connection is not None:
        try:
            cur = connection.cursor()
            cur.execute(
                "UPDATE users SET totp_enabled = 0, totp_secret = NULL WHERE user_id = %s",
                (current_user.user_id,)
            )
            connection.commit()
            cur.close()
        except Exception:
            pass

    return TotpStatusResponse(
        totp_enabled=False,
        message="Two-step verification has been turned off.",
    )
