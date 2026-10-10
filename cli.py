import os
import sys

# Ensure backend directory is importable
_backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import time
import datetime
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

def log_cli_action(action: str, details: str = ""):
    if token:
        try:
            session.post(
                f"{API_BASE_URL}/api/audit/",
                json={"action": action, "details": details},
                headers=get_headers()
            )
        except Exception:
            pass

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
# Real-Time Cross-Layer OS-DBMS Correlation Engine Functions
# ---------------------------------------------------------------------------

def run_cross_layer_correlation():
    console.print("\n[bold cyan]--- Real-Time Cross-Layer OS-DBMS Correlation Engine ---[/bold cyan]")
    pid = IntPrompt.ask("Enter OS PID", default=4211)
    tx_id = IntPrompt.ask("Enter DBMS Transaction ID", default=12)
    query_id = IntPrompt.ask("Enter Query ID", default=25)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    events = [
        {
            "os_event_id": 2001,
            "pid": pid,
            "transaction_id": tx_id,
            "query_id": query_id,
            "timestamp": now_iso,
            "event_type": "process_created",
            "source": "os_monitor_adapter"
        },
        {
            "os_event_id": 2002,
            "pid": pid,
            "transaction_id": tx_id,
            "query_id": query_id,
            "timestamp": now_iso,
            "event_type": "transaction_started",
            "source": "dbms_transaction_tracker"
        },
        {
            "os_event_id": 2003,
            "pid": pid,
            "transaction_id": tx_id,
            "query_id": query_id,
            "timestamp": now_iso,
            "event_type": "query_executed",
            "source": "dbms_performance_schema"
        }
    ]

    with console.status("[bold green]Executing Cross-Layer Event Correlation..."):
        r = session.post(f"{API_BASE_URL}/api/correlations", json={"events": events}, headers=get_headers())
        if r.status_code == 200:
            res = r.json()
            classification = res.get("classification", "NONE")
            trace = res.get("trace") or {}
            
            console.print(Panel(
                f"[bold green]✔ CORRELATION RESULT[/bold green]\n\n"
                f"Classification: [bold yellow]{classification}[/bold yellow]\n"
                f"Is Correlated: [bold green]{res.get('is_correlated')}[/bold green]\n"
                f"Summary: {trace.get('summary', 'N/A')}\n"
                f"Completeness Score: [bold cyan]{res.get('os_evidence_completeness', 'N/A')}[/bold cyan]",
                border_style="green" if res.get('is_correlated') else "red"
            ))

            corrs = res.get("correlations", [])
            if corrs:
                table = Table(title="Causal Sequence & Cross-Layer Map")
                table.add_column("Seq #", justify="right", style="cyan")
                table.add_column("OS Event ID", justify="right", style="magenta")
                table.add_column("Query ID", justify="right", style="green")
                table.add_column("Method", style="yellow")
                for c in corrs:
                    table.add_row(str(c["sequence_order"]), str(c["os_event_id"]), str(c["query_id"]), c["correlation_method"])
                console.print(table)
        else:
            console.print(f"[bold red]Correlation Failed: {r.text}[/bold red]")


def run_auto_correlation():
    console.print("\n[bold cyan]--- DBMS-OS Auto-Correlation Engine ---[/bold cyan]")
    
    # First, fetch recent observations so the user sees valid IDs
    default_id = 1
    with console.status("[bold blue]Fetching available DBMS observations..."):
        r_obs = session.get(f"{API_BASE_URL}/api/dbms-events/observations?limit=5", headers=get_headers())
    
    if r_obs.status_code == 200:
        obs_list = r_obs.json()
        if obs_list:
            table = Table(title="Recent Available DBMS Observations")
            table.add_column("Observation ID", style="cyan", justify="right")
            table.add_column("Type", style="magenta")
            table.add_column("Query Preview", style="green")
            table.add_column("Time (ms)", style="yellow", justify="right")
            for o in obs_list:
                q = o.get("query_text", "")
                q_short = (q[:45] + "..") if len(q) > 45 else q
                table.add_row(str(o["observation_id"]), o.get("query_type", "N/A"), q_short, str(o.get("execution_time_ms", 0)))
            console.print(table)
            default_id = obs_list[0]["observation_id"]
        else:
            console.print("[yellow]No DBMS observations found in the database. Please run option [6] from the main menu to collect some events first.[/yellow]")
    
    obs_id = IntPrompt.ask("Enter DBMS Observation ID to auto-correlate", default=default_id)
    window_ms = IntPrompt.ask("Time Window (ms)", default=5000)

    with console.status(f"[bold green]Auto-correlating DBMS Observation #{obs_id}..."):
        r = session.post(f"{API_BASE_URL}/api/correlations/auto", json={
            "observation_id": obs_id,
            "window_ms": window_ms,
            "persist": True
        }, headers=get_headers())
        if r.status_code == 200:
            res = r.json()
            console.print(Panel(
                f"[bold green]✔ AUTO-CORRELATION COMPLETE[/bold green]\n\n"
                f"Observation ID: [bold cyan]{res.get('observation_id')}[/bold cyan]\n"
                f"Matched Query ID: [bold yellow]{res.get('matched_query_id', 'None')}[/bold yellow]\n"
                f"Matched OS Events: [bold magenta]{res.get('matched_os_event_ids', [])}[/bold magenta]\n"
                f"Status: {res.get('reason', 'Success')}",
                border_style="green" if res.get('matched_query_id') else "yellow"
            ))
        else:
            console.print(f"[bold red]Auto-Correlation Failed: {r.text}[/bold red]")


