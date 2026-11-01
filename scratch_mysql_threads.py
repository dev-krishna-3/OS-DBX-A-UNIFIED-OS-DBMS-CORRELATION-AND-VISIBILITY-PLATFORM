import os
import mysql.connector

def check_processlist():
    try:
        password = os.environ.get("MYSQL_PASSWORD")
        if not password:
            raise RuntimeError("Set MYSQL_PASSWORD before running this diagnostic.")
        conn = mysql.connector.connect(
            host=os.environ.get("MYSQL_HOST", "localhost"),
            user=os.environ.get("MYSQL_USER", "osdbx_app"),
            password=password,
            database="information_schema"
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT ID, USER, HOST FROM processlist")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_processlist()
