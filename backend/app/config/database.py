"""Small MySQL connection factory used by database-backed features."""

from pathlib import Path
import tempfile
import threading
import time
import mysql.connector
from mysql.connector import pooling

from app.config.settings import settings

_conn_lock = threading.Lock()
_last_failure_time = 0.0
_COOLDOWN_SECONDS = 3.0
_connect_host = "127.0.0.1" if settings.mysql_host.strip().lower() in {"localhost", ""} else settings.mysql_host
_cached_ssl_ca_path: str | None = None


def _resolve_ssl_ca_path() -> str | None:
    """Return a filesystem CA bundle path if configured via file path or inline PEM."""
    global _cached_ssl_ca_path
    pem_text = settings.mysql_ssl_ca_pem.strip()
    if pem_text:
        if _cached_ssl_ca_path and Path(_cached_ssl_ca_path).is_file():
            return _cached_ssl_ca_path
        normalized_pem = pem_text.replace("\\n", "\n")
        if not normalized_pem.endswith("\n"):
            normalized_pem += "\n"
        tmp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix="-mysql-ca.pem", delete=False)
        try:
            tmp.write(normalized_pem)
        finally:
            tmp.close()
        _cached_ssl_ca_path = tmp.name
        return _cached_ssl_ca_path

    ca_path = settings.mysql_ssl_ca.strip()
    if ca_path:
        return ca_path

    if settings.mysql_ssl_required:
        linux_system_ca = Path("/etc/ssl/certs/ca-certificates.crt")
        if linux_system_ca.is_file():
            return str(linux_system_ca)
    return None


def get_mysql_connect_kwargs(database: str | None = None) -> dict:
    """Build keyword arguments for mysql.connector including timeout and optional TLS."""
    kwargs: dict = {
        "host": _connect_host,
        "port": settings.mysql_port,
        "user": settings.mysql_user,
        "password": settings.mysql_password,
        "database": database or settings.mysql_database,
        "connection_timeout": max(1, int(settings.mysql_connect_timeout)),
    }
    ssl_ca = _resolve_ssl_ca_path()
    if ssl_ca:
        kwargs["ssl_ca"] = ssl_ca
        kwargs["ssl_verify_cert"] = True
        kwargs["ssl_disabled"] = False
    elif settings.mysql_ssl_required:
        kwargs["ssl_disabled"] = False
    return kwargs


# Create a module-level connection pool (sized safely for cloud/trial tiers)
try:
    _pool_size = max(1, min(int(getattr(settings, "mysql_pool_size", 4)), 5))
    _connection_pool = pooling.MySQLConnectionPool(
        pool_name="osdbx_pool",
        pool_size=_pool_size,
        pool_reset_session=True,
        **get_mysql_connect_kwargs(),
    )
except Exception as err:
    print(f"Notice: MySQL connection pool not initialized ({err}); using on-demand connections.")
    _connection_pool = None


def get_connection():
    """Get a MySQL connection from the pool, with fallback to on-demand and short circuit breaker."""
    global _connection_pool, _last_failure_time

    if _connection_pool:
        try:
            return _connection_pool.get_connection()
        except Exception:
            pass

    now = time.time()
    with _conn_lock:
        if _last_failure_time > 0 and (now - _last_failure_time) < _COOLDOWN_SECONDS:
            raise mysql.connector.errors.DatabaseError(
                2003,
                f"Can't connect to MySQL server on '{_connect_host}:{settings.mysql_port}' (offline cooldown active)",
            )

    try:
        conn = mysql.connector.connect(**get_mysql_connect_kwargs())
        with _conn_lock:
            _last_failure_time = 0.0
        return conn
    except Exception as err:
        with _conn_lock:
            _last_failure_time = time.time()
        raise err
