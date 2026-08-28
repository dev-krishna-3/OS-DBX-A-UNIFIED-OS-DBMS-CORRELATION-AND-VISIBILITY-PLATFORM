-- ============================================================
-- OS-DBX SEED DATA
-- Sample/Test Data
-- ============================================================


-- ============================================================
-- 1. USERS
-- ============================================================

INSERT INTO users (
    username,
    uid_linux
)
VALUES (
    'testuser',
    1001
);


-- ============================================================
-- 2. PROCESSES
-- ============================================================

INSERT INTO processes (
    pid,
    ppid,
    user_id,
    name,
    state,
    cpu_percent,
    memory_percent,
    start_time,
    end_time
)
VALUES (
    4211,
    NULL,
    1,
    'test_process',
    'RUNNING',
    5.20,
    10.40,
    NOW(),
    NULL
);


-- ============================================================
-- 3. THREADS
-- ============================================================

INSERT INTO threads (
    process_id,
    tid,
    state,
    created_at
)
VALUES
(
    1,
    4212,
    'RUNNING',
    NOW()
),
(
    1,
    4213,
    'SLEEPING',
    NOW()
),
(
    1,
    4214,
    'WAITING',
    NOW()
);


-- ============================================================
-- 4. SYSTEM CALLS
-- ============================================================

INSERT INTO system_calls (
    process_id,
    syscall_name,
    arguments,
    return_value,
    timestamp
)
VALUES
(
    1,
    'open',
    '/tmp/test.txt',
    '3',
    NOW()
),
(
    1,
    'read',
    'fd=3,count=100',
    '100',
    NOW()
),
(
    1,
    'write',
    'fd=3,count=50',
    '50',
    NOW()
),
(
    1,
    'close',
    'fd=3',
    '0',
    NOW()
);


-- ============================================================
-- 5. OS EVENTS
-- ============================================================

INSERT INTO os_events (
    pid,
    event_type,
    file_path,
    timestamp,
    details
)
VALUES
(
    17192,
     'process_created',
    'C:\\Windows\\System32\\dllhost.exe',
    '2026-08-27 10:22:51',
    '{"ppid":1780,"user":"LAPTOP-GP6CB324\\\\adity"}'
),
(
    1488,
    'process_created',
    'C:\\Windows\\System32\\svchost.exe',
    '2026-08-27 10:22:53',
    '{"ppid":1588,"user":null}'
),
(
    21316,
    'process_created',
    'C:\\Windows\\System32\\svchost.exe',
    '2026-08-27 10:22:53',
    '{"ppid":1588,"user":null}'
),
(
    10784,
    'process_created',
    'C:\\Windows\\System32\\DataExchangeHost.exe',
    '2026-08-27 10:22:56',
    '{"ppid":1780,"user":"LAPTOP-GP6CB324\\\\adity"}'
),
(
    2088,
    'process_terminated',
    'C:\\Windows\\System32\\wbem\\WmiPrvSE.exe',
    '2026-08-27 10:22:56',
    '{"ppid":1780,"user":null}'
),
(
    17192,
    'process_terminated',
    'C:\\Windows\\System32\\dllhost.exe',
    '2026-08-27 10:22:58',
    '{"ppid":1780,"user":"LAPTOP-GP6CB324\\\\adity"}'
),
(
    12600,
    'process_created',
    'C:\\Program Files\\Microsoft OneDrive\\26.145.0728.0011\\FileCoAuth.exe',
    '2026-08-27 10:23:08',
    '{"ppid":1780,"user":"LAPTOP-GP6CB324\\\\adity"}'
),
(
    12336,
    'process_created',
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    '2026-08-27 10:23:13',
    '{"ppid":22196,"user":"LAPTOP-GP6CB324\\\\adity"}'
),
(
    10016,
    'process_terminated',
    'C:\\Program Files\\WindowsApps\\microsoft.windowsnotepad_11.2606.15.0_x64__8wekyb3d8bbwe\\Notepad\\Notepad.exe',
    '2026-08-27 10:23:13',
    '{"ppid":19096,"user":"LAPTOP-GP6CB324\\\\adity"}'
),
(
    5348,
    'process_terminated',
    'C:\\Program Files (x86)\\Microsoft\\EdgeWebView\\Application\\151.0.4129.107\\msedgewebview2.exe',
    '2026-08-27 10:23:16',
    '{"ppid":21812,"user":"LAPTOP-GP6CB324\\\\adity"}'
),
(
    12600,
    'process_terminated',
    'C:\\Program Files\\Microsoft OneDrive\\26.145.0728.0011\\FileCoAuth.exe',
    '2026-08-27 10:23:16',
    '{"ppid":1780,"user":"LAPTOP-GP6CB324\\\\adity"}'
),
(
    11912,
    'process_created',
    'C:\\Program Files (x86)\\Microsoft\\EdgeWebView\\Application\\151.0.4129.107\\msedgewebview2.exe',
    '2026-08-27 10:23:21',
    '{"ppid":21812,"user":"LAPTOP-GP6CB324\\\\adity"}'
),
(
    10784,
    'process_terminated',
    'C:\\Windows\\System32\\DataExchangeHost.exe',
    '2026-08-27 10:23:26',
    '{"ppid":1780,"user":"LAPTOP-GP6CB324\\\\adity"}'
);