def run_blast_radius_analysis():
    console.print("\n[bold cyan]--- Incident Blast Radius & Causality Analysis ---[/bold cyan]")
    incident_id = IntPrompt.ask("Enter Incident ID", default=1)

    with console.status(f"[bold green]Computing Blast Radius for Incident #{incident_id}..."):
        r = session.get(f"{API_BASE_URL}/api/v1/incidents/{incident_id}/blast-radius", headers=get_headers())
        if r.status_code == 200:
            res = r.json()
            console.print(f"\n[bold green]Incident #{res['incident_id']} ({res['incident_type']}) Impact Analysis[/bold green]")
            
            table = Table(title="Affected Resources (Direct, Indirect & Potential Impact)")
            table.add_column("Level", style="red")
            table.add_column("Resource Type", style="cyan")
            table.add_column("Resource ID", style="yellow")
            table.add_column("Applied Rule", style="magenta")
            table.add_column("Relationship Evidence")

            for item in res.get("affected_resources", []):
                ev = item.get("evidence", {})
                table.add_row(
                    item["impact_level"],
                    item["resource_type"],
                    str(item["resource_id"]),
                    ev.get("rule_applied", "N/A"),
                    ev.get("relationship", "N/A")
                )
            console.print(table)
        else:
            console.print(f"[bold red]Blast Radius Computation Failed: {r.text}[/bold red]")


def run_correlation_demo_cli():
    with console.status("[bold magenta]Running Cross-Layer Engine Live Verification Demo..."):
        r = session.get(f"{API_BASE_URL}/api/demo/correlation")
        if r.status_code == 200:
            res = r.json()
            console.print(Panel(
                f"[bold green]✔ DEMO VERIFICATION: {res['status']}[/bold green]\n\n"
                f"Scenario: [bold cyan]{res['demo']}[/bold cyan]\n"
                f"Generated At: {res['generated_at']}",
                border_style="green" if res['status'] == "PASS" else "red"
            ))
            
            table = Table(title="Deterministic Check Verification")
            table.add_column("Check Name", style="cyan")
            table.add_column("Passed", justify="center")
            table.add_column("Details", style="green")

            for check in res.get("checks", []):
                pass_str = "[bold green]YES[/bold green]" if check["passed"] else "[bold red]NO[/bold red]"
                table.add_row(check["name"], pass_str, check["detail"])
            console.print(table)
        else:
            console.print(f"[bold red]Demo Failed: {r.text}[/bold red]")


def cross_layer_correlation_menu():
    while True:
        console.clear()
        console.print(Panel.fit("[bold cyan]Real-Time Cross-Layer OS-DBMS Correlation Engine[/bold cyan]", border_style="cyan"))
        console.print("[1] Execute Real-Time Event Correlation (OS PID + Transaction + Query)")
        console.print("[2] Run DBMS-OS Auto-Correlation Engine (Match Observations to OS Events)")
        console.print("[3] Compute Incident Blast Radius & Causality Impact")
        console.print("[4] Run Engine Verification Live Demo")
        console.print("[5] View Live Identity Bridge Map (OS PIDs <-> MySQL Connections)")
        console.print("[6] Back to Main Menu")

        choice = Prompt.ask("Choose a Correlation Engine option", choices=["1", "2", "3", "4", "5", "6"])
        if choice == "6":
            break
        elif choice == "1":
            run_cross_layer_correlation()
            Prompt.ask("\nPress Enter to return to Correlation menu")
        elif choice == "2":
            run_auto_correlation()
            Prompt.ask("\nPress Enter to return to Correlation menu")
        elif choice == "3":
            run_blast_radius_analysis()
            Prompt.ask("\nPress Enter to return to Correlation menu")
        elif choice == "4":
            run_correlation_demo_cli()
            Prompt.ask("\nPress Enter to return to Correlation menu")
        elif choice == "5":
            run_identity_bridge_live_map()
            Prompt.ask("\nPress Enter to return to Correlation menu")

