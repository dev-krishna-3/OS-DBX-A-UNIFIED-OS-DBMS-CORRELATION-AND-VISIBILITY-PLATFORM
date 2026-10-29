"""Real-Time OS-DBMS Identity Bridge Service.

Maps live OS processes to MySQL connections by matching OS network sockets 
to MySQL information_schema.processlist client ports.
"""
import psutil
import mysql.connector

class IdentityBridgeService:
    def __init__(self, host="localhost", user="root", password="", database="information_schema", port=3306):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.has_access_denied = False

    def _get_mysql_connection(self):
        return mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database
        )

    def is_admin_mode(self) -> bool:
        """Check if process has Administrator privileges on Windows / root on Linux."""
        import os
        if os.name == 'nt':
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except Exception:
                return False
        return os.geteuid() == 0 if hasattr(os, 'geteuid') else False

    def _get_ports_from_netstat(self, mysql_port: int = 3306) -> dict[int, int]:
        """Extract client port -> PID mappings on Windows using netstat without requiring admin elevation."""
        import subprocess
        import re
        client_ports = {}
        try:
            output = subprocess.check_output(
                ["netstat", "-ano", "-p", "tcp"],
                universal_newlines=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=5
            )
            pattern = re.compile(
                rf'^\s*TCP\s+\S+:(\d+)\s+\S+:{mysql_port}\s+ESTABLISHED\s+(\d+)',
                re.IGNORECASE | re.MULTILINE
            )
            for port_str, pid_str in pattern.findall(output):
                client_ports[int(port_str)] = int(pid_str)
        except Exception:
            pass
        return client_ports

    def get_os_client_ports(self) -> dict[int, int]:
        """Returns a dict mapping local client ports to their owning OS PID."""
        import os
        client_ports = {}
        self.has_access_denied = False

        # On Windows, netstat -ano -p tcp works in unprivileged prompts and
        # captures ALL sockets including SYSTEM and other users without AccessDenied.
        if os.name == 'nt':
            netstat_ports = self._get_ports_from_netstat(mysql_port=self.port)
            if netstat_ports:
                client_ports.update(netstat_ports)

        try:
            for conn in psutil.net_connections(kind='tcp'):
                # Check if it's connected to MySQL port
                if conn.raddr and len(conn.raddr) == 2 and conn.raddr.port == self.port:
                    if conn.status == 'ESTABLISHED' and conn.pid:
                        client_ports[conn.laddr.port] = conn.pid
        except psutil.AccessDenied:
            # Only flag access denied if unprivileged netstat also failed to get ports
            if not client_ports:
                self.has_access_denied = True
        except Exception:
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
