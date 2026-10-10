import psutil
import mysql.connector

def find_bridge():
    print("Step 1: Finding OS processes connected to MySQL (Port 3306)...")
    client_ports = {}
    for conn in psutil.net_connections(kind='tcp'):
        if conn.raddr and len(conn.raddr) == 2 and conn.raddr.port == 3306:
            if conn.status == 'ESTABLISHED':
                client_ports[conn.laddr.port] = conn.pid
                print(f"  -> Found PID {conn.pid} connected via local port {conn.laddr.port}")
                
    if not client_ports:
        print("  -> No active connections found from the OS side.")
        return

    print("\nStep 2: Matching client ports in MySQL PROCESSLIST...")
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
            host_str = row['HOST']
            if host_str and ':' in host_str:
                port_str = host_str.split(':')[-1]
                if port_str.isdigit():
                    port = int(port_str)
                    if port in client_ports:
                        pid = client_ports[port]
                        print(f"  -> SUCCESS! MySQL Connection ID {row['ID']} exactly maps to OS PID {pid}")
                        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_bridge()
