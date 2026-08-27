# OS-DBX Database Data Dictionary

**Project:** OS-DBX — Unified OS + DBMS Correlation and Visibility Platform  
**Version:** 1.0  
**Status:** Schema Baseline / Frozen Documentation  
**Database:** MySQL  
**Backend:** FastAPI  
**OS Reference:** Linux / UNIX Operating System Concepts

---

# 1. Purpose

The OS-DBX database provides the persistent data layer for the complete
OS + DBMS integration platform.

The database stores:

1. Linux operating-system observations
2. Process and thread information
3. System-call and file activity
4. File and permission information
5. CPU, memory and system metrics
6. Operating-system simulations
7. DBMS transactions
8. Transaction operations
9. Query execution information
10. Locks and concurrency information
11. Transaction schedules
12. Recovery logs and checkpoints
13. Cross-layer correlations
14. Detected incidents
15. Performance measurements

The primary objective is to make it possible to connect an OS-level event
with a DBMS-level event.

Example:

    Linux Process
        |
        v
    OS Event
        |
        v
    File/System Activity
        |
        v
    DBMS Transaction
        |
        v
    Transaction Operation
        |
        v
    Lock / Waiting
        |
        v
    Cross-Layer Trace
        |
        v
    Incident / Performance Analysis

---

# 2. Database Design Principles

The database follows these principles:

- Relational database design
- Primary-key based entity identification
- Foreign-key based relationships
- Referential integrity
- Normalized relational structure
- Consistent timestamps
- Linux PID preservation
- Explicit OS and DBMS event separation
- Cross-layer correlation through shared identifiers
- Indexed event and timestamp columns
- MySQL-compatible data types
- FastAPI-compatible relational access

---

# 3. Naming Conventions

The following conventions are used throughout the database:

- Table names use lowercase snake_case.
- Column names use lowercase snake_case.
- Primary keys use the `<entity>_id` pattern.
- Linux process identifiers use `pid`.
- Foreign keys use the referenced entity name followed by `_id`
  wherever an internal database identifier is referenced.
- Event timestamps use `timestamp`.
- Boolean values use BOOLEAN.
- Enumerated states are represented using controlled VARCHAR values
  unless an ENUM is explicitly required.
- All event records should contain enough information to reconstruct
  the sequence of system activity.

---

# 4. Key Identifiers

## 4.1 Internal Database Identifier

The database may use an internal numeric primary key such as:

    process_id
    transaction_id
    event_id

These identify database records.

## 4.2 Linux Process Identifier

`pid` represents the Linux process ID observed by the OS monitoring layer.

The PID is especially important to OS-DBX because it can associate
operating-system activity with DBMS activity.

Example:

    PID 4211
       |
       +---- OS process activity
       |
       +---- OS events
       |
       +---- DBMS transaction
       |
       +---- cross-layer trace

---

# 5. OS / Linux Monitoring Tables

---

# 5.1 users

## Purpose

Stores Linux user information associated with processes and system activity.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| user_id | BIGINT | PK | NO | Internal unique identifier for a user |
| username | VARCHAR(100) | UNIQUE | NO | Linux username |
| uid_linux | INT | UNIQUE | NO | Linux numeric user ID |
| created_at | DATETIME | - | NO | Time when the database record was created |

## Relationships

- One user can own many processes.
- `processes.user_id` references `users.user_id`.

## Source

Linux operating-system monitoring layer.

---

# 5.2 processes

## Purpose

Stores processes observed by the Linux monitoring component.

A process is the main OS-level entity used for connecting operating-system
activity with DBMS activity.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| process_id | BIGINT | PK | NO | Internal process record identifier |
| pid | INT | UNIQUE | NO | Linux process identifier |
| ppid | INT | FK/Self | YES | Parent process PID |
| user_id | BIGINT | FK | YES | User owning the process |
| name | VARCHAR(255) | - | NO | Process name |
| state | VARCHAR(50) | - | YES | Current process state |
| cpu_percent | DECIMAL(6,2) | - | YES | CPU utilization of the process |
| memory_percent | DECIMAL(6,2) | - | YES | Memory utilization of the process |
| start_time | DATETIME | - | YES | Process start time |
| end_time | DATETIME | - | YES | Process termination time |
| created_at | DATETIME | - | NO | Time record was stored |

