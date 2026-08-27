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
VALUES
    ('testuser', 1001);


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
VALUES
    (
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
        4211,
        'file_open',
        '/tmp/test.txt',
        NOW(),
        'Process opened file'
    ),
    (
        4211,
        'file_read',
        '/tmp/test.txt',
        NOW(),
        'Process read file'
    ),
    (
        4211,
        'file_write',
        '/tmp/test.txt',
        NOW(),
        'Process modified file'
    ),
    (
        4211,
        'file_close',
        '/tmp/test.txt',
        NOW(),
        'Process closed file'
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

INSERT INTO directories (
    parent_id,
    path,
    owner_id,
    permissions
)
VALUES
    (
        NULL,
        '/',
        1,
        '755'
    );

INSERT INTO directories (
    parent_id,
    path,
    owner_id,
    permissions
)
VALUES
    (
        1,
        '/home',
        1,
        '755'
    ),
    (
        1,
        '/tmp',
        1,
        '777'
    );

INSERT INTO directories (
    parent_id,
    path,
    owner_id,
    permissions
)
VALUES
    (
        2,
        '/home/testuser',
        1,
        '700'
    );

INSERT INTO permissions (
    file_id,
    user_id,
    access_type,
    granted_at
)
VALUES
    (1, 1, 'READ', NOW()),
    (2, 1, 'WRITE', NOW()),
    (3, 1, 'EXECUTE', NOW()),
    (4, 1, 'READ', NOW());

    INSERT INTO os_events (
    pid,
    ppid,
    user,
    event_type,
    file_path,
    timestamp,
    details
)
VALUES (
    17192,
    1780,
    'LAPTOP-GP6CB324\\adity',
    'process_created',
    'C:\\Windows\\System32\\dllhost.exe',
    '2026-08-27 10:22:51',
    NULL
);

INSERT INTO os_events (
    pid,
    ppid,
    user,
    event_type,
    file_path,
    timestamp,
    details
)
VALUES (
    1488,
    1588,
    NULL,
    'process_created',
    'C:\\Windows\\System32\\svchost.exe',
    '2026-08-27 10:22:53',
    NULL
);