-- ============================================================
-- 6. RESOURCE METRICS
-- ============================================================

INSERT INTO resource_metrics (
    process_id,
    cpu_usage,
    memory_usage,
    disk_io,
    network_io,
    recorded_at
)
VALUES
(
    1,
    10.20,
    30.50,
    100.00,
    40.00,
    NOW()
),
(
    1,
    15.70,
    32.10,
    150.50,
    48.30,
    NOW()
),
(
    1,
    20.40,
    38.60,
    180.20,
    52.70,
    NOW()
);


-- ============================================================
-- 7. FILES
-- ============================================================

INSERT INTO files (
    file_path,
    owner_id,
    permissions,
    size_bytes
)
VALUES
(
    '/tmp/test.txt',
    1,
    '644',
    1024
),
(
    '/home/testuser/data.txt',
    1,
    '644',
    2048
),
(
    '/home/testuser/script.sh',
    1,
    '755',
    4096
),
(
    '/tmp/config.conf',
    1,
    '600',
    512
);


-- ============================================================
-- 8. DIRECTORIES
-- ============================================================

-- Root directory

INSERT INTO directories (
    parent_directory_id,
    path
)
VALUES (
    NULL,
    '/'
);

-- /home and /tmp

INSERT INTO directories (
    parent_directory_id,
    path
)
VALUES
(
    1,
    '/home'
),
(
    1,
    '/tmp'
);

-- /home/testuser and /home/projects

INSERT INTO directories (
    parent_directory_id,
    path
)
VALUES
(
    2,
    '/home/testuser'
),
(
    2,
    '/home/projects'
);

-- /home/testuser/docs

INSERT INTO directories (
    parent_directory_id,
    path
)
VALUES (
    4,
    '/home/testuser/docs'
);


-- ============================================================
-- 9. PERMISSIONS
-- ============================================================

INSERT INTO permissions (
    file_id,
    user_id,
    access_type,
    granted_at
)
VALUES
(
    1,
    1,
    'READ',
    NOW()
),
(
    2,
    1,
    'WRITE',
    NOW()
),
(
    3,
    1,
    'EXECUTE',
    NOW()
),
(
    4,
    1,
    'READ',
    NOW()
);


-- ============================================================
-- 10. SIMULATIONS
-- ============================================================

INSERT INTO simulations (
    type,
    algorithm,
    created_by,
    created_at,
    status
)
VALUES (
    'CPU Scheduling',
    'FCFS',
    1,
    NOW(),
    'COMPLETED'
);


-- ============================================================
-- 11. SCHEDULED PROCESSES
-- ============================================================

INSERT INTO scheduled_processes (
    simulation_id,
    process_label,
    arrival_time,
    burst_time,
    priority,
    waiting_time,
    turnaround_time,
    completion_time
)
VALUES
(
    1,
    'P1',
    0,
    5,
    1,
    0,
    5,
    5
),
(
    1,
    'P2',
    1,
    3,
    2,
    4,
    7,
    8
),
(
    1,
    'P3',
    2,
    8,
    3,
    6,
    14,
    16
);


-- ============================================================
-- 12. MEMORY EXPERIMENTS
-- ============================================================

INSERT INTO memory_experiments (
    simulation_id,
    algorithm,
    frame_count,
    result_summary
)
VALUES (
    1,
    'FIFO',
    3,
    'FIFO page replacement completed successfully'
);


-- ============================================================
-- 13. PAGE REFERENCES
-- ============================================================

INSERT INTO page_references (
    experiment_id,
    page_number,
    sequence_order,
    fault_occurred
)
VALUES
(
    1,
    1,
    1,
    TRUE
),
(
    1,
    2,
    2,
    TRUE
),
(
    1,
    3,
    3,
    TRUE
),
(
    1,
    1,
    4,
    FALSE
),
(
    1,
    4,
    5,
    TRUE
),
(
    1,
    2,
    6,
    TRUE
);


-- ============================================================
-- 14. DISK REQUESTS
-- ============================================================

INSERT INTO disk_requests (
    simulation_id,
    track_number,
    sequence_order,
    seek_time
)
VALUES
(
    1,
    98,
    1,
    20
),
(
    1,
    183,
    2,
    85
),
(
    1,
    37,
    3,
    146
),
(
    1,
    122,
    4,
    108
),
(
    1,
    14,
    5,
    94
);


-- ============================================================
-- 15. DEADLOCK EXPERIMENTS
-- ============================================================

INSERT INTO deadlock_experiments (
    simulation_id,
    algorithm,
    deadlock_detected,
    cycle_path
)
VALUES (
    1,
    'Bankers Algorithm',
    TRUE,
    'P1 -> P2 -> P1'
);


-- ============================================================
-- 16. SYNCHRONIZATION EXPERIMENTS
-- ============================================================

INSERT INTO synchronization_experiments (
    simulation_id,
    problem_type,
    result_log
)
VALUES (
    1,
    'Producer-Consumer',
    'Producer and consumer synchronization completed successfully'
);