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
    for stmt, col_name in [
        ("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NULL;", "password_hash"),
        ("ALTER TABLE users ADD COLUMN email VARCHAR(255) NULL UNIQUE;", "email"),
    ]:
        try:
            cursor.execute(stmt)
            conn.commit()
            print(f"Successfully added {col_name} column to users table.")
        except mysql.connector.Error as err:
            if err.errno == 1060:  # Duplicate column name
                print(f"{col_name} column already exists.")
            else:
                print(f"Error adding {col_name}: {err}")
except mysql.connector.Error as err:
    print(f"Connection Error: {err}")
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
