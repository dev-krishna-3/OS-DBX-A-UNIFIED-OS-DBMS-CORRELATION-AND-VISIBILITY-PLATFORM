2. The three levels you need

For your PBL, focus on:

1NF
 ↓
2NF
 ↓
3NF

Think of them as three questions.

1NF

"Is every cell storing one proper value?"

2NF

"Does every attribute depend on the complete primary key?"

3NF

"Are non-key attributes depending only on the primary key, rather than on another non-key attribute?"

3. 1NF — First Normal Form

A table is in 1NF when each cell contains an atomic/single value.

Bad example
PROCESS

process_id | pid  | syscalls
-----------|------|----------------------
1          | 4211 | open, read, write

syscalls contains multiple values.

That's bad for a relational table.

Better

Create separate records:

SYSTEM_CALLS

syscall_id | process_id | syscall_name
-----------|------------|-------------
1          | 1          | open
2          | 1          | read
3          | 1          | write

Now each cell contains one value.

Your schema already follows this approach.

4. 2NF — Second Normal Form

2NF mainly matters when a table has a composite primary key.

For example:

ENROLLMENT

student_id
course_id
student_name
course_name
marks

Suppose the primary key is:

(student_id, course_id)

But:

student_id → student_name
course_id → course_name

Those attributes don't depend on the whole key.

So we split:

STUDENTS
student_id
student_name

COURSES
course_id
course_name

ENROLLMENT
student_id
course_id
marks

Now the dependency is cleaner.

5. Your project and 2NF

Your tables mostly use single-column primary keys:

users.user_id
processes.process_id
threads.thread_id
system_calls.syscall_id
os_events.event_id
transactions.transaction_id

Therefore, partial dependency is generally not an issue.

For example:

THREADS

thread_id       PK
process_id      FK
tid
state
created_at

Every non-key attribute describes the thread identified by thread_id.

So this table is fine with respect to 2NF.

6. 3NF — Third Normal Form

This is the most useful one to explain to your mentor.

Suppose:

PROCESSES

process_id
pid
user_id
username
uid_linux

You could have:

process_id → user_id
user_id → username
user_id → uid_linux

Therefore:

process_id → user_id → username
                       uid_linux

username and uid_linux don't really belong in PROCESSES.

They belong in USERS.

So:

USERS
----------------
user_id PK
username
uid_linux

and:

PROCESSES
----------------
process_id PK
pid
user_id FK
name
state
...

Now:

USERS
  ↑
  |
user_id
  |
PROCESSES

That's a good normalization decision.

7. Let's normalize your actual tables

Now we can go through your OS-DBX schema.

USERS
USERS
--------------------
user_id PK
username
uid_linux
created_at

Dependency:

user_id → username
user_id → uid_linux
user_id → created_at

No obvious transitive dependency.

Result
3NF ✅
8. PROCESSES

Your structure:

PROCESSES
--------------------
process_id PK
pid
ppid
user_id FK
name
state
cpu_percent
memory_percent
start_time
end_time
created_at

Dependencies conceptually:

process_id → pid
process_id → user_id
process_id → name
process_id → state
process_id → cpu_percent
process_id → memory_percent
...

User details aren't duplicated.

Result
3NF ✅
9. THREADS

Your finalized table:

THREADS
--------------------
thread_id PK
process_id FK
tid
state
created_at

Dependency:

thread_id → process_id
thread_id → tid
thread_id → state
thread_id → created_at

No obvious unnecessary dependency.

Result
3NF ✅

And your SQL:

CREATE TABLE threads (
    thread_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    process_id BIGINT NOT NULL,
    tid BIGINT NOT NULL UNIQUE,
    state VARCHAR(50),
    created_at DATETIME,

    CONSTRAINT fk_thread_process
        FOREIGN KEY (process_id)
        REFERENCES processes(process_id)
);

is consistent with that design.

10. SYSTEM_CALLS
SYSTEM_CALLS
--------------------
syscall_id PK
process_id FK
syscall_name
syscall_number
arguments
return_value
timestamp
duration_us

Each system-call record describes one system-call occurrence.

You aren't storing:

process_name
username

again.

Result
3NF ✅
11. OS_EVENTS
OS_EVENTS
--------------------
event_id PK
process_id FK
pid
event_type
timestamp
source
file_path
details

This one deserves a small discussion.

You have both:

process_id
pid

Why?

Because process_id is the relational FK, while pid represents the Linux PID captured in the event and is useful for correlation with the OS collector/DBMS layer.

So don't remove it automatically just because it looks duplicated.

Document its purpose:

process_id → relational relationship
pid        → Linux/cross-layer correlation identifier
Result
3NF: acceptable for the project's event/correlation requirements
12. FILES
FILES
--------------------
file_id PK
path
file_name
file_type
owner_user_id FK
size_bytes
created_at
modified_at
accessed_at

User information isn't duplicated.

Instead:

FILES.owner_user_id
        ↓