def run_identity_bridge_live_map():
    console.print("\n[bold cyan]--- Live Identity Bridge Map (OS PIDs <-> MySQL Connections) ---[/bold cyan]")
    console.print("[1] Instant Passive Scan (Detects any currently open connections)")
    console.print("[2] Live Interactive Demo (Spawns a real client connection to demonstrate dynamic mapping)")

    mode = Prompt.ask("Select Mode", choices=["1", "2"], default="2")
    
    demo_conn = None
    if mode == "2":
        try:
            # Import settings to get MySQL credentials
            import mysql.connector
            from app.config.settings import settings
            console.print("[dim]Opening real client connection to MySQL server...[/dim]")
            demo_conn = mysql.connector.connect(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                database=settings.mysql_database
            )
            time.sleep(0.5)
        except Exception as err:
            console.print(f"[dim yellow]Notice: Could not establish demo connection ({err}), scanning existing sockets instead.[/dim yellow]")

    try:
        with console.status("[bold blue]Scanning OS network sockets and MySQL PROCESSLIST..."):
            r = session.get(f"{API_BASE_URL}/api/bridge/live-map", headers=get_headers())
            
        if r.status_code == 200:
            data = r.json()
            active = data.get("active_bridges", 0)
            mapping = data.get("mapping", [])
            
            console.print(f"\n[bold green]Found {active} Active Bridge(s)[/bold green]")
            
            if active == 0:
                console.print("[yellow]No active OS-level connections to MySQL detected at this exact moment.[/yellow]")
                console.print("Try selecting Option [2] for an automated live test.")
            else:
                table = Table(title="OS PID <===> MySQL Connection Identity Bridge")
                table.add_column("OS Process ID (PID)", style="cyan", justify="right")
                table.add_column("Direction", style="dim", justify="center")
                table.add_column("MySQL Connection ID", style="magenta", justify="left")
                
                for m in mapping:
                    table.add_row(str(m["os_pid"]), "<======>", str(m["mysql_connection_id"]))
                
                console.print(table)
                console.print("\n[bold green]✔ SUCCESS:[/bold green] The Cross-Layer Engine has successfully proved the identity bridge without relying on application-provided metrics!")
        else:
            console.print(f"[bold red]Failed to load map: {r.text}[/bold red]")
    finally:
        if demo_conn:
            try:
                demo_conn.close()
            except:
                pass

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
        log_cli_action(f"OS Simulation Menu Option {choice}")
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


def dbms_simulation_menu():
    while True:
        console.clear()
        console.print(Panel.fit("[bold magenta]DBMS Simulation Lab[/bold magenta]", border_style="magenta"))
        console.print("[1] Serializability & Conflict Graph Analysis")
        console.print("[2] WAL Crash Recovery Simulator")
        console.print("[3] 2PL Lock Manager (Begin/Read/Write/Commit)")
        console.print("[4] Back to Main Menu")

        choice = Prompt.ask("Choose a DBMS Simulation option", choices=["1", "2", "3", "4"])
        log_cli_action(f"DBMS Simulation Menu Option {choice}")
        if choice == "4":
            break
        elif choice == "1":
            run_serializability_lab()
            Prompt.ask("\nPress Enter to return")
        elif choice == "2":
            run_wal_recovery_lab()
            Prompt.ask("\nPress Enter to return")
        elif choice == "3":
            run_2pl_lock_lab()
            Prompt.ask("\nPress Enter to return")


def run_serializability_lab():
    console.print(Panel.fit("[bold cyan]Serializability & Conflict Graph Analysis[/bold cyan]", border_style="cyan"))
    console.print("\nThis lab analyzes a transaction schedule for conflict serializability.")
    console.print("It builds a precedence graph and detects cycles.\n")

    use_preset = Prompt.ask("Use preset demo schedule?", choices=["yes", "no"], default="yes")

    if use_preset == "yes":
        operations = [
            {"transaction_id": 1, "operation": "R", "data_item": "A"},
            {"transaction_id": 2, "operation": "R", "data_item": "A"},
            {"transaction_id": 1, "operation": "W", "data_item": "A"},
            {"transaction_id": 2, "operation": "W", "data_item": "A"},
            {"transaction_id": 1, "operation": "R", "data_item": "B"},
            {"transaction_id": 2, "operation": "W", "data_item": "B"},
        ]
    else:
        operations = []
        console.print("[yellow]Enter operations (e.g. T1 R A). Type 'done' when finished.[/yellow]")
        while True:
            inp = Prompt.ask("Operation (e.g. T1 R A)")
            if inp.strip().lower() == "done":
                break
            parts = inp.strip().split()
            if len(parts) != 3:
                console.print("[red]Format: T<id> R|W <data_item>[/red]")
                continue
            try:
                tid = int(parts[0].replace("T", "").replace("t", ""))
                operations.append({"transaction_id": tid, "operation": parts[1].upper(), "data_item": parts[2]})
            except ValueError:
                console.print("[red]Invalid transaction ID[/red]")

    if not operations:
        console.print("[yellow]No operations entered.[/yellow]")
        return

    with console.status("[bold blue]Analyzing schedule serializability..."):
        r = session.post(f"{API_BASE_URL}/api/schedules/analyze", json={"operations": operations}, headers=get_headers())

    if r.status_code == 200:
        res = r.json()
        sched_table = Table(title="Transaction Schedule")
        sched_table.add_column("Step", justify="right", style="cyan")
        sched_table.add_column("Transaction", style="yellow")
        sched_table.add_column("Op", style="magenta")
        sched_table.add_column("Data Item", style="green")
        for i, op in enumerate(operations, 1):
            sched_table.add_row(str(i), f"T{op['transaction_id']}", op['operation'], op['data_item'])
        console.print(sched_table)

        console.print("\n[bold cyan]Precedence Graph:[/bold cyan]")
        graph = res.get("precedence_graph", {})
        if graph:
            for node, edges in graph.items():
                if edges:
                    edge_str = ", ".join([f"T{e}" for e in edges])
                    console.print(f"  T{node} -> {edge_str}")
                else:
                    console.print(f"  T{node} -> (no outgoing edges)")
        else:
            console.print("  (empty graph)")

        is_serializable = res.get("conflict_serializable", False)
        cycles = res.get("cycles", [])
        if is_serializable:
            console.print(Panel("[bold green]CONFLICT SERIALIZABLE[/bold green]\nNo cycles in precedence graph.", border_style="green"))
        else:
            cycle_str = ", ".join([str(cycle) for cycle in cycles])
            console.print(Panel(f"[bold red]NOT CONFLICT SERIALIZABLE[/bold red]\nCycles detected: {cycle_str}", border_style="red"))
    else:
        console.print(f"[bold red]Failed: {r.text}[/bold red]")


