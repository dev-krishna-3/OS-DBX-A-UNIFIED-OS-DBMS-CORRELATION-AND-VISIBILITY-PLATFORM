"""Small MySQL connection factory used by database-backed features."""

import threading
import time
import mysql.connector
from mysql.connector import pooling

from app.config.settings import settings

_conn_lock = threading.Lock()
_last_failure_time = 0.0
_COOLDOWN_SECONDS = 20.0
_connect_host = "127.0.0.1" if settings.mysql_host.strip().lower() in {"localhost", ""} else settings.mysql_host

# Create a module-level connection pool
try:
    _connection_pool = pooling.MySQLConnectionPool(
        pool_name="osdbx_pool",
        pool_size=25,
        pool_reset_session=True,
        host=_connect_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        connection_timeout=1,
    )
except Exception as err:
    print(f"Error initializing connection pool: {err}")
    _connection_pool = None
    _last_failure_time = time.time()


def get_connection():
    """Get a MySQL connection from the pool, with fast-fail circuit breaker when offline."""
    global _connection_pool, _last_failure_time

    if _connection_pool:
        try:
            return _connection_pool.get_connection()
        except Exception:
            _connection_pool = None

    now = time.time()
    with _conn_lock:
        if now - _last_failure_time < _COOLDOWN_SECONDS:
            raise mysql.connector.errors.DatabaseError(
                2003,
                f"Can't connect to MySQL server on '{_connect_host}:{settings.mysql_port}' (offline cooldown active)",
            )

    try:
        conn = mysql.connector.connect(
            host=_connect_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            connection_timeout=1,
        )
        with _conn_lock:
            _last_failure_time = 0.0
        return conn
    except Exception as err:
        with _conn_lock:
            _last_failure_time = time.time()
        raise err