USERS.user_id
Result
3NF ✅
13. FILE_EVENTS
FILE_EVENTS
--------------------
file_event_id PK
file_id FK
process_id FK
pid
event_type
timestamp
details

Each row represents one event.

It doesn't duplicate complete process/file information.

Result
3NF ✅
14. FILE_PERMISSIONS
FILE_PERMISSIONS
--------------------
permission_id PK
file_id FK
owner_user_id FK
mode_octal
owner_permissions
group_permissions
other_permissions
setuid
setgid
sticky_bit
captured_at

The file itself is referenced using:

file_id

and owner using:

owner_user_id

So you don't need to repeat the entire file/user information.

Result
3NF ✅
15. SYSTEM_METRICS
SYSTEM_METRICS
--------------------
metric_id PK
timestamp
cpu_percent
memory_percent
memory_used_bytes
memory_available_bytes
disk_read_bytes
disk_write_bytes
load_average

Each record represents a system measurement at a point in time.

Result
3NF ✅
16. TRANSACTIONS
TRANSACTIONS
--------------------
transaction_id PK
pid
transaction_name
status
isolation_level
started_at
ended_at
created_at

Transaction-specific information stays here.

Individual operations aren't stored as repeating columns.

Instead:

TRANSACTIONS
      ↓
TRANSACTION_OPERATIONS
Result
3NF ✅
17. TRANSACTION_OPERATIONS
TRANSACTION_OPERATIONS
--------------------
operation_id PK
transaction_id FK
operation_order
operation_type
table_name
record_identifier
sql_text
timestamp
duration_us

Each operation belongs to a transaction.

You aren't doing something like:

operation1
operation2
operation3
operation4

inside the transaction row.

That's good normalization.

Result
3NF ✅
18. LOCKS
LOCKS
--------------------
lock_id PK
transaction_id FK
resource_type
resource_identifier
lock_type
lock_status
acquired_at
released_at

Lock information is separated from transactions.

Therefore:

TRANSACTIONS
     ↓
    LOCKS
Result
3NF ✅
19. SCHEDULES
SCHEDULES
--------------------
schedule_id PK
name
schedule_type
created_at
status

and:

SCHEDULE_OPERATIONS
--------------------
schedule_operation_id PK
schedule_id FK
transaction_id FK
operation_id FK
sequence_number
operation_type
resource_identifier

This is a good separation between:

Schedule

and:

Operations belonging to schedule
Result
3NF ✅
20. RECOVERY_LOGS
RECOVERY_LOGS
--------------------
log_id PK
transaction_id FK
log_type
operation_id FK
old_value
new_value
timestamp
lsn

Recovery records are separated from transactions and operations.

Result
3NF ✅
21. CHECKPOINTS
CHECKPOINTS
--------------------
checkpoint_id PK
lsn
timestamp
active_transactions
status

One thing to notice:

active_transactions may be a serialized representation/list depending on your implementation.

If it contains multiple transaction IDs in one field, that would violate strict 1NF.

For example:

active_transactions = "101,102,103"

would not be ideal in a normalized relational schema.

If you actually need to query individual active transactions at checkpoints, we'd create a separate relation such as:

CHECKPOINT_TRANSACTIONS
-----------------------
checkpoint_id FK
transaction_id FK

However, don't change your frozen ER diagram without discussing it with the team. If active_transactions is simply stored as a snapshot/payload for recovery simulation, you can document that decision.

22. CROSS_LAYER_TRACES
CROSS_LAYER_TRACES
--------------------
trace_id PK
pid
transaction_id FK
start_timestamp
end_timestamp
trace_status
correlation_method
confidence_score
summary

This is an integration entity.

The important thing is that you're not copying all OS and DBMS information into it.

Instead:

transaction_id → TRANSACTIONS
pid            → Linux identity
Result
3NF / integration-oriented design ✅
23. EVENT_CORRELATIONS

This is particularly important.

EVENT_CORRELATIONS
--------------------
correlation_id PK
os_event_id FK
transaction_id FK
operation_id FK
correlation_type
timestamp
reason

Instead of copying the entire OS event and transaction into one huge table, you reference them.

OS_EVENTS
    ↑
    |
EVENT_CORRELATIONS
    |
    +────→ TRANSACTIONS
    |
    +────→ TRANSACTION_OPERATIONS

That's exactly the kind of separation normalization encourages.

24. INCIDENTS
INCIDENTS
--------------------
incident_id PK
trace_id FK
incident_type
severity
detected_at
resolved_at
status
root_cause
description

Incident information belongs to the incident.

The trace is referenced:

trace_id → CROSS_LAYER_TRACES
Result
3NF ✅
25. PERFORMANCE_RECORDS
PERFORMANCE_RECORDS
--------------------
performance_id PK
trace_id FK
pid
transaction_id FK
timestamp
cpu_percent
memory_percent
io_read_bytes
io_write_bytes
query_time_us
transaction_time_us
lock_wait_us

This table represents a performance observation associated with a trace.

Result
3NF / analytical event design ✅