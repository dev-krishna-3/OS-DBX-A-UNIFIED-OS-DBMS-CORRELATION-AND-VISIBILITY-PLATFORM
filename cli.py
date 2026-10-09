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

# ---------------------------------------------------------------------------
# OS Simulation Lab Functions
# ---------------------------------------------------------------------------

def run_cpu_scheduling_lab():
    console.print("\n[bold cyan]--- CPU Scheduling Simulation Lab ---[/bold cyan]")
    algo = Prompt.ask("Select Algorithm", choices=["FCFS", "SJF", "SRTF", "RR", "PRIORITY"], default="FCFS")
    quantum = 2
    if algo == "RR":
        quantum = IntPrompt.ask("Enter Time Quantum (q)", default=2)

    sample_procs = [
        {"pid": 1, "arrival_time": 0, "burst_time": 6, "priority": 2},
        {"pid": 2, "arrival_time": 2, "burst_time": 4, "priority": 1},
        {"pid": 3, "arrival_time": 4, "burst_time": 2, "priority": 3},
    ]

    with console.status(f"[bold green]Simulating {algo} CPU Scheduling..."):
        r = session.post(f"{API_BASE_URL}/api/simulations/scheduling", json={
            "algorithm": algo,
            "processes": sample_procs,
            "quantum": quantum
        }, headers=get_headers())

        if r.status_code == 200:
            res = r.json()
            console.print(f"\n[bold green]=== Algorithm: {res['algorithm']} ===[/bold green]")
            
            # Table of Process Metrics
            table = Table(title="Process Performance Metrics")
            table.add_column("PID", justify="right", style="cyan")
            table.add_column("Arrival", justify="right")
            table.add_column("Burst", justify="right")
            table.add_column("Priority", justify="right")
            table.add_column("Start", justify="right")
            table.add_column("Finish", justify="right")
            table.add_column("Waiting Time", justify="right", style="yellow")
            table.add_column("Turnaround Time", justify="right", style="magenta")

            for p in res["processes"]:
                table.add_row(
                    str(p["pid"]), str(p["arrival_time"]), str(p["burst_time"]),
                    str(p["priority"]), str(p["start_time"]), str(p["finish_time"]),
                    str(p["waiting_time"]), str(p["turnaround_time"])
                )
            console.print(table)

            # Gantt Chart Display
            gantt_str = " | ".join([f"P{item['pid']} ({item['start']}-{item['end']})" for item in res["gantt_chart"]])
            console.print(Panel(f"[bold yellow]Gantt Chart:[/bold yellow] [ {gantt_str} ]", border_style="yellow"))

            # Summary Metrics
            console.print(f"[bold white]Avg Waiting Time:[/bold white] [bold green]{res['avg_waiting_time']}[/bold green]")
            console.print(f"[bold white]Avg Turnaround Time:[/bold white] [bold green]{res['avg_turnaround_time']}[/bold green]")
            console.print(f"[bold white]CPU Utilization:[/bold white] [bold green]{res['cpu_utilization']}%[/bold green]")
        else:
            console.print(f"[bold red]Scheduling Simulation Failed: {r.text}[/bold red]")


def run_memory_lab():
    console.print("\n[bold cyan]--- Page Replacement Memory Lab ---[/bold cyan]")
    algo = Prompt.ask("Select Algorithm", choices=["FIFO", "LRU", "OPTIMAL", "ALL"], default="ALL")
    frames = IntPrompt.ask("Number of Frames", default=3)
    ref_input = Prompt.ask("Reference String (comma-separated)", default="1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5")
    
    try:
        ref_string = [int(x.strip()) for x in ref_input.split(",") if x.strip()]
    except ValueError:
        console.print("[bold red]Invalid reference string format.[/bold red]")
        return

    with console.status(f"[bold green]Running Memory Simulation ({algo})..."):
        r = session.post(f"{API_BASE_URL}/api/simulations/memory", json={
            "algorithm": algo,
            "reference_string": ref_string,
            "num_frames": frames
        }, headers=get_headers())

        if r.status_code == 200:
            res = r.json()
            if algo == "ALL":
                comp = res["comparison"]
                table = Table(title="Algorithm Comparison (Page Fault Analysis)")
                table.add_column("Algorithm", style="cyan")
                table.add_column("Page Faults", justify="right", style="red")
                table.add_column("Fault Rate", justify="right", style="yellow")
                
                for alg_name, data in comp.items():
                    table.add_row(alg_name, str(data["faults"]), f"{data['fault_rate'] * 100:.1f}%")
                console.print(table)
            else:
                console.print(f"\n[bold green]=== {res['algorithm']} Simulation Results ===[/bold green]")
                console.print(f"Frames: [bold cyan]{res['num_frames']}[/bold cyan] | Reference Length: [bold cyan]{len(res['reference_string'])}[/bold cyan]")
                console.print(f"Page Faults: [bold red]{res['page_faults']}[/bold red] | Page Hits: [bold green]{res['page_hits']}[/bold green]")
                console.print(f"Fault Rate: [bold yellow]{res['fault_rate'] * 100:.1f}%[/bold yellow] | Hit Rate: [bold green]{res['hit_rate'] * 100:.1f}%[/bold green]")
        else:
            console.print(f"[bold red]Memory Simulation Failed: {r.text}[/bold red]")


