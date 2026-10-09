# OS-DBX – Work Completed So Far

**For the group – current status as of filesystem monitor completion**

---

### Project Goal (reminder)
Unified platform that correlates OS-level activity with DBMS activity for better visibility and analysis.  
MVP focuses on **OS Live Monitoring** + basic correlation foundations, following the master doc.

---

### Completed & in review (OS Live Monitoring)

| Module                | Status                          | Branch / PR                          | Key details |
|-----------------------|---------------------------------|--------------------------------------|-------------|
| **Process Monitor**   | Done + tested on real machine   | Already pushed / in review           | Collects running process data into the shared `os_events` JSON shape |
| **Resource Monitor**  | Done + tested on real machine   | Already pushed / in review           | Collects CPU / memory / resource metrics in the same shared event format |
| **Filesystem Monitor**| Done + tested on real machine   | `feature/filesystem-monitor` (just pushed) | Uses `watchdog`. Watches one or more folders at once. Detects create / modify / delete / rename. Emits events in the shared `os_events` JSON shape. `pid` is intentionally `null` (file→process attribution needs OS-level auditing / eBPF / auditd — out of MVP scope). Multi-folder support verified locally. |

All three produce events in the **same JSON shape** so the correlation layer can consume them later without format changes.

---

### What’s still open / next logical pieces

1. Any remaining OS Live Monitoring items from the master doc (if any).
2. Start the correlation / visibility layer that consumes the shared `os_events` stream.
3. DBMS-side collectors (once OS side is solid).

---

### Practical notes for the group

- All collectors write to the agreed event format so downstream work can start in parallel.
- Filesystem monitor deliberately leaves `pid` null — don’t expect process attribution from it in MVP.
- Test folders and `filesystem_events.jsonl` are gitignored.
- PRs should target **`develop`** (not `main`).

---

*Ready for the next phase. Let the team know what each person wants to pick up.*