## Relationships

- Belongs to a user.
- Can reference another process as its parent.
- Can have multiple threads.
- Can generate multiple OS events.
- Can be associated with DBMS transactions.

## Source

Linux process monitoring.

---

# 5.3 threads

## Purpose

Stores thread-level information associated with processes.

Threads allow the platform to represent multithreading behavior and
thread-level operating-system activity.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| thread_id | BIGINT | PK | NO | Internal thread identifier |
| process_id | BIGINT | FK | NO | Process owning the thread |
| tid | INT | UNIQUE | NO | Linux thread identifier |
| name | VARCHAR(255) | YES | YES | Thread name |
| state | VARCHAR(50) | - | YES | Current thread state |
| start_time | DATETIME | - | YES | Thread start time |
| end_time | DATETIME | - | YES | Thread termination time |

## Relationships

- One process can have multiple threads.
- `threads.process_id` references `processes.process_id`.

## Source

Linux process/thread monitoring.

---

# 5.4 system_calls

## Purpose

Stores system-call observations generated by monitored processes.

System calls represent the interface between user-level applications
and the operating system.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| syscall_id | BIGINT | PK | NO | Unique system-call record |
| process_id | BIGINT | FK | NO | Process that issued the system call |
| syscall_name | VARCHAR(100) | NO | NO | Name of the system call |
| syscall_number | INT | - | YES | Numeric Linux system-call identifier |
| arguments | TEXT | - | YES | Serialized system-call arguments |
| return_value | BIGINT | - | YES | System-call return value |
| timestamp | DATETIME | - | NO | Time system call was observed |
| duration_us | BIGINT | - | YES | System-call execution duration in microseconds |

## Examples

Examples of monitored calls include:

    open
    read
    write
    close
    fork
    execve

## Source

Linux OS monitoring layer.

---

# 5.5 os_events

## Purpose

Stores normalized operating-system events.

This table acts as one of the primary event sources for the
Cross-Layer Correlation Engine.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| event_id | BIGINT | PK | NO | Unique OS event identifier |
| process_id | BIGINT | FK | YES | Process associated with the event |
| pid | INT | - | YES | Linux PID associated with the event |
| event_type | VARCHAR(100) | NO | NO | Type of OS event |
| timestamp | DATETIME | NO | NO | Event occurrence time |
| source | VARCHAR(100) | NO | NO | Source of the event |
| file_path | TEXT | YES | YES | File involved in the event if applicable |
| details | JSON | YES | YES | Additional normalized event information |

## Example Event Types

    process_create
    process_terminate
    syscall
    file_open
    file_read
    file_write
    file_close
    permission_change

## Relationships

- Can belong to a process.
- Can be correlated with DBMS events.

---

# 5.6 files

## Purpose

Stores files observed by the Linux file-system monitoring component.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| file_id | BIGINT | PK | NO | Unique file record |
| path | TEXT | UNIQUE | NO | Absolute or normalized file path |
| file_name | VARCHAR(255) | - | YES | File name |
| file_type | VARCHAR(50) | - | YES | File type |
| owner_user_id | BIGINT | FK | YES | Linux owner |
| size_bytes | BIGINT | - | YES | File size |
| created_at | DATETIME | - | YES | File creation time if available |
| modified_at | DATETIME | - | YES | Last modification time |
| accessed_at | DATETIME | - | YES | Last access time |

## Source

Linux file-system monitoring.

---

# 5.7 file_events

## Purpose