def run_deadlock_lab():
    console.print("\n[bold cyan]--- Deadlock & Banker's Algorithm Lab ---[/bold cyan]")
    mode = Prompt.ask("Choose Simulation", choices=["BANKERS", "RAG"], default="BANKERS")

    if mode == "BANKERS":
        payload = {
            "allocation": [[0,1,0],[2,0,0],[3,0,2],[2,1,1],[0,0,2]],
            "max_need":   [[7,5,3],[3,2,2],[9,0,2],[2,2,2],[4,3,3]],
            "available":  [3, 3, 2]
        }
        with console.status("[bold green]Executing Banker's Safety Algorithm..."):
            r = session.post(f"{API_BASE_URL}/api/simulations/deadlock/bankers", json=payload, headers=get_headers())
            if r.status_code == 200:
                res = r.json()
                if res["is_safe"]:
                    console.print(Panel(
                        f"[bold green]✔ SAFE STATE DETECTED[/bold green]\n\n"
                        f"Safe Sequence: [bold yellow]{res['safe_sequence']}[/bold yellow]\n"
                        f"Reason: {res['reason']}",
                        border_style="green"
                    ))
                else:
                    console.print(Panel(
                        f"[bold red]✖ UNSAFE STATE DETECTED[/bold red]\n\n"
                        f"Reason: {res['reason']}",
                        border_style="red"
                    ))
            else:
                console.print(f"[bold red]Banker's Algorithm Failed: {r.text}[/bold red]")

    elif mode == "RAG":
        payload = {
            "processes": [0, 1],
            "resources": [0, 1],
            "allocation": {"0": [0], "1": [1]},
            "request":    {"0": [1], "1": [0]}
        }
        with console.status("[bold green]Running Resource Allocation Graph (RAG) Analysis..."):
            r = session.post(f"{API_BASE_URL}/api/simulations/deadlock/rag", json=payload, headers=get_headers())
            if r.status_code == 200:
                res = r.json()
                if res["deadlock_detected"]:
                    console.print(Panel(
                        f"[bold red]✖ DEADLOCK DETECTED IN RAG[/bold red]\n\n"
                        f"Deadlocked PIDs: [bold yellow]{res['deadlocked_processes']}[/bold yellow]\n"
                        f"Cycle Path: [bold magenta]{res['cycle']}[/bold magenta]\n"
                        f"Reason: {res['reason']}",
                        border_style="red"
                    ))
                else:
                    console.print(Panel(
                        f"[bold green]✔ NO DEADLOCK DETECTED[/bold green]\n\n"
                        f"Reason: {res['reason']}",
                        border_style="green"
                    ))
            else:
                console.print(f"[bold red]RAG Simulation Failed: {r.text}[/bold red]")


def os_simulation_menu():
    while True:
        console.clear()
        console.print(Panel.fit("[bold magenta]OS Simulation & Work Analysis Lab[/bold magenta]", border_style="magenta"))
        console.print("[1] CPU Scheduling Simulator (FCFS, SJF, SRTF, Round Robin, Priority)")
        console.print("[2] Memory Page Replacement Lab (FIFO, LRU, Optimal)")
        console.print("[3] Deadlock Analysis (Banker's Algorithm & Resource Allocation Graph)")
        console.print("[4] View OS Live Stream Collector Metrics & Health")
        console.print("[5] Back to Main Menu")

        choice = Prompt.ask("Choose an OS Simulation option", choices=["1", "2", "3", "4", "5"])
        if choice == "5":
            break
        elif choice == "1":
            run_cpu_scheduling_lab()
            Prompt.ask("\nPress Enter to return to OS menu")
        elif choice == "2":
            run_memory_lab()
            Prompt.ask("\nPress Enter to return to OS menu")
        elif choice == "3":
            run_deadlock_lab()
            Prompt.ask("\nPress Enter to return to OS menu")
        elif choice == "4":
            with console.status("[bold blue]Fetching OS Stream Metrics..."):
                r = session.get(f"{API_BASE_URL}/api/os-events/metrics", headers=get_headers())
                if r.status_code == 200:
                    data = r.json()
                    console.print("\n[bold green]OS Live Collector Status:[/bold green]")
                    for k, v in data.items():
                        console.print(f"  [bold cyan]{k}:[/bold cyan] {v}")
                else:
                    console.print(f"[bold red]Failed to fetch OS metrics: {r.text}[/bold red]")
            Prompt.ask("\nPress Enter to return to OS menu")


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
        console.print("[5] OS Simulation & Work Analysis Lab (Scheduling, Memory, Deadlocks)")
        console.print("[6] Logout / Exit")
        
        choice = Prompt.ask("Choose an action", choices=["1", "2", "3", "4", "5", "6"])
        
        console.clear()
        if choice == "6":
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

        elif choice == "5":
            os_simulation_menu()

if __name__ == "__main__":
    try:
        login_menu()
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[bold red]Exiting...[/bold red]")
        sys.exit(0)