def run_wal_recovery_lab():
    console.print(Panel.fit("[bold cyan]WAL Crash Recovery Simulator[/bold cyan]", border_style="cyan"))
    console.print("\nThis lab simulates ARIES-style UNDO/REDO crash recovery.")
    console.print("Provide initial DB state + WAL log entries, then see which transactions get redone/undone.\n")

    use_preset = Prompt.ask("Use preset crash scenario?", choices=["yes", "no"], default="yes")

    if use_preset == "yes":
        initial_state = {"A": "10", "B": "20", "C": "30"}
        logs = [
            {"sequence": 1, "transaction_id": 1, "log_type": "START"},
            {"sequence": 2, "transaction_id": 1, "log_type": "WRITE", "data_item": "A", "old_value": "10", "new_value": "50"},
            {"sequence": 3, "transaction_id": 2, "log_type": "START"},
            {"sequence": 4, "transaction_id": 2, "log_type": "WRITE", "data_item": "B", "old_value": "20", "new_value": "80"},
            {"sequence": 5, "transaction_id": 1, "log_type": "WRITE", "data_item": "C", "old_value": "30", "new_value": "70"},
            {"sequence": 6, "transaction_id": 1, "log_type": "COMMIT"},
        ]
        console.print("[dim]Preset: T1 committed (A:10->50, C:30->70), T2 active at crash (B:20->80)[/dim]")
    else:
        initial_state = {}
        console.print("[yellow]Enter initial state (e.g. A=10). Type 'done' when finished.[/yellow]")
        while True:
            inp = Prompt.ask("State (e.g. A=10)")
            if inp.strip().lower() == "done":
                break
            parts = inp.strip().split("=")
            if len(parts) == 2:
                initial_state[parts[0].strip()] = parts[1].strip()

        logs = []
        seq = 1
        console.print("[yellow]Enter WAL log entries. Type 'done' when finished.[/yellow]")
        console.print("[dim]Formats: START <tid> | WRITE <tid> <item> <old> <new> | COMMIT <tid>[/dim]")
        while True:
            inp = Prompt.ask(f"Log #{seq}")
            if inp.strip().lower() == "done":
                break
            parts = inp.strip().split()
            entry = {"sequence": seq}
            if parts[0].upper() == "START" and len(parts) >= 2:
                entry.update({"transaction_id": int(parts[1]), "log_type": "START"})
            elif parts[0].upper() == "WRITE" and len(parts) >= 5:
                entry.update({"transaction_id": int(parts[1]), "log_type": "WRITE", "data_item": parts[2], "old_value": parts[3], "new_value": parts[4]})
            elif parts[0].upper() == "COMMIT" and len(parts) >= 2:
                entry.update({"transaction_id": int(parts[1]), "log_type": "COMMIT"})
            else:
                console.print("[red]Invalid format[/red]")
                continue
            logs.append(entry)
            seq += 1

    with console.status("[bold blue]Running WAL crash recovery..."):
        r = session.post(f"{API_BASE_URL}/api/recovery/recover", json={"initial_state": initial_state, "logs": logs}, headers=get_headers())

    if r.status_code == 200:
        res = r.json()
        log_table = Table(title="WAL Log Entries")
        log_table.add_column("Seq", justify="right", style="cyan")
        log_table.add_column("TxID", style="yellow")
        log_table.add_column("Type", style="magenta")
        log_table.add_column("Item", style="green")
        log_table.add_column("Old->New")
        for log_entry in logs:
            item = log_entry.get("data_item", "-")
            change = f"{log_entry.get('old_value', '')}->{log_entry.get('new_value', '')}" if log_entry.get("data_item") else "-"
            log_table.add_row(str(log_entry["sequence"]), f"T{log_entry['transaction_id']}", log_entry["log_type"], item, change)
        console.print(log_table)

        console.print("\n[bold green]Recovery Results:[/bold green]")
        committed = res.get('committed_transactions', [])
        redone = res.get('redone_transactions', [])
        undone = res.get('undone_transactions', [])
        console.print(f"  Committed (REDO):  {['T'+str(t) for t in committed]}" if committed else "  Committed: (none)")
        console.print(f"  Redone:            {['T'+str(t) for t in redone]}" if redone else "  Redone: (none)")
        console.print(f"  Undone (ROLLBACK): {['T'+str(t) for t in undone]}" if undone else "  Undone: (none)")

        state_table = Table(title="Final Database State After Recovery")
        state_table.add_column("Item", style="cyan")
        state_table.add_column("Initial", style="yellow")
        state_table.add_column("Final", style="green")
        final = res.get("final_state", {})
        for k in sorted(set(list(initial_state.keys()) + list(final.keys()))):
            state_table.add_row(k, initial_state.get(k, "?"), final.get(k, "?"))
        console.print(state_table)
    else:
        console.print(f"[bold red]Failed: {r.text}[/bold red]")