Stores file-level operations observed on Linux.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| file_event_id | BIGINT | PK | NO | Unique file event |
| file_id | BIGINT | FK | YES | File involved in the event |
| process_id | BIGINT | FK | YES | Process performing the operation |
| pid | INT | - | YES | Linux PID |
| event_type | VARCHAR(100) | NO | NO | File activity type |
| timestamp | DATETIME | NO | NO | Time of file activity |
| details | JSON | YES | YES | Additional event information |

## Example Event Types

    open
    read
    write
    close
    create
    delete
    rename

---

# 5.8 file_permissions

## Purpose

Stores Linux file permission information required for permission analysis
and security-related monitoring.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| permission_id | BIGINT | PK | NO | Unique permission record |
| file_id | BIGINT | FK | NO | File to which permissions belong |
| owner_user_id | BIGINT | FK | YES | File owner |
| mode_octal | VARCHAR(10) | NO | NO | Unix permission mode such as 0644 |
| owner_permissions | VARCHAR(3) | YES | YES | Owner read/write/execute permissions |
| group_permissions | VARCHAR(3) | YES | YES | Group permissions |
| other_permissions | VARCHAR(3) | YES | YES | Other-user permissions |
| setuid | BOOLEAN | YES | YES | Whether setuid is enabled |
| setgid | BOOLEAN | YES | YES | Whether setgid is enabled |
| sticky_bit | BOOLEAN | YES | YES | Whether sticky bit is enabled |
| captured_at | DATETIME | NO | NO | Time permissions were captured |

---

# 5.9 system_metrics

## Purpose

Stores periodic system-level performance measurements.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| metric_id | BIGINT | PK | NO | Unique metric record |
| timestamp | DATETIME | NO | NO | Measurement time |
| cpu_percent | DECIMAL(6,2) | YES | YES | Overall CPU utilization |
| memory_percent | DECIMAL(6,2) | YES | YES | Overall memory utilization |
| memory_used_bytes | BIGINT | YES | YES | Used memory |
| memory_available_bytes | BIGINT | YES | YES | Available memory |
| disk_read_bytes | BIGINT | YES | YES | Disk bytes read |
| disk_write_bytes | BIGINT | YES | YES | Disk bytes written |
| load_average | DECIMAL(8,3) | YES | YES | System load measurement |

---

# 6. OS Simulation Tables

---

# 6.1 simulations

## Purpose

Stores definitions and metadata for operating-system simulations.

The simulation component demonstrates OS concepts such as scheduling,
memory management, synchronization, deadlock and disk scheduling.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| simulation_id | BIGINT | PK | NO | Unique simulation |
| name | VARCHAR(150) | NO | NO | Simulation name |
| simulation_type | VARCHAR(100) | NO | NO | Type of OS simulation |
| description | TEXT | YES | YES | Simulation description |
| created_at | DATETIME | NO | NO | Creation time |

## Example Types

    cpu_scheduling
    memory_management
    deadlock
    synchronization
    disk_scheduling

---

# 6.2 simulation_runs

## Purpose

Stores individual executions of an OS simulation.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| run_id | BIGINT | PK | NO | Unique simulation run |
| simulation_id | BIGINT | FK | NO | Simulation being executed |
| algorithm | VARCHAR(100) | YES | YES | Algorithm used |
| started_at | DATETIME | NO | NO | Start time |
| completed_at | DATETIME | YES | YES | Completion time |
| status | VARCHAR(50) | NO | NO | Execution status |
| input_data | JSON | YES | YES | Simulation input |
| output_data | JSON | YES | YES | Simulation output |

## Example Algorithms

    FCFS
    SJF
    Round Robin
    LRU
    Banker's Algorithm
    Disk Scheduling Algorithms

---

# 7. DBMS Tables

---

# 7.1 transactions

## Purpose

Stores database transaction lifecycle information.

