import threading
import time
import psutil
from typing import List
from ..core.adapter import OSCollectorAdapter
from ..core.stream import LiveEventStream
from ..core.events import NormalizedOSEvent

class WindowsAdapter(OSCollectorAdapter):
    """
    Concrete adapter for the current platform (Windows/psutil/watchdog).
    Provides normalized OS events to the stream.
    """
    def __init__(self, stream: LiveEventStream, watch_paths: List[str] = None):
        super().__init__(stream)
        self.watch_paths = watch_paths or []
        self._threads = []
        self._stop_event = threading.Event()

    def start(self) -> None:
        self.is_running = True
        self._stop_event.clear()
        
        # Start Process Monitor Thread
        t_proc = threading.Thread(target=self._monitor_processes, daemon=True)
        self._threads.append(t_proc)
        t_proc.start()

        # Start Resource Monitor Thread
        t_res = threading.Thread(target=self._monitor_resources, daemon=True)
        self._threads.append(t_res)
        t_res.start()

        # Filesystem monitor would be integrated here 
        # using watchdog if watch_paths are provided.
        if self.watch_paths:
            self._start_filesystem_monitor()

    def stop(self) -> None:
        self.is_running = False
        self._stop_event.set()
        for t in self._threads:
            t.join(timeout=1.0)
            
    def _monitor_processes(self):
        """Simple differential process monitor emitting normalized events."""
        known_pids = set(psutil.pids())
        
        while not self._stop_event.is_set():
            time.sleep(2)
            current_pids = set(psutil.pids())
            
            # Process Created
            for pid in current_pids - known_pids:
                try:
                    proc = psutil.Process(pid)
                    event = NormalizedOSEvent(
                        event_type="process_created",
                        operation="start",
                        pid=pid,
                        process_name=proc.name(),
                        metadata={"ppid": proc.ppid(), "state": proc.status()}
                    )
                    self.stream.publish(event)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Process Terminated
            for pid in known_pids - current_pids:
                event = NormalizedOSEvent(
                    event_type="process_terminated",
                    operation="stop",
                    pid=pid,
                    process_name=None, # Gone
                )
                self.stream.publish(event)
                
            known_pids = current_pids

    def _monitor_resources(self):
        """Resource monitor emitting normalized events."""
        # Warmup cpu_percent
        for proc in psutil.process_iter():
            try:
                proc.cpu_percent(interval=None)
            except:
                pass
                
        while not self._stop_event.is_set():
            time.sleep(5)
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    pid = proc.info["pid"]
                    if pid == 0: continue # System Idle Process
                    
                    cpu = proc.cpu_percent(interval=None)
                    mem = proc.memory_percent()
                    
                    if cpu < 1.0 and mem < 0.5:
                        continue
                    
                    io = proc.io_counters() if hasattr(proc, 'io_counters') else None
                    disk_io = (io.read_bytes + io.write_bytes) if io else None

                    event = NormalizedOSEvent(
                        event_type="resource_usage",
                        operation="metric",
                        pid=pid,
                        process_name=proc.info["name"],
                        resource_info={
                            "cpu_usage": round(cpu, 2),
                            "memory_usage": round(mem, 2),
                            "disk_io": disk_io,
                            "network_io": None
                        }
                    )
                    self.stream.publish(event)
                except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                    continue

    def _start_filesystem_monitor(self):
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class NormalizedFSEventHandler(FileSystemEventHandler):
                def __init__(self, stream):
                    self.stream = stream
                    
                def _emit(self, op, path, is_dir=False, old_path=None):
                    event = NormalizedOSEvent(
                        event_type=f"file_{op}",
                        operation=op,
                        pid=None, # Intentionally null
                        file_path=path,
                        metadata={"is_directory": is_dir, "old_path": old_path}
                    )
                    self.stream.publish(event)

                def on_created(self, event):
                    self._emit("created", event.src_path, event.is_directory)
                def on_modified(self, event):
                    if not event.is_directory:
                        self._emit("modified", event.src_path)
                def on_deleted(self, event):
                    self._emit("deleted", event.src_path, event.is_directory)
                def on_moved(self, event):
                    self._emit("moved", event.dest_path, event.is_directory, event.src_path)

            handler = NormalizedFSEventHandler(self.stream)
            observer = Observer()
            for path in self.watch_paths:
                observer.schedule(handler, path, recursive=True)
            observer.start()
            
            # Keep track so we can stop it
            self._observer = observer
        except ImportError:
            pass # watchdog not installed

    def get_health(self) -> dict:
        return {
            "status": "running" if self.is_running else "stopped",
            "threads_active": sum(1 for t in self._threads if t.is_alive())
        }