def run_2pl_lock_lab():
    console.print(Panel.fit("[bold cyan]2PL Lock Manager & Transaction Lifecycle[/bold cyan]", border_style="cyan"))
    console.print("\nThis lab lets you create transactions, acquire locks, read/write data items, commit/rollback.")
    console.print("It enforces 2-Phase Locking (2PL) with Shared (S) and Exclusive (X) locks.\n")

    while True:
        console.print("[1] Begin Transaction")
        console.print("[2] Acquire Lock")
        console.print("[3] Read Data Item")
        console.print("[4] Write Data Item")
        console.print("[5] Commit Transaction")
        console.print("[6] Rollback Transaction")
        console.print("[7] Back")

        choice = Prompt.ask("Choose", choices=["1", "2", "3", "4", "5", "6", "7"])
        log_cli_action(f"2PL Lab Option {choice}")
        if choice == "7":
            break
        elif choice == "1":
            pid = IntPrompt.ask("Process ID (PID)")
            iso = Prompt.ask("Isolation Level", choices=["READ_UNCOMMITTED", "READ_COMMITTED", "REPEATABLE_READ", "SERIALIZABLE"], default="READ_COMMITTED")
            r = session.post(f"{API_BASE_URL}/api/transactions/begin", json={"pid": pid, "isolation_level": iso}, headers=get_headers())
            if r.status_code == 201:
                data = r.json()
                console.print(f"[bold green]Transaction {data['transaction_id']} started (Status: {data['status']})[/bold green]")
            else:
                console.print(f"[bold red]Failed: {r.text}[/bold red]")
        elif choice == "2":
            txid = IntPrompt.ask("Transaction ID")
            item = Prompt.ask("Data Item (e.g. A)")
            ltype = Prompt.ask("Lock Type", choices=["S", "X"], default="X")
            r = session.post(f"{API_BASE_URL}/api/locks", json={"transaction_id": txid, "data_item": item, "lock_type": ltype}, headers=get_headers())
            if r.status_code == 201:
                data = r.json()
                console.print(f"[bold green]Lock {data['lock_id']} acquired: {data['lock_type']} on '{data['data_item']}' (Status: {data['status']})[/bold green]")
            else:
                console.print(f"[bold red]Failed: {r.text}[/bold red]")
        elif choice == "3":
            txid = IntPrompt.ask("Transaction ID")
            item = Prompt.ask("Data Item to Read")
            r = session.post(f"{API_BASE_URL}/api/transactions/{txid}/read", json={"data_item": item}, headers=get_headers())
            if r.status_code == 200:
                data = r.json()
                console.print(f"[bold green]READ('{item}') by T{data['transaction_id']} at seq #{data['sequence_no']}[/bold green]")
            else:
                console.print(f"[bold red]Failed: {r.text}[/bold red]")
        elif choice == "4":
            txid = IntPrompt.ask("Transaction ID")
            item = Prompt.ask("Data Item to Write")
            r = session.post(f"{API_BASE_URL}/api/transactions/{txid}/write", json={"data_item": item}, headers=get_headers())
            if r.status_code == 200:
                data = r.json()
                console.print(f"[bold green]WRITE('{item}') by T{data['transaction_id']} at seq #{data['sequence_no']}[/bold green]")
            else:
                console.print(f"[bold red]Failed: {r.text}[/bold red]")
        elif choice == "5":
            txid = IntPrompt.ask("Transaction ID")
            r = session.post(f"{API_BASE_URL}/api/transactions/{txid}/commit", json={}, headers=get_headers())
            if r.status_code == 200:
                data = r.json()
                console.print(f"[bold green]Transaction {data['transaction_id']} -> {data['status']}[/bold green]")
            else:
                console.print(f"[bold red]Failed: {r.text}[/bold red]")
        elif choice == "6":
            txid = IntPrompt.ask("Transaction ID")
            r = session.post(f"{API_BASE_URL}/api/transactions/{txid}/rollback", json={}, headers=get_headers())
            if r.status_code == 200:
                data = r.json()
                console.print(f"[bold yellow]Transaction {data['transaction_id']} -> {data['status']}[/bold yellow]")
            else:
                console.print(f"[bold red]Failed: {r.text}[/bold red]")
        console.print()


def what_if_menu():
    while True:
        console.clear()
        console.print(Panel.fit("[bold magenta]What-If Scenario Replay Engine[/bold magenta]", border_style="magenta"))
        console.print("[1] Run What-If Schedule Analysis (Serializability)")
        console.print("[2] Run What-If Recovery Experiment (WAL Crash)")
        console.print("[3] List Saved What-If Scenarios")
        console.print("[4] View Scenario Details")
        console.print("[5] Back to Main Menu")

        choice = Prompt.ask("Choose", choices=["1", "2", "3", "4", "5"])
        log_cli_action(f"What-If Menu Option {choice}")
        if choice == "5":
            break
        elif choice == "1":
            run_whatif_schedule()
            Prompt.ask("\nPress Enter to return")
        elif choice == "2":
            run_whatif_recovery()
            Prompt.ask("\nPress Enter to return")
        elif choice == "3":
            list_whatif_scenarios()
            Prompt.ask("\nPress Enter to return")
        elif choice == "4":
            view_whatif_scenario()
            Prompt.ask("\nPress Enter to return")