A transaction represents a logical unit of database work.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| transaction_id | BIGINT | PK | NO | Unique transaction identifier |
| pid | INT | FK/Reference | YES | Linux process associated with transaction |
| transaction_name | VARCHAR(150) | YES | YES | Optional transaction name |
| status | VARCHAR(50) | NO | NO | Current transaction state |
| isolation_level | VARCHAR(50) | YES | YES | Transaction isolation level |
| started_at | DATETIME | NO | NO | Transaction start |
| ended_at | DATETIME | YES | YES | Transaction completion |
| created_at | DATETIME | NO | NO | Record creation time |

## Example Status Values

    ACTIVE
    COMMITTED
    ROLLED_BACK
    ABORTED
    WAITING

## Example Isolation Levels

    READ_UNCOMMITTED
    READ_COMMITTED
    REPEATABLE_READ
    SERIALIZABLE

## Important OS-DBX Relationship

The `pid` field is important because it associates a DBMS transaction
with the Linux process responsible for the database activity.

Example:

    PID 4211
       |
       +---- Linux process
       |
       +---- Transaction T100

---

# 7.2 transaction_operations

## Purpose

Stores individual operations performed within a transaction.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| operation_id | BIGINT | PK | NO | Unique operation identifier |
| transaction_id | BIGINT | FK | NO | Transaction containing the operation |
| operation_order | INT | NO | NO | Sequential order of operation |
| operation_type | VARCHAR(50) | NO | NO | SQL/database operation type |
| table_name | VARCHAR(255) | YES | YES | Table affected |
| record_identifier | VARCHAR(255) | YES | YES | Optional record identifier |
| sql_text | TEXT | YES | YES | SQL statement or normalized representation |
| timestamp | DATETIME | NO | NO | Operation time |
| duration_us | BIGINT | YES | YES | Operation duration |

## Example Operation Types

    SELECT
    INSERT
    UPDATE
    DELETE
    BEGIN
    COMMIT
    ROLLBACK

---

# 7.3 query_executions

## Purpose

Stores query execution information for DBMS performance analysis.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| query_id | BIGINT | PK | NO | Unique query execution record |
| transaction_id | BIGINT | FK | YES | Transaction executing the query |
| pid | INT | YES | YES | Linux PID associated with execution |
| query_text | TEXT | NO | NO | SQL query |
| query_type | VARCHAR(50) | YES | YES | Query category |
| started_at | DATETIME | NO | NO | Query start time |
| completed_at | DATETIME | YES | YES | Query completion time |
| duration_us | BIGINT | YES | YES | Query duration |
| rows_affected | BIGINT | YES | YES | Number of affected rows |
| status | VARCHAR(50) | YES | YES | Query execution result |

---

# 7.4 locks

## Purpose

Stores database lock information required for concurrency analysis,
lock monitoring and deadlock detection.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| lock_id | BIGINT | PK | NO | Unique lock identifier |
| transaction_id | BIGINT | FK | NO | Transaction owning/requesting the lock |
| resource_type | VARCHAR(50) | NO | NO | Type of resource being locked |
| resource_identifier | VARCHAR(255) | NO | NO | Identifier of locked resource |
| lock_type | VARCHAR(20) | NO | NO | Shared or exclusive lock |
| lock_status | VARCHAR(30) | NO | NO | Granted or waiting |
| acquired_at | DATETIME | YES | YES | Lock acquisition time |
| released_at | DATETIME | YES | YES | Lock release time |

## Example Lock Types

    SHARED
    EXCLUSIVE

## Example Status

    GRANTED
    WAITING
    RELEASED

---

# 7.5 schedules

## Purpose

Represents schedules consisting of operations from multiple transactions.

Schedules are used for concurrency and serializability analysis.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| schedule_id | BIGINT | PK | NO | Unique schedule |
| name | VARCHAR(150) | YES | YES | Schedule name |
| schedule_type | VARCHAR(50) | YES | YES | Serial or concurrent schedule |
| created_at | DATETIME | NO | NO | Creation time |
| status | VARCHAR(50) | YES | YES | Schedule analysis status |

---

