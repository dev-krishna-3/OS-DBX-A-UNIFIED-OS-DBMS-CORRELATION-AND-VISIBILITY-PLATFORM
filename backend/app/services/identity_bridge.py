"""Real-Time OS-DBMS Identity Bridge Service.

Maps live OS processes to MySQL connections by matching OS network sockets 
to MySQL information_schema.processlist client ports.
"""
import psutil
import mysql.connector

class IdentityBridgeService:
    def __init__(self, host="localhost", user="root", password="", database="information_schema"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database

    def _get_mysql_connection(self):
        return mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database
        )

    def get_os_client_ports(self) -> dict[int, int]:
        """Returns a dict mapping local client ports to their owning OS PID."""
        client_ports = {}
        try:
            for conn in psutil.net_connections(kind='tcp'):
                # Check if it's connected to MySQL port (3306)
                if conn.raddr and len(conn.raddr) == 2 and conn.raddr.port == 3306:
                    if conn.status == 'ESTABLISHED':
                        client_ports[conn.laddr.port] = conn.pid
        except psutil.AccessDenied:
            # We might not have permission to see all processes, but we get what we can
            pass
        return client_ports

    def build_pid_to_connection_map(self) -> dict[int, int]:
        """Builds a map of OS PID -> MySQL PROCESSLIST_ID."""
        client_ports = self.get_os_client_ports()
        if not client_ports:
            return {}

        pid_map = {}
        conn = None
        try:
            conn = self._get_mysql_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT ID, HOST FROM processlist WHERE HOST IS NOT NULL")
            rows = cursor.fetchall()
            
            for row in rows:
                host_str = row['HOST']
                if host_str and ':' in host_str:
                    port_str = host_str.split(':')[-1]
                    if port_str.isdigit():
                        port = int(port_str)
                        if port in client_ports:
                            pid = client_ports[port]
                            processlist_id = row['ID']
                            pid_map[pid] = processlist_id
        except Exception as e:
            print(f"IdentityBridge error: {e}")
        finally:
            if conn:
                conn.close()
                
        return pid_map
        
    def get_pid_for_connection(self, processlist_id: int) -> int | None:
        """Reverse lookup: Find which OS PID owns a given MySQL connection ID."""
        pid_map = self.build_pid_to_connection_map()
        for pid, conn_id in pid_map.items():
            if conn_id == processlist_id:
                return pid
        return None