def run_whatif_schedule():
    name = Prompt.ask("Scenario Name", default="CLI-WhatIf-Schedule")
    console.print("[yellow]Enter operations (e.g. T1 R A). Type 'done' when finished.[/yellow]")
    console.print("[dim]Or press Enter immediately for preset demo.[/dim]")

    operations = []
    inp = Prompt.ask("First Operation (or Enter for preset)")
    if not inp.strip():
        operations = [
            {"transaction_id": 1, "operation": "R", "data_item": "X"},
            {"transaction_id": 2, "operation": "W", "data_item": "X"},
            {"transaction_id": 1, "operation": "W", "data_item": "X"},
            {"transaction_id": 2, "operation": "R", "data_item": "Y"},
            {"transaction_id": 1, "operation": "W", "data_item": "Y"},
        ]
        console.print("[dim]Using preset: T1:R(X), T2:W(X), T1:W(X), T2:R(Y), T1:W(Y)[/dim]")
    else:
        parts = inp.strip().split()
        if len(parts) == 3:
            operations.append({"transaction_id": int(parts[0].replace("T","").replace("t","")), "operation": parts[1].upper(), "data_item": parts[2]})
        while True:
            inp = Prompt.ask("Operation (or 'done')")
            if inp.strip().lower() == "done":
                break
            parts = inp.strip().split()
            if len(parts) == 3:
                operations.append({"transaction_id": int(parts[0].replace("T","").replace("t","")), "operation": parts[1].upper(), "data_item": parts[2]})

    with console.status("[bold blue]Running What-If Schedule Analysis..."):
        r = session.post(f"{API_BASE_URL}/api/what-if/schedules", json={"name": name, "operations": operations}, headers=get_headers())
    if r.status_code == 201:
        res = r.json()
        console.print(f"\n[bold green]Scenario saved (ID: {res['scenario_id']})[/bold green]")
        result = res.get("result", {})
        is_ser = result.get("conflict_serializable", False)
        if is_ser:
            console.print(Panel("[bold green]CONFLICT SERIALIZABLE[/bold green]", border_style="green"))
        else:
            cycles = result.get("cycles", [])
            console.print(Panel(f"[bold red]NOT SERIALIZABLE - Cycles: {cycles}[/bold red]", border_style="red"))
    else:
        console.print(f"[bold red]Failed: {r.text}[/bold red]")


def run_whatif_recovery():
    name = Prompt.ask("Scenario Name", default="CLI-WhatIf-Recovery")
    console.print("[dim]Using preset crash scenario (T1 committed, T2 active at crash)[/dim]")

    initial_state = {"A": "100", "B": "200"}
    logs = [
        {"sequence": 1, "transaction_id": 1, "log_type": "START"},
        {"sequence": 2, "transaction_id": 1, "log_type": "WRITE", "data_item": "A", "old_value": "100", "new_value": "150"},
        {"sequence": 3, "transaction_id": 2, "log_type": "START"},
        {"sequence": 4, "transaction_id": 2, "log_type": "WRITE", "data_item": "B", "old_value": "200", "new_value": "350"},
        {"sequence": 5, "transaction_id": 1, "log_type": "COMMIT"},
    ]

    with console.status("[bold blue]Running What-If Recovery Experiment..."):
        r = session.post(f"{API_BASE_URL}/api/what-if/recovery", json={"name": name, "initial_state": initial_state, "logs": logs}, headers=get_headers())
    if r.status_code == 201:
        res = r.json()
        console.print(f"\n[bold green]Scenario saved (ID: {res['scenario_id']})[/bold green]")
        result = res.get("result", {})
        console.print(f"  Redone:    {result.get('redone_transactions', [])}")
        console.print(f"  Undone:    {result.get('undone_transactions', [])}")
        console.print(f"  Committed: {result.get('committed_transactions', [])}")
        console.print(f"  Final:     {result.get('final_state', {})}")
    else:
        console.print(f"[bold red]Failed: {r.text}[/bold red]")


def list_whatif_scenarios():
    with console.status("[bold blue]Fetching What-If Scenarios..."):
        r = session.get(f"{API_BASE_URL}/api/what-if/scenarios?limit=20", headers=get_headers())
    if r.status_code == 200:
        scenarios = r.json()
        if not scenarios:
            console.print("[yellow]No What-If scenarios found.[/yellow]")
            return
        table = Table(title="Saved What-If Scenarios")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Name", style="green")
        table.add_column("Created", style="yellow")
        for s in scenarios:
            table.add_row(str(s["scenario_id"]), s["analysis_type"], s["name"], s["created_at"])
        console.print(table)
    else:
        console.print(f"[bold red]Failed: {r.text}[/bold red]")