# 7.6 schedule_operations

## Purpose

Stores the ordered operations belonging to a schedule.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| schedule_operation_id | BIGINT | PK | NO | Unique schedule operation |
| schedule_id | BIGINT | FK | NO | Parent schedule |
| transaction_id | BIGINT | FK | NO | Transaction performing operation |
| operation_id | BIGINT | FK | YES | Corresponding transaction operation |
| sequence_number | INT | NO | NO | Position in schedule |
| operation_type | VARCHAR(50) | NO | NO | Operation type |
| resource_identifier | VARCHAR(255) | YES | YES | Resource accessed |

## Use

This table supports:

- Conflict analysis
- Precedence graph construction
- Serializability analysis
- Concurrent schedule visualization

---

# 7.7 recovery_logs

## Purpose

Stores transaction recovery log records.

These records support analysis of crash recovery, UNDO and REDO behavior.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| log_id | BIGINT | PK | NO | Unique recovery log record |
| transaction_id | BIGINT | FK | YES | Associated transaction |
| log_type | VARCHAR(50) | NO | NO | Type of log record |
| operation_id | BIGINT | FK | YES | Related transaction operation |
| old_value | TEXT | YES | YES | Previous value for recovery |
| new_value | TEXT | YES | YES | New value for recovery |
| timestamp | DATETIME | NO | NO | Log creation time |
| lsn | BIGINT | UNIQUE | YES | Log sequence number |

## Example Log Types

    BEGIN
    UPDATE
    INSERT
    DELETE
    COMMIT
    ROLLBACK
    CHECKPOINT

---

# 7.8 checkpoints

## Purpose

Stores database recovery checkpoints.

Checkpoints reduce the amount of log information that must be examined
during recovery.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| checkpoint_id | BIGINT | PK | NO | Unique checkpoint |
| lsn | BIGINT | YES | YES | Log sequence number at checkpoint |
| timestamp | DATETIME | NO | NO | Checkpoint time |
| active_transactions | JSON | YES | YES | Transactions active at checkpoint |
| status | VARCHAR(50) | YES | YES | Checkpoint status |

---

# 8. Cross-Layer Integration Tables

These tables represent the main innovation of OS-DBX.

They connect operating-system activity with DBMS activity.

---

# 8.1 cross_layer_traces

## Purpose

Represents an end-to-end trace connecting OS-level and DBMS-level activity.

Example:

    PID 4211
       |
       v
    FILE_WRITE
       |
       v
    Transaction T100
       |
       v
    UPDATE
       |
       v
    LOCK
       |
       v
    COMMIT

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| trace_id | BIGINT | PK | NO | Unique cross-layer trace |
| pid | INT | YES | YES | Linux PID involved |
| transaction_id | BIGINT | FK | YES | DBMS transaction involved |
| start_timestamp | DATETIME | NO | NO | Trace beginning |
| end_timestamp | DATETIME | YES | YES | Trace completion |
| trace_status | VARCHAR(50) | NO | NO | Trace status |
| correlation_method | VARCHAR(100) | YES | YES | Method used to correlate events |
| confidence_score | DECIMAL(5,2) | YES | YES | Correlation confidence/strength |
| summary | TEXT | YES | YES | Human-readable trace summary |

## Purpose in OS-DBX

This is one of the primary tables through which the platform exposes
cross-layer relationships.

---

# 8.2 event_correlations

## Purpose

Stores relationships between individual OS events and DBMS events.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| correlation_id | BIGINT | PK | NO | Unique correlation |
| os_event_id | BIGINT | FK | YES | Associated OS event |
| transaction_id | BIGINT | FK | YES | Associated DBMS transaction |
| operation_id | BIGINT | FK | YES | Associated transaction operation |
| correlation_type | VARCHAR(100) | NO | NO | Type of relationship |
| timestamp | DATETIME | NO | NO | Correlation creation time |
| reason | TEXT | YES | YES | Explanation for correlation |

