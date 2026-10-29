import mysql.connector
from app.config.settings import settings

try:
    conn = mysql.connector.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database
    )
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NULL;")
    conn.commit()
    print("Successfully added password_hash column to users table.")
except mysql.connector.Error as err:
    if err.errno == 1060: # Duplicate column name
        print("password_hash column already exists.")
    else:
        print(f"Error: {err}")
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