def view_whatif_scenario():
    sid = IntPrompt.ask("Scenario ID")
    with console.status("[bold blue]Fetching Scenario..."):
        r = session.get(f"{API_BASE_URL}/api/what-if/scenarios/{sid}", headers=get_headers())
    if r.status_code == 200:
        s = r.json()
        console.print(Panel(f"[bold]{s['name']}[/bold] (Type: {s['analysis_type']}, ID: {s['scenario_id']})", border_style="cyan"))
        console.print("\n[bold]Input Data:[/bold]")
        for k, v in s.get("input_data", {}).items():
            console.print(f"  {k}: {v}")
        console.print("\n[bold]Result:[/bold]")
        for k, v in s.get("result", {}).items():
            console.print(f"  {k}: {v}")
    elif r.status_code == 404:
        console.print("[bold red]Scenario not found.[/bold red]")
    else:
        console.print(f"[bold red]Failed: {r.text}[/bold red]")


def investigations_menu():
    while True:
        console.clear()
        console.print(Panel.fit("[bold magenta]Incident Investigation & Replay[/bold magenta]", border_style="magenta"))
        console.print("[1] Investigate Incident (Deep-Dive Root Cause)")
        console.print("[2] Replay Incident (Forensic Replay)")
        console.print("[3] Back to Main Menu")

        choice = Prompt.ask("Choose", choices=["1", "2", "3"])
        log_cli_action(f"Investigation Menu Option {choice}")
        if choice == "3":
            break
        elif choice == "1":
            incident_id = IntPrompt.ask("Incident ID to investigate")
            with console.status("[bold blue]Running deep investigation..."):
                r = session.get(f"{API_BASE_URL}/api/incidents/{incident_id}/investigation", headers=get_headers())
            if r.status_code == 200:
                inv = r.json()
                incident = inv.get("incident", {})
                console.print(Panel(
                    f"[bold]Incident #{incident.get('incident_id', incident_id)}[/bold]\n"
                    f"Type: {incident.get('incident_type', 'N/A')}\n"
                    f"Description: {incident.get('description', 'N/A')}\n"
                    f"Severity: {incident.get('severity', 'N/A')}",
                    border_style="red",
                    title="Incident Details"
                ))
                timeline = inv.get("timeline", [])
                if timeline:
                    tl_table = Table(title="Investigation Timeline")
                    tl_table.add_column("Seq", justify="right", style="cyan")
                    tl_table.add_column("Source", style="magenta")
                    tl_table.add_column("Event", style="yellow")
                    tl_table.add_column("Description", style="green")
                    for entry in timeline:
                        tl_table.add_row(str(entry["sequence"]), entry["source"], entry["event_type"], entry["description"])
                    console.print(tl_table)
                perf = inv.get("performance", [])
                if perf:
                    console.print(f"\n[bold]Performance Records:[/bold] {len(perf)} entries collected")
            elif r.status_code == 404:
                console.print("[bold red]Incident not found.[/bold red]")
            else:
                console.print(f"[bold red]Failed: {r.text}[/bold red]")
            Prompt.ask("\nPress Enter to return")
        elif choice == "2":
            incident_id = IntPrompt.ask("Incident ID to replay")
            with console.status("[bold blue]Replaying incident..."):
                r = session.post(f"{API_BASE_URL}/api/incidents/{incident_id}/replay", json={}, headers=get_headers())
            if r.status_code == 200:
                replay = r.json()
                console.print(Panel(
                    f"[bold green]Replay Complete[/bold green]\n"
                    f"Replay ID: {replay.get('replay_id')}\n"
                    f"Outcome: {replay.get('outcome')}\n"
                    f"Summary: {replay.get('summary')}",
                    border_style="green"
                ))
                steps = replay.get("steps", [])
                if steps:
                    st_table = Table(title="Replay Steps")
                    st_table.add_column("Seq", justify="right", style="cyan")
                    st_table.add_column("Source", style="magenta")
                    st_table.add_column("Event", style="yellow")
                    st_table.add_column("Description", style="green")
                    for step in steps:
                        st_table.add_row(str(step["sequence"]), step["source"], step["event_type"], step["description"])
                    console.print(st_table)
            elif r.status_code == 404:
                console.print("[bold red]Incident not found.[/bold red]")
            elif r.status_code == 409:
                console.print(f"[bold yellow]Replay unavailable: {r.json().get('detail', '')}[/bold yellow]")
            else:
                console.print(f"[bold red]Failed: {r.text}[/bold red]")
            Prompt.ask("\nPress Enter to return")


