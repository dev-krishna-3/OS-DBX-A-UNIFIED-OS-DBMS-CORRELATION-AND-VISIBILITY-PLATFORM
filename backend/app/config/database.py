"""Small MySQL connection factory used by database-backed features."""

import mysql.connector
from mysql.connector import pooling

from app.config.settings import settings

# Create a module-level connection pool
try:
    _connection_pool = pooling.MySQLConnectionPool(
        pool_name="osdbx_pool",
        pool_size=10,
        pool_reset_session=True,
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
    )
except mysql.connector.Error as err:
    print(f"Error initializing connection pool: {err}")
    _connection_pool = None

def get_connection():
    """Get a MySQL connection from the pool."""
    if _connection_pool:
        return _connection_pool.get_connection()
    # Fallback if pool failed to initialize
    return mysql.connector.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
    )
