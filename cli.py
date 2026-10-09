import os
import sys
import time
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.progress import Progress
from rich import print as rprint

API_BASE_URL = "http://127.0.0.1:8000"
console = Console()
session = requests.Session()
token = None

def get_headers():
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def show_header():
    console.clear()
    console.print(Panel.fit("[bold cyan]OS-DBX Unified CLI Dashboard[/bold cyan]", border_style="cyan"))
    console.print("The bridge between OS metrics and DBMS observations.\n")

def check_health():
    try:
        r = session.get(f"{API_BASE_URL}/health/details", timeout=3)
        if r.status_code == 200:
            console.print("[bold green]✔ Backend is Online[/bold green]")
            return True
        else:
            console.print(f"[bold red]✖ Backend returned status code {r.status_code}[/bold red]")
            return False
    except requests.ConnectionError:
        console.print("[bold red]✖ Cannot connect to backend (http://127.0.0.1:8000). Is it running?[/bold red]")
        return False

def login_menu():
    global token
    while True:
        show_header()
        if not check_health():
            sys.exit(1)
            
        console.print("\n[1] Login")
        console.print("[2] Register New User")
        console.print("[3] Exit")
        
        choice = Prompt.ask("Choose an option", choices=["1", "2", "3"])
        
        if choice == "3":
            sys.exit(0)
        elif choice == "1":
            username = Prompt.ask("Username")
            password = Prompt.ask("Password", password=True)
            try:
                r = session.post(f"{API_BASE_URL}/api/auth/token", data={"username": username, "password": password})
                if r.status_code == 200:
                    token = r.json()["access_token"]
                    console.print("[bold green]Login successful![/bold green]")
                    time.sleep(1)
                    return
                else:
                    console.print("[bold red]Invalid credentials. Try again.[/bold red]")
                    time.sleep(2)
            except Exception as e:
                console.print(f"[bold red]Error: {e}[/bold red]")
                time.sleep(2)
        elif choice == "2":
            username = Prompt.ask("New Username")
            uid_linux = IntPrompt.ask("Linux UID (e.g. 1000)")
            password = Prompt.ask("New Password", password=True)
            try:
                r = session.post(f"{API_BASE_URL}/api/auth/register", json={
                    "username": username,
                    "uid_linux": uid_linux,
                    "password": password
                })
                if r.status_code == 201:
                    console.print("[bold green]Registration successful! You can now login.[/bold green]")
                else:
                    console.print(f"[bold red]Registration failed: {r.json()}[/bold red]")
                time.sleep(2)
            except Exception as e:
                console.print(f"[bold red]Error: {e}[/bold red]")
                time.sleep(2)

