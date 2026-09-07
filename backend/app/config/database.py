"""Small MySQL connection factory used by database-backed features."""

import mysql.connector

from app.config.settings import settings


def get_connection():
    """Create one MySQL connection for a request."""
    return mysql.connector.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
    )
