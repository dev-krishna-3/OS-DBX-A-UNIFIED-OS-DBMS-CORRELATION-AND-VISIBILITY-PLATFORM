#!/usr/bin/env python3
"""
OS-DBX Environment and System Diagnostics Utility
=================================================
A non-destructive diagnostic tool for developers and teammates to verify:
1. Python runtime and platform compatibility
2. Required third-party dependencies (FastAPI, uvicorn, psutil, mysql-connector, etc.)
3. OS-DBX backend configuration (.env / environment variables)
4. MySQL connection and Performance Schema consumers (read-only verification)

This script NEVER modifies database tables, schemas, or existing files.
"""

import sys
import os
import platform
import argparse
import importlib.util
from pathlib import Path

# ANSI colors for friendly terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_status(tag: str, message: str, color: str = ""):
    print(f"  {color}[{tag}]{RESET} {message}")


def check_python_environment() -> bool:
    print(f"\n{BOLD}1. Checking Python Environment...{RESET}")
    version = sys.version_info
    v_str = f"{version.major}.{version.minor}.{version.micro}"
    print_status("INFO", f"Python version: {v_str} ({platform.python_implementation()})", CYAN)
    print_status("INFO", f"Operating System: {platform.system()} {platform.release()} ({platform.architecture()[0]})", CYAN)

    if version.major >= 3 and version.minor >= 10:
        print_status("PASS", f"Python version >= 3.10 is satisfied.", GREEN)
        return True
    else:
        print_status("WARN", f"Recommended Python version is 3.10+. Detected {v_str}.", YELLOW)
        return False


def is_package_available(pkg_name: str) -> bool:
    try:
        spec = importlib.util.find_spec(pkg_name)
        return spec is not None
    except (ModuleNotFoundError, ValueError, Exception):
        return False


def check_dependencies() -> dict:
    print(f"\n{BOLD}2. Checking Python Dependencies...{RESET}")
    required_packages = [
        ("fastapi", "FastAPI web framework"),
        ("uvicorn", "ASGI server"),
        ("pydantic", "Data validation"),
        ("psutil", "OS process and resource metrics collection"),
        ("mysql.connector", "MySQL database connector (mysql-connector-python)"),
        ("pytest", "Testing framework"),
    ]

    optional_packages = [
        ("watchdog", "Filesystem event monitoring (for OS monitor)"),
        ("requests", "HTTP client for testing / integration"),
        ("dotenv", "Environment variable loader (python-dotenv)"),
    ]

    results = {}

    print("  Required packages:")
    for pkg, desc in required_packages:
        if is_package_available(pkg):
            print_status("PASS", f"{pkg:<18} - {desc}", GREEN)
            results[pkg] = True
        else:
            print_status("FAIL", f"{pkg:<18} - {desc} (NOT INSTALLED)", RED)
            results[pkg] = False

    print("  Optional packages:")
    for pkg, desc in optional_packages:
        if is_package_available(pkg):
            print_status("PASS", f"{pkg:<18} - {desc}", GREEN)
            results[pkg] = True
        else:
            print_status("INFO", f"{pkg:<18} - {desc} (Optional)", CYAN)
            results[pkg] = False

    return results


def check_project_paths(base_dir: Path):
    print(f"\n{BOLD}3. Checking Project Structure & Configuration...{RESET}")
    expected_paths = [
        ("backend/app/main.py", "FastAPI entry point"),
        ("backend/readme_backend.md", "Backend documentation"),
        ("database/schema.sql", "Database schema definition"),
        ("database/migrations", "Database migrations folder"),
        ("os_monitor", "OS event monitoring module"),
    ]

    for rel_path, desc in expected_paths:
        target = base_dir / rel_path
        if target.exists():
            print_status("PASS", f"{rel_path:<28} - {desc}", GREEN)
        else:
            print_status("WARN", f"{rel_path:<28} - Missing file/dir", YELLOW)

    storage_mode = os.getenv("EVENT_STORAGE", "memory")
    print_status("INFO", f"EVENT_STORAGE mode: '{storage_mode}' (Options: 'memory', 'mysql')", CYAN)


def check_mysql_read_only(skip_db: bool = False):
    print(f"\n{BOLD}4. Checking MySQL & Performance Schema (Read-Only)...{RESET}")
    if skip_db:
        print_status("INFO", "Skipping MySQL connectivity check (--skip-db passed).", CYAN)
        return

    # Check if mysql.connector is installed
    if importlib.util.find_spec("mysql.connector") is None:
        print_status("WARN", "mysql-connector-python is not installed. Skipping MySQL check.", YELLOW)
        return

    import mysql.connector

    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "os_dbx")

    try:
        print_status("INFO", f"Attempting read-only connection to {user}@{host}:{port}...", CYAN)
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connection_timeout=3
        )
        if conn.is_connected():
            print_status("PASS", f"Successfully connected to MySQL database '{database}'.", GREEN)
            cursor = conn.cursor(dictionary=True)

            # Check Performance Schema consumer status (READ ONLY)
            cursor.execute(
                "SELECT NAME, ENABLED FROM performance_schema.setup_consumers "
                "WHERE NAME = 'events_statements_history_long';"
            )
            consumer_row = cursor.fetchone()
            if consumer_row:
                status = consumer_row.get("ENABLED")
                if status == "YES":
                    print_status("PASS", "Performance Schema consumer 'events_statements_history_long' is ENABLED.", GREEN)
                else:
                    print_status("WARN", "Performance Schema consumer 'events_statements_history_long' is DISABLED.", YELLOW)
                    print("         Run: UPDATE performance_schema.setup_consumers SET ENABLED = 'YES' WHERE NAME = 'events_statements_history_long';")
            else:
                print_status("WARN", "Could not query setup_consumers. Ensure Performance Schema is enabled in my.cnf/my.ini.", YELLOW)

            cursor.close()
            conn.close()
    except mysql.connector.Error as err:
        print_status("WARN", f"Could not connect to MySQL server: {err}", YELLOW)
        print("         Note: In-memory mode (EVENT_STORAGE=memory) can still be run without local MySQL.")
    except Exception as ex:
        print_status("WARN", f"Unexpected error during DB check: {ex}", YELLOW)


def main():
    parser = argparse.ArgumentParser(
        description="OS-DBX Environment and Diagnostics Tool",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--skip-db", action="store_true", help="Skip MySQL server connection check")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent

    print(f"{BOLD}{'=' * 65}{RESET}")
    print(f"{BOLD}  OS-DBX System & Environment Diagnostics Utility{RESET}")
    print(f"  Project Root: {project_root}")
    print(f"{BOLD}{'=' * 65}{RESET}")

    check_python_environment()
    check_dependencies()
    check_project_paths(project_root)
    check_mysql_read_only(skip_db=args.skip_db)

    print(f"\n{BOLD}{'=' * 65}{RESET}")
    print(f"  Diagnostics finished. For issues, check backend/readme_backend.md.")
    print(f"{BOLD}{'=' * 65}{RESET}\n")


if __name__ == "__main__":
    main()