def fetch_dbms_observations():
    with console.status("[bold green]Fetching DBMS Observations..."):
        r = session.get(f"{API_BASE_URL}/api/dbms-events/observations?limit=10", headers=get_headers())
        if r.status_code == 200:
            obs = r.json()
            table = Table(title="Recent DBMS Queries (Live)")
            table.add_column("ID", justify="right", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Query", style="green")
            table.add_column("Time (ms)", justify="right")
            table.add_column("Status")
            
            for o in obs:
                qtext = (o['query_text'][:50] + '..') if len(o['query_text']) > 50 else o['query_text']
                table.add_row(str(o['observation_id']), o['query_type'], qtext, str(o['execution_time_ms']), o['status'])
            console.print(table)
        else:
            console.print(f"[bold red]Failed to fetch: {r.text}[/bold red]")

def fetch_deadlocks():
    with console.status("[bold green]Fetching Deadlock Incidents..."):
        r = session.get(f"{API_BASE_URL}/api/deadlocks/incidents?limit=5", headers=get_headers())
        if r.status_code == 200:
            incidents = r.json()
            if not incidents:
                console.print("[yellow]No deadlocks recorded.[/yellow]")
                return
                
            table = Table(title="Recent Deadlock Incidents")
            table.add_column("Incident ID", justify="right", style="cyan")
            table.add_column("Trace ID", style="magenta")
            table.add_column("Type", style="red")
            table.add_column("Detected At")
            table.add_column("Resolved")
            
            for inc in incidents:
                table.add_row(
                    str(inc['incident_id']), 
                    str(inc.get('trace_id', 'N/A')), 
                    inc['incident_type'], 
                    inc['detected_at'], 
                    str(inc['resolved'])
                )
            console.print(table)
        else:
            console.print(f"[bold red]Failed to fetch: {r.text}[/bold red]")

def run_benchmark():
    console.print("\n[bold yellow]Triggering Live DBMS Benchmark...[/bold yellow]")
    scenario = Prompt.ask("Scenario", choices=["DBMS_ONLY", "LOCK_CONTENTION", "DEADLOCK"], default="DBMS_ONLY")
    ops = IntPrompt.ask("Number of operations", default=50)
    
    with console.status("[bold magenta]Running Benchmark..."):
        r = session.post(f"{API_BASE_URL}/api/benchmark/run", json={
            "scenario": scenario,
            "operations": ops,
            "concurrency": 1
        }, headers=get_headers())
        
        if r.status_code == 200:
            res = r.json()
            metrics = res.get("metrics", {})
            console.print("\n[bold green]Benchmark Completed Successfully![/bold green]")
            table = Table(title="Benchmark Results")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="magenta")
            table.add_row("Scenario", res.get("scenario"))
            table.add_row("Total Time (ms)", str(metrics.get("workload_duration_ms")))
            table.add_row("Ops Executed", str(metrics.get("operations_executed")))
            table.add_row("Failed Ops", str(metrics.get("failed_operations")))
            table.add_row("OS Dropped Events", str(metrics.get("dropped_events")))
            console.print(table)
        else:
            console.print(f"[bold red]Benchmark Failed: {r.text}[/bold red]")

def main_menu():
    while True:
        show_header()
        
        # Get User details
        try:
            r = session.get(f"{API_BASE_URL}/api/auth/me", headers=get_headers())
            if r.status_code == 200:
                user = r.json()
                console.print(f"Logged in as: [bold yellow]{user['username']}[/bold yellow] (UID: {user['uid_linux']})\n")
        except:
            pass

        console.print("[1] View Live DBMS Observations (Query Fetcher)")
        console.print("[2] View Recent Deadlocks & Incidents")
        console.print("[3] Run Live Benchmark Simulator")
        console.print("[4] Collect OS-DB Events (Ping Performance Schema)")
        console.print("[5] Logout / Exit")
        
        choice = Prompt.ask("Choose an action", choices=["1", "2", "3", "4", "5"])
        
        console.clear()
        if choice == "5":
            console.print("[bold yellow]Logging out...[/bold yellow]")
            sys.exit(0)
            
        elif choice == "1":
            fetch_dbms_observations()
            Prompt.ask("\nPress Enter to return to menu")
            
        elif choice == "2":
            fetch_deadlocks()
            Prompt.ask("\nPress Enter to return to menu")
            
        elif choice == "3":
            run_benchmark()
            Prompt.ask("\nPress Enter to return to menu")
            
        elif choice == "4":
            with console.status("[bold blue]Collecting events from MySQL Performance Schema..."):
                r = session.post(f"{API_BASE_URL}/api/dbms-events/collect", json={"limit": 25, "persist": True}, headers=get_headers())
                if r.status_code == 200:
                    data = r.json()
                    console.print(f"\n[bold green]Collection Success![/bold green]")
                    console.print(f"Collected: {data.get('collected')} | Persisted: {data.get('persisted')}")
                else:
                    console.print(f"[bold red]Collection Failed: {r.text}[/bold red]")
            Prompt.ask("\nPress Enter to return to menu")

if __name__ == "__main__":
    try:
        login_menu()
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[bold red]Exiting...[/bold red]")
        sys.exit(0)
