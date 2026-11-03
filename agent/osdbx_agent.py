#!/usr/bin/env python3
"""
OS-DBX Enterprise Endpoint Forensic Agent
-----------------------------------------
Lightweight, silent endpoint collector for host-level OS forensics.
- Monitors process lifecycle (creation/termination) via psutil.
- Monitors filesystem mutations via watchdog.
- Captures per-host CPU, RAM, and I/O metrics.
- Streams normalized telemetry to central OS-DBX API.
- Cleans up gracefully on termination.
"""

import argparse
import datetime
import getpass
import json
import logging
import os
import platform
import signal
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

def get_base_dir() -> str:
    """Return the executable directory when frozen (PyInstaller) or the script directory."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

# Setup local file logging
LOG_FILE = os.path.join(get_base_dir(), "agent.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

# Configuration defaults
DEFAULT_CONFIG = {
    "server_url": "http://127.0.0.1:8000",
    "host_id": socket.gethostname(),
    "watch_paths": ["."],
    "poll_interval_sec": 3.0,
    "max_batch_size": 25,
    "api_token": "osdbx-default-token",
}


def load_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    base_dir = get_base_dir()
    for potential_dir in [base_dir, os.getcwd()]:
        cfg_path = os.path.join(potential_dir, "config.json")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    config.update(loaded)
                    break
            except Exception as e:
                logging.warning("Could not read config.json, using defaults: %s", e)

    # Environment variable overrides
    if os.environ.get("OSDBX_SERVER_URL"):
        config["server_url"] = os.environ["OSDBX_SERVER_URL"]
    if os.environ.get("OSDBX_HOST_ID"):
        config["host_id"] = os.environ["OSDBX_HOST_ID"]
    if os.environ.get("OSDBX_API_TOKEN"):
        config["api_token"] = os.environ["OSDBX_API_TOKEN"]

    if not config.get("host_id"):
        config["host_id"] = socket.gethostname()

    config["server_url"] = config["server_url"].rstrip("/")
    return config


class OSDBXAgent:
    def __init__(self, config: dict):
        self.config = config
        self.server_url = config["server_url"]
        self.host_id = config["host_id"]
        self.watch_paths = config.get("watch_paths", ["."])
        self.poll_interval = float(config.get("poll_interval_sec", 3.0))
        self.is_running = False
        self._threads: list[threading.Thread] = []
        self._stop_event = threading.Event()
        self._event_queue: list[dict] = []
        self._queue_lock = threading.Lock()
        self._known_processes: dict[int, dict] = {}

    def _post_json(self, endpoint: str, payload: dict) -> bool:
        url = f"{self.server_url}{endpoint}"
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"OSDBX-Agent/1.0 ({platform.system()}; {self.host_id})",
        }
        if self.config.get("api_token"):
            headers["Authorization"] = f"Bearer {self.config['api_token']}"
        req = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status in (200, 201):
                    if getattr(self, "_had_conn_error", False):
                        logging.info("[✓] Successfully connected to %s! Streaming live telemetry.", self.server_url)
                        self._had_conn_error = False
                    return True
                return False
        except urllib.error.HTTPError as he:
            logging.debug("POST %s returned HTTP %d: %s", endpoint, he.code, he.reason)
            # If server rejected due to client validation (400 or 422), do not retry
            if he.code in (400, 422):
                return True
            return False
        except Exception as e:
            now = time.time()
            if now - getattr(self, "_last_conn_warning_time", 0) > 30.0:
                self._last_conn_warning_time = now
                self._had_conn_error = True
                logging.warning("Cannot reach %s (%s). Buffering events in memory...", self.server_url, e)
            return False

    def enqueue_event(self, event: dict):
        with self._queue_lock:
            if len(self._event_queue) > 1000:
                self._event_queue.pop(0)  # Drop oldest if queue overflows
            self._event_queue.append(event)

    def _flush_worker(self):
        """Background flusher sending queued events to OS-DBX server."""
        while not self._stop_event.is_set():
            batch = []
            with self._queue_lock:
                if self._event_queue:
                    batch = self._event_queue[: self.config.get("max_batch_size", 25)]
                    self._event_queue = self._event_queue[len(batch) :]

            if batch:
                sent_count = 0
                for index, ev in enumerate(batch):
                    endpoint = (
                        "/api/os-events/filesystem"
                        if ev.get("is_filesystem")
                        else "/api/os-events"
                    )
                    payload = {k: v for k, v in ev.items() if k != "is_filesystem"}
                    success = self._post_json(endpoint, payload)
                    if not success:
                        # Preserve the failed event and every event not yet sent.
                        with self._queue_lock:
                            self._event_queue = batch[index:] + self._event_queue
                        time.sleep(1.0)
                        break
                    sent_count += 1
                if sent_count > 0:
                    logging.info("Streamed %d forensic event(s) to %s", sent_count, self.server_url)

            time.sleep(0.5)

    def _monitor_processes(self):
        """Differential process watcher emitting process_created and process_terminated."""
        try:
            import psutil
        except ImportError:
            logging.error("psutil is required. Run 'pip install psutil'.")
            return

        # Initial baseline snapshot: cache and stream active processes
        baseline_events = []
        for p in psutil.process_iter(["pid", "ppid", "name", "username", "exe"]):
            try:
                info = p.info
                pid = info["pid"]
                if not pid or pid <= 0:
                    continue
                self._known_processes[pid] = info
                now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                raw_user = (info.get("username") or getpass.getuser() or "system").strip()
                user = raw_user if raw_user else "system"
                raw_ppid = info.get("ppid") or 0
                ppid = max(0, int(raw_ppid))
                event = {
                    "event_id": str(uuid.uuid4()),
                    "source": "OS",
                    "timestamp": now_iso,
                    "event_type": "process_created",
                    "operation": "process_baseline",
                    "pid": pid,
                    "ppid": ppid,
                    "process_name": info.get("name") or "unknown",
                    "user": user,
                    "file_path": info.get("exe"),
                    "host_id": self.host_id,
                    "evidence_completeness": "5/5",
                    "is_filesystem": False,
                }
                baseline_events.append(event)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        logging.info("Baseline process snapshot: %d active processes.", len(self._known_processes))
        for ev in baseline_events:
            self.enqueue_event(ev)

        while not self._stop_event.is_set():
            time.sleep(self.poll_interval)
            current_pids = set()

            for p in psutil.process_iter(["pid", "ppid", "name", "username", "exe"]):
                try:
                    info = p.info
                    pid = info["pid"]
                    if not pid or pid <= 0:
                        continue
                    current_pids.add(pid)

                    if pid not in self._known_processes:
                        self._known_processes[pid] = info
                        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                        raw_user = (info.get("username") or getpass.getuser() or "system").strip()
                        user = raw_user if raw_user else "system"
                        raw_ppid = info.get("ppid") or 0
                        ppid = max(0, int(raw_ppid))
                        event = {
                            "event_id": str(uuid.uuid4()),
                            "source": "OS",
                            "timestamp": now_iso,
                            "event_type": "process_created",
                            "operation": "process_spawn",
                            "pid": pid,
                            "ppid": ppid,
                            "process_name": info.get("name") or "unknown",
                            "user": user,
                            "file_path": info.get("exe"),
                            "host_id": self.host_id,
                            "evidence_completeness": "5/5",
                            "is_filesystem": False,
                        }
                        self.enqueue_event(event)
                        logging.debug("Created process: %s (PID: %d)", info.get("name"), pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Check terminated processes
            terminated_pids = set(self._known_processes.keys()) - current_pids
            for t_pid in terminated_pids:
                old_info = self._known_processes.pop(t_pid, {})
                if not t_pid or t_pid <= 0:
                    continue
                now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                raw_user = (old_info.get("username") or getpass.getuser() or "system").strip()
                user = raw_user if raw_user else "system"
                raw_ppid = old_info.get("ppid") or 0
                ppid = max(0, int(raw_ppid))
                event = {
                    "event_id": str(uuid.uuid4()),
                    "source": "OS",
                    "timestamp": now_iso,
                    "event_type": "process_terminated",
                    "operation": "process_exit",
                    "pid": t_pid,
                    "ppid": ppid,
                    "process_name": old_info.get("name") or "unknown",
                    "user": user,
                    "file_path": old_info.get("exe"),
                    "host_id": self.host_id,
                    "evidence_completeness": "4/5",
                    "is_filesystem": False,
                }
                self.enqueue_event(event)
                logging.debug("Terminated process: %s (PID: %d)", old_info.get("name"), t_pid)

    def _monitor_resources(self):
        """Collect host system resource metrics and top active processes."""
        try:
            import psutil
        except ImportError:
            return

        # Prime psutil cpu measurement
        for p in psutil.process_iter():
            try:
                p.cpu_percent(interval=None)
            except Exception:
                continue

        while not self._stop_event.is_set():
            time.sleep(self.poll_interval * 2)
            try:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                net = psutil.net_io_counters()

                now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

                # 1. Sample agent itself with true process RSS memory
                try:
                    my_proc = psutil.Process()
                    my_mem_mb = my_proc.memory_info().rss / (1024 * 1024)
                    my_cpu = my_proc.cpu_percent(interval=None)
                    agent_event = {
                        "event_id": str(uuid.uuid4()),
                        "source": "OS",
                        "timestamp": now_iso,
                        "event_type": "resource_sample",
                        "operation": "host_metrics",
                        "pid": os.getpid(),
                        "ppid": 0,
                        "process_name": "osdbx_agent",
                        "user": (getpass.getuser() or "system").strip() or "system",
                        "resource_info": {
                            "cpu_usage": round(my_cpu, 1),
                            "memory_usage": round((my_mem_mb * 1024 * 1024 / (mem.total or 1)) * 100, 1),
                            "memory_used_mb": round(my_mem_mb, 1),
                            "network_io": round((net.bytes_sent + net.bytes_recv) / 1024, 2),
                        },
                        "host_id": self.host_id,
                        "evidence_completeness": "5/5",
                        "is_filesystem": False,
                    }
                    self.enqueue_event(agent_event)
                except Exception:
                    pass

                # 2. Sample top active processes by CPU and memory
                active_procs = []
                for p in psutil.process_iter(["pid", "name"]):
                    try:
                        pid = p.info["pid"]
                        if pid == 0 or pid == os.getpid():
                            continue
                        p_cpu = p.cpu_percent(interval=None)
                        p_mem = p.memory_info().rss / (1024 * 1024)
                        if p_cpu > 0.0 or p_mem > 30.0:
                            active_procs.append((p_cpu, p_mem, pid, p.info.get("name") or "unknown"))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                active_procs.sort(key=lambda x: (x[0], x[1]), reverse=True)
                for p_cpu, p_mem_mb, p_pid, p_name in active_procs[:12]:
                    sample_event = {
                        "event_id": str(uuid.uuid4()),
                        "source": "OS",
                        "timestamp": now_iso,
                        "event_type": "resource_sample",
                        "operation": "process_resource_sample",
                        "pid": p_pid,
                        "ppid": 0,
                        "process_name": p_name,
                        "user": (getpass.getuser() or "system").strip() or "system",
                        "resource_info": {
                            "cpu_usage": round(p_cpu, 1),
                            "memory_usage": round((p_mem_mb * 1024 * 1024 / (mem.total or 1)) * 100, 1),
                            "memory_used_mb": round(p_mem_mb, 1),
                            "network_io": 0.0,
                        },
                        "host_id": self.host_id,
                        "evidence_completeness": "5/5",
                        "is_filesystem": False,
                    }
                    self.enqueue_event(sample_event)
            except Exception as e:
                logging.debug("Resource sampling error: %s", e)

    def _start_filesystem_monitor(self):
        """Watch paths for filesystem changes using watchdog."""
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            logging.warning("watchdog package not installed; filesystem monitoring disabled.")
            return

        agent_ref = self

        class Handler(FileSystemEventHandler):
            def on_created(self, event):
                agent_ref._handle_fs("file_created", event)

            def on_modified(self, event):
                agent_ref._handle_fs("file_modified", event)

            def on_deleted(self, event):
                agent_ref._handle_fs("file_deleted", event)

        observer = Observer()
        handler = Handler()
        for p in self.watch_paths:
            resolved = os.path.abspath(p)
            if os.path.exists(resolved):
                observer.schedule(handler, resolved, recursive=True)
                logging.info("Watching filesystem path: %s", resolved)

        observer.daemon = True
        observer.start()

        def _fs_loop():
            while not self._stop_event.is_set():
                time.sleep(1.0)
            observer.stop()
            observer.join(timeout=2.0)

        t = threading.Thread(target=_fs_loop, daemon=True)
        self._threads.append(t)
        t.start()

    def _handle_fs(self, ev_type: str, fs_event):
        # Ignore agent's own log file to prevent infinite event loop
        if fs_event.src_path.endswith("agent.log") or fs_event.src_path.endswith(".tmp"):
            return

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": now_iso,
            "event_type": ev_type,
            "file_path": fs_event.src_path,
            "host_id": self.host_id,
            "operation": "fs_watchdog",
            "metadata": {"is_directory": fs_event.is_directory},
            "is_filesystem": True,
        }
        self.enqueue_event(event)

    def _heartbeat_worker(self):
        """Send periodic 30-second heartbeat lease to the server."""
        while not self._stop_event.is_set():
            if self.config.get("api_token"):
                self._post_json("/api/devices/heartbeat", {})
            self._stop_event.wait(30.0)

    def start(self):
        self.is_running = True
        self._stop_event.clear()
        logging.info("==========================================================")
        logging.info("  OS-DBX Forensic Collector Agent Active")
        logging.info("  Host ID:    %s", self.host_id)
        logging.info("  Target API: %s", self.server_url)
        logging.info("  OS:         %s %s", platform.system(), platform.release())
        logging.info("==========================================================")

        # 1. Start Flush Worker
        t_flush = threading.Thread(target=self._flush_worker, daemon=True)
        self._threads.append(t_flush)
        t_flush.start()

        # 2. Start Process Monitor
        t_proc = threading.Thread(target=self._monitor_processes, daemon=True)
        self._threads.append(t_proc)
        t_proc.start()

        # 3. Start Resource Monitor
        t_res = threading.Thread(target=self._monitor_resources, daemon=True)
        self._threads.append(t_res)
        t_res.start()

        # 4. Start Filesystem Monitor
        self._start_filesystem_monitor()

        # 5. Start Heartbeat Worker (30s lease)
        t_heartbeat = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self._threads.append(t_heartbeat)
        t_heartbeat.start()

    def stop(self):
        logging.info("Stopping OS-DBX Agent...")
        self.is_running = False
        self._stop_event.set()
        for t in self._threads:
            t.join(timeout=1.5)
        logging.info("OS-DBX Agent safely stopped.")


def write_pid_file():
    pid_path = os.path.join(get_base_dir(), "agent.pid")
    try:
        with open(pid_path, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def remove_pid_file():
    pid_path = os.path.join(get_base_dir(), "agent.pid")
    if os.path.exists(pid_path):
        try:
            os.remove(pid_path)
        except Exception:
            pass


def normalize_server_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    tunnel_domains = (
        ".trycloudflare.com",
        ".loca.lt",
        ".ngrok",
        ".pinggy.link",
        ".serveo.net",
        ".herokuapp.com",
        ".onrender.com",
        ".railway.app",
    )
    is_known_tunnel = any(d in raw.lower() for d in tunnel_domains)
    if is_known_tunnel:
        if raw.startswith("http://"):
            raw = f"https://{raw[7:]}"
        elif not raw.startswith("https://"):
            raw = f"https://{raw}"
    elif not raw.startswith("http://") and not raw.startswith("https://"):
        raw = f"http://{raw}"

    # Do not append :8000 if it is https:// or a known tunnel/cloud domain
    if not raw.startswith("https://") and not is_known_tunnel:
        host_part = raw.split("://", 1)[1]
        if ":" not in host_part and "/" not in host_part:
            raw = f"{raw}:8000"
    return raw.rstrip("/")


def main():
    parser = argparse.ArgumentParser(description="OS-DBX Endpoint Forensic Collector")
    parser.add_argument("--server", "-s", help="OS-DBX Server API URL (e.g. http://10.72.84.192:8000 or https://xyz.trycloudflare.com)")
    parser.add_argument("--host-id", help="Custom Host Identifier")
    parser.add_argument("--token", "-t", help="Device Bearer Token")
    parser.add_argument("--watch-path", "-w", help="Path to monitor for filesystem mutations (default: current directory)")
    args = parser.parse_args()

    config = load_config()

    if args.server:
        config["server_url"] = normalize_server_url(args.server)
    else:
        # Prompt the user for server IP whenever run without --server flag
        print("\n" + "=" * 66)
        print("          OS-DBX Forensic Collector Agent")
        print("=" * 66)
        saved_server = config.get("server_url") or "http://10.72.84.192:8000"
        print("\nEnter your OS-DBX Server IP, Hostname, or Tunnel URL:")
        print("  - LAN Examples:    10.72.84.192  OR  LAPTOP-GP6CB324  OR  192.168.1.5:8000")
        print("  - Tunnel Examples: https://xyz.trycloudflare.com  OR  https://xyz.loca.lt\n")
        try:
            prompt_text = f"Server IP / Hostname [Press Enter for {saved_server}]: "
            entered = input(prompt_text).strip()
            if entered:
                config["server_url"] = normalize_server_url(entered)
            else:
                config["server_url"] = saved_server

            default_host = config.get("host_id") or socket.gethostname()
            entered_host = input(f"Host / PC Name       [Press Enter for '{default_host}']: ").strip()
            if entered_host:
                config["host_id"] = entered_host
            else:
                config["host_id"] = default_host

            # Save to config.json next to executable so it remembers for next time
            cfg_save_path = os.path.join(get_base_dir(), "config.json")
            try:
                with open(cfg_save_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "server_url": config["server_url"],
                        "host_id": config["host_id"],
                        "api_token": config.get("api_token", "osdbx-default-token")
                    }, f, indent=2)
            except Exception:
                pass
            print(f"\n[✓] Connecting to: {config['server_url']}")
            print(f"[✓] Reporting as:  {config['host_id']}\n")
        except (EOFError, KeyboardInterrupt):
            pass

    if args.host_id:
        config["host_id"] = args.host_id
    if args.token:
        config["api_token"] = args.token
    if args.watch_path:
        config["watch_paths"] = [args.watch_path]

    write_pid_file()
    agent = OSDBXAgent(config)

    def handle_exit(sig, frame):
        agent.stop()
        remove_pid_file()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    agent.start()

    # Keep main thread alive
    try:
        while agent.is_running:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        agent.stop()
        remove_pid_file()


if __name__ == "__main__":
    main()