def performance_menu():
    while True:
        console.clear()
        console.print(Panel.fit("[bold magenta]Performance & Bottleneck Analysis[/bold magenta]", border_style="magenta"))
        console.print("[1] View Recent Performance Records")
        console.print("[2] Record New Performance Metric")
        console.print("[3] Back to Main Menu")

        choice = Prompt.ask("Choose", choices=["1", "2", "3"])
        log_cli_action(f"Performance Menu Option {choice}")
        if choice == "3":
            break
        elif choice == "1":
            with console.status("[bold blue]Fetching Performance Records..."):
                r = session.get(f"{API_BASE_URL}/api/performance/records?limit=25", headers=get_headers())
            if r.status_code == 200:
                records = r.json()
                if not records:
                    console.print("[yellow]No performance records found.[/yellow]")
                else:
                    table = Table(title="Performance Records")
                    table.add_column("ID", justify="right", style="cyan")
                    table.add_column("Metric", style="green")
                    table.add_column("Value", justify="right", style="yellow")
                    table.add_column("Trace ID", style="magenta")
                    table.add_column("Recorded At", style="dim")
                    for rec in records:
                        table.add_row(
                            str(rec["record_id"]),
                            rec["metric_name"],
                            f"{rec['metric_value']:.2f}",
                            str(rec.get("trace_id") or "-"),
                            rec["recorded_at"]
                        )
                    console.print(table)
            else:
                console.print(f"[bold red]Failed: {r.text}[/bold red]")
            Prompt.ask("\nPress Enter to return")
        elif choice == "2":
            metric_name = Prompt.ask("Metric Name (e.g. query_latency_ms)")
            metric_value = float(Prompt.ask("Metric Value"))
            trace_id_str = Prompt.ask("Trace ID (optional, Enter to skip)", default="")
            payload = {"metric_name": metric_name, "metric_value": metric_value}
            if trace_id_str.strip():
                payload["trace_id"] = int(trace_id_str)
            r = session.post(f"{API_BASE_URL}/api/performance/records", json=payload, headers=get_headers())
            if r.status_code == 201:
                rec = r.json()
                console.print(f"[bold green]Performance record created (ID: {rec['record_id']})[/bold green]")
            else:
                console.print(f"[bold red]Failed: {r.text}[/bold red]")
            Prompt.ask("\nPress Enter to return")


def admin_audit_logs():
    with console.status("[bold blue]Fetching Audit Logs..."):
        r = session.get(f"{API_BASE_URL}/api/audit/", headers=get_headers())
        if r.status_code == 200:
            logs = r.json()
            if not logs:
                console.print("[bold yellow]No audit logs found.[/bold yellow]")
            else:
                table = Table(title="Admin Audit Logs")
                table.add_column("ID", style="cyan", justify="right")
                table.add_column("Timestamp", style="magenta")
                table.add_column("User", style="green")
                table.add_column("Action", style="yellow")
                for log in logs:
                    table.add_row(
                        str(log["id"]),
                        log["timestamp"],
                        f"{log['username']} (UID: {log['user_id']})",
                        log["action"]
                    )
                console.print(table)
        elif r.status_code == 403:
            console.print("[bold red]Access Denied: Admin privileges required to view logs.[/bold red]")
        else:
            console.print(f"[bold red]Failed to fetch audit logs: {r.text}[/bold red]")
    Prompt.ask("\nPress Enter to return")



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

        console.print("[1]  View Live DBMS Observations (Query Fetcher)")
        console.print("[2]  View Recent Deadlocks & Incidents")
        console.print("[3]  Real-Time Cross-Layer OS-DBMS Correlation Engine")
        console.print("[4]  Incident Blast Radius & Causality Analysis")
        console.print("[5]  Run Live Benchmark Simulator (OS + DBMS Load)")
        console.print("[6]  Collect OS-DB Events (Ping Performance Schema)")
        console.print("[7]  OS Simulation Lab (Scheduling, Memory, Deadlocks)")
        console.print("[8]  DBMS Simulation Lab (Serializability, WAL, 2PL)")
        console.print("[9]  What-If Scenario Replay Engine")
        console.print("[10] Incident Investigation & Replay")
        console.print("[11] Performance & Bottleneck Analysis")
        console.print("[12] Admin Audit Logs Viewer")
        console.print("[13] Logout / Exit")
        
        choice = Prompt.ask("Choose an action", choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"])
        log_cli_action(f"Main Menu Option {choice}")
        
        console.clear()
        if choice == "13":
            console.print("[bold yellow]Logging out...[/bold yellow]")
            sys.exit(0)
            
        elif choice == "1":
            fetch_dbms_observations()
            Prompt.ask("\nPress Enter to return to menu")
            
        elif choice == "2":
            fetch_deadlocks()
            Prompt.ask("\nPress Enter to return to menu")

        elif choice == "3":
            cross_layer_correlation_menu()

        elif choice == "4":
            run_blast_radius_analysis()
            Prompt.ask("\nPress Enter to return to menu")

        elif choice == "5":
            run_benchmark()
            Prompt.ask("\nPress Enter to return to menu")
            
        elif choice == "6":
            with console.status("[bold blue]Collecting events from MySQL Performance Schema..."):
                r = session.post(f"{API_BASE_URL}/api/dbms-events/collect", json={"limit": 25, "persist": True}, headers=get_headers())
                if r.status_code == 200:
                    data = r.json()
                    console.print(f"\n[bold green]Collection Success![/bold green]")
                    console.print(f"Collected: {data.get('collected')} | Persisted: {data.get('persisted')}")
                else:
                    console.print(f"[bold red]Collection Failed: {r.text}[/bold red]")
            Prompt.ask("\nPress Enter to return to menu")

        elif choice == "7":
            os_simulation_menu()
            
        elif choice == "8":
            dbms_simulation_menu()

        elif choice == "9":
            what_if_menu()

        elif choice == "10":
            investigations_menu()

        elif choice == "11":
            performance_menu()
            
        elif choice == "12":
            admin_audit_logs()

if __name__ == "__main__":
    try:
        login_menu()
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[bold red]Exiting...[/bold red]")
        sys.exit(0)