## Example Correlation Types

    PID_MATCH
    TEMPORAL_MATCH
    FILE_MATCH
    RESOURCE_MATCH
    PROCESS_TRANSACTION_MATCH

---

# 8.3 incidents

## Purpose

Stores problems detected from correlated OS and DBMS behavior.

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| incident_id | BIGINT | PK | NO | Unique incident |
| trace_id | BIGINT | FK | YES | Related cross-layer trace |
| incident_type | VARCHAR(100) | NO | NO | Type of detected problem |
| severity | VARCHAR(30) | NO | NO | Severity level |
| detected_at | DATETIME | NO | NO | Detection time |
| resolved_at | DATETIME | YES | YES | Resolution time |
| status | VARCHAR(50) | NO | NO | Incident state |
| root_cause | TEXT | YES | YES | Identified root cause |
| description | TEXT | YES | YES | Incident explanation |

## Example Incident Types

    DEADLOCK
    LONG_TRANSACTION
    HIGH_IO
    HIGH_CPU
    PERMISSION_ANOMALY
    SLOW_QUERY
    RESOURCE_CONTENTION

---

# 8.4 performance_records

## Purpose

Stores performance measurements that can be associated with OS and
DBMS behavior.

This enables comparisons such as:

    OS CPU utilization
             vs
    Query execution time

or:

    File I/O activity
             vs
    Transaction latency

## Columns

| Column | Data Type | Key | Nullable | Description |
|---|---|---|---|---|
| performance_id | BIGINT | PK | NO | Unique performance record |
| trace_id | BIGINT | FK | YES | Related cross-layer trace |
| pid | INT | YES | YES | Linux PID |
| transaction_id | BIGINT | FK | YES | Related transaction |
| timestamp | DATETIME | NO | NO | Measurement time |
| cpu_percent | DECIMAL(6,2) | YES | YES | CPU utilization |
| memory_percent | DECIMAL(6,2) | YES | YES | Memory utilization |
| io_read_bytes | BIGINT | YES | YES | Read I/O |
| io_write_bytes | BIGINT | YES | YES | Write I/O |
| query_time_us | BIGINT | YES | YES | Query execution time |
| transaction_time_us | BIGINT | YES | YES | Transaction duration |
| lock_wait_us | BIGINT | YES | YES | Lock waiting duration |

---

# 9. Relationship Summary

The main relationships of the database are:

    users
      |
      +----< processes
                 |
                 +----< threads
                 |
                 +----< system_calls
                 |
                 +----< os_events
                 |
                 +----< file_events
                 |
                 +----< transactions
                              |
                              +----< transaction_operations
                              |
                              +----< query_executions
                              |
                              +----< locks
                              |
                              +----< recovery_logs

    files
      |
      +----< file_events
      |
      +----< file_permissions

    simulations
      |
      +----< simulation_runs

    schedules
      |
      +----< schedule_operations
                    |
                    +---- transactions

    checkpoints
      |
      +---- recovery information

    os_events
      |
      +----< event_correlations
                    |
                    +---- transactions
                    |
                    +---- transaction_operations

    transactions
      |
      +----< cross_layer_traces
                    |
                    +----< incidents
                    |
                    +----< performance_records

---

# 10. Cross-Layer Correlation Concept

The database is designed around the following logical chain:

    Linux Process
          |
          | PID
          v
    OS Event
          |
          | temporal/resource relationship
          v
    Transaction
          |
          v
    Transaction Operation
          |
          v
    Lock
          |
          v
    Waiting / Contention
          |
          v
    Cross-Layer Trace
          |
          +---- Incident
          |
          +---- Performance Record

The PID is an important bridge between the operating-system layer
and the database layer.

---

# 11. Example End-to-End Scenario

Consider an online shopping application.

A user clicks:

    "Buy Laptop"

The application runs as Linux process:

    PID = 4211

The process accesses a database file and executes a database transaction.

The DBMS records:

    Transaction = T100

