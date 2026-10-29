import mysql.connector

def check_processlist():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="krishna356",
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
