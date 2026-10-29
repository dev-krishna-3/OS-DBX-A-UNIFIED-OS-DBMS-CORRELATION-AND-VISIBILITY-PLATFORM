import psutil

def get_mysql_connections():
    print("Scanning active connections to port 3306...")
    for conn in psutil.net_connections(kind='tcp'):
        if conn.raddr and len(conn.raddr) == 2 and conn.raddr.port == 3306:
            if conn.status == 'ESTABLISHED':
                print(f"PID {conn.pid} is connected to MySQL from local port {conn.laddr.port}")

if __name__ == "__main__":
    get_mysql_connections()