The transaction performs:

    UPDATE inventory
    UPDATE orders

Another transaction is already holding a lock.

The second transaction waits.

The OS-DBX platform can represent:

    Process P4211
        |
        v
    File/System Activity
        |
        v
    Transaction T100
        |
        v
    UPDATE inventory
        |
        v
    Lock
        |
        v
    Waiting
        |
        v
    Cross-Layer Trace
        |
        v
    Possible contention/deadlock incident

This allows the platform to explain a DBMS problem using
operating-system context.

---

# 12. Database Layer Responsibilities

The database is responsible for:

- Persistent storage
- Referential integrity
- Transaction metadata
- OS event storage
- DBMS event storage
- Simulation results
- Recovery information
- Correlation results
- Incident history
- Performance history

The database does NOT directly replace the Linux kernel.

The Linux monitoring layer observes OS behavior and sends normalized
information to the backend/database.

---

# 13. FastAPI Interaction

React must never directly connect to MySQL.

The intended architecture is:

    React
      |
      | HTTP/REST
      v
    FastAPI
      |
      | SQL / ORM
      v
    MySQL

FastAPI exposes controlled API endpoints for:

- Processes
- OS events
- Transactions
- Queries
- Locks
- Recovery
- Cross-layer traces
- Incidents
- Performance information

---

# 14. Data Flow

The expected data flow is:

    Linux / OS
        |
        v
    Event Collector
        |
        v
    Event Normalizer
        |
        v
    FastAPI
        |
        v
    MySQL
        |
        v
    Cross-Layer Correlation
        |
        v
    FastAPI REST API
        |
        v
    React Dashboard

DBMS information follows a similar path:

    DBMS Event
        |
        v
    Normalization
        |
        v
    MySQL
        |
        v
    Cross-Layer Correlation

---

# 15. Integrity Requirements

The database implementation should enforce:

- Primary keys
- Foreign keys
- NOT NULL constraints where required
- UNIQUE constraints where required
- Referential integrity
- Appropriate indexes
- Valid status values
- Valid event types
- Consistent timestamps
- Consistent PID usage

---

# 16. Indexing Requirements

High-frequency fields should be considered for indexing.

Important candidates include:

    processes.pid
    os_events.pid
    os_events.timestamp
    os_events.event_type
    file_events.pid
    file_events.timestamp
    transactions.pid
    transactions.status
    transaction_operations.transaction_id
    locks.transaction_id
    locks.lock_status
    cross_layer_traces.pid
    cross_layer_traces.transaction_id
    event_correlations.os_event_id

Actual indexes should be finalized during SQL implementation and
performance testing.

---

# 17. Security Considerations

The database should:

- Avoid storing unnecessary sensitive information.
- Use parameterized queries.
- Prevent SQL injection through the API layer.
- Keep database credentials outside source code.
- Use environment variables for credentials.
- Restrict database privileges.
- Avoid exposing raw database credentials to React.
- Validate API input before database operations.

---

# 18. Schema Change Policy

The ER diagram is treated as the structural source of truth.

A schema change should follow:

    Proposed Change
          |
          v
    ERD Update
          |
          v
    Team Review
          |
          v
    Data Dictionary Update
          |
          v
    Relational Schema Update
          |
          v
    SQL Migration
          |
          v
    Testing
          |
          v
    FastAPI Update

No major database change should be silently made only in SQL.

---

# 19. Final Database Objective

The database should allow OS-DBX to answer questions such as:

1. Which Linux process generated this activity?
2. Which OS event occurred before the database operation?
3. Which transaction was executing?
4. Which SQL operation was performed?
5. Which resource was locked?
6. Was another transaction waiting?
7. Did the situation lead to a deadlock?
8. How long did the transaction take?
9. What was CPU/memory/I/O utilization at that time?
10. What recovery information is available?
11. What is the complete cross-layer trace?

This cross-layer visibility is the primary database-level objective
of OS-DBX.