-- One-time migration. Take and verify a database backup before applying.
-- Existing records are intentionally assigned to a private admin-only legacy workspace.

INSERT INTO workspaces (workspace_id, name, is_legacy, created_by)
VALUES (1, 'Legacy records (admin only)', TRUE, NULL);

INSERT INTO devices (
    device_id, workspace_id, host_id, display_name, operating_system,
    collection_scope, retention_days, status
) VALUES (
    '00000000-0000-0000-0000-000000000001', 1, 'legacy', 'Legacy records', 'unknown',
    JSON_OBJECT('mode', 'legacy-admin-only'), 0, 'offline'
);

ALTER TABLE processes
    ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1,
    ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    ADD COLUMN process_started_at DATETIME(6) NULL,
    ADD KEY idx_process_workspace_device_pid (workspace_id, device_id, pid);

ALTER TABLE threads
    ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1,
    ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    ADD KEY idx_threads_workspace_device (workspace_id, device_id);
ALTER TABLE system_calls
    ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1,
    ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    ADD KEY idx_syscalls_workspace_device (workspace_id, device_id);
ALTER TABLE os_events
    ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1,
    ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    ADD COLUMN source_event_id CHAR(36) NULL,
    ADD COLUMN received_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    ADD COLUMN source_sequence BIGINT UNSIGNED NULL,
    ADD UNIQUE KEY uq_os_event_device_source (device_id, source_event_id),
    ADD KEY idx_os_event_workspace_device_time (workspace_id, device_id, timestamp);
ALTER TABLE resource_metrics
    ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1,
    ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    ADD KEY idx_resource_workspace_device (workspace_id, device_id, recorded_at);
ALTER TABLE files
    ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1,
    ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    DROP INDEX uq_files_path,
    ADD UNIQUE KEY uq_files_device_path (device_id, file_path(255)),
    ADD KEY idx_files_workspace_device (workspace_id, device_id);
ALTER TABLE directories
    ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1,
    ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    DROP INDEX uq_directories_path,
    ADD UNIQUE KEY uq_directories_device_path (device_id, path(255)),
    ADD KEY idx_directories_workspace_device (workspace_id, device_id);
ALTER TABLE permissions
    ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1,
    ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    ADD KEY idx_permissions_workspace_device (workspace_id, device_id);

ALTER TABLE simulations ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_simulations_workspace_device (workspace_id, device_id);
ALTER TABLE scheduled_processes ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_scheduled_workspace_device (workspace_id, device_id);
ALTER TABLE memory_experiments ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_memory_workspace_device (workspace_id, device_id);
ALTER TABLE page_references ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_page_refs_workspace_device (workspace_id, device_id);
ALTER TABLE disk_requests ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_disk_workspace_device (workspace_id, device_id);
ALTER TABLE deadlock_experiments ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_deadlock_exp_workspace_device (workspace_id, device_id);
ALTER TABLE synchronization_experiments ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_sync_exp_workspace_device (workspace_id, device_id);

-- Replace globally unique PID relationships with process-row relationships.
ALTER TABLE transactions DROP FOREIGN KEY fk_transaction_process;
ALTER TABLE transactions
    ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1,
    ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    ADD COLUMN process_id BIGINT NULL,
    ADD KEY idx_transactions_workspace_device (workspace_id, device_id),
    ADD KEY idx_transactions_process (process_id);
UPDATE transactions t JOIN processes p ON p.pid = t.pid
SET t.process_id = p.process_id, t.device_id = p.device_id, t.workspace_id = p.workspace_id;
ALTER TABLE transactions
    ADD CONSTRAINT fk_transaction_process_row FOREIGN KEY (process_id) REFERENCES processes(process_id);

ALTER TABLE transaction_operations ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_tx_ops_workspace_device (workspace_id, device_id);

ALTER TABLE query_executions DROP FOREIGN KEY fk_query_execution_process;
ALTER TABLE query_executions
    ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1,
    ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    ADD COLUMN process_id BIGINT NULL,
    ADD KEY idx_queries_workspace_device (workspace_id, device_id, timestamp),
    ADD KEY idx_queries_process (process_id);
UPDATE query_executions q JOIN processes p ON p.pid = q.pid
SET q.process_id = p.process_id, q.device_id = p.device_id, q.workspace_id = p.workspace_id;
ALTER TABLE query_executions
    ADD CONSTRAINT fk_query_execution_process_row FOREIGN KEY (process_id) REFERENCES processes(process_id);

ALTER TABLE locks ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_locks_workspace_device (workspace_id, device_id);
ALTER TABLE schedules ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_schedules_workspace_device (workspace_id, device_id);
ALTER TABLE schedule_operations ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_schedule_ops_workspace_device (workspace_id, device_id);
ALTER TABLE recovery_logs ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_recovery_workspace_device (workspace_id, device_id);
ALTER TABLE checkpoints ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_checkpoints_workspace_device (workspace_id, device_id);

ALTER TABLE cross_layer_traces DROP FOREIGN KEY fk_trace_process;
ALTER TABLE cross_layer_traces
    ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1,
    ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    ADD COLUMN process_id BIGINT NULL,
    ADD KEY idx_traces_workspace_device (workspace_id, device_id),
    ADD KEY idx_traces_process (process_id);
UPDATE cross_layer_traces t JOIN processes p ON p.pid = t.pid
SET t.process_id = p.process_id, t.device_id = p.device_id, t.workspace_id = p.workspace_id;
ALTER TABLE cross_layer_traces
    ADD CONSTRAINT fk_trace_process_row FOREIGN KEY (process_id) REFERENCES processes(process_id);

ALTER TABLE event_correlations ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_correlations_workspace_device (workspace_id, device_id);
ALTER TABLE incidents ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_incidents_workspace_device (workspace_id, device_id);
ALTER TABLE performance_records ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_perf_workspace_device (workspace_id, device_id);
ALTER TABLE dbms_query_observations ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_dbms_obs_workspace_device (workspace_id, device_id);
ALTER TABLE incident_replays ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_replays_workspace_device (workspace_id, device_id);
ALTER TABLE what_if_scenarios ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001', ADD KEY idx_whatif_workspace_device (workspace_id, device_id);
ALTER TABLE audit_logs ADD COLUMN workspace_id BIGINT NOT NULL DEFAULT 1, ADD COLUMN device_id CHAR(36) NULL, ADD KEY idx_audit_workspace_time (workspace_id, timestamp);

-- PID is not globally unique across devices or process lifetimes.
ALTER TABLE processes DROP INDEX pid;
ALTER TABLE processes ADD UNIQUE KEY uq_process_device_pid_started (device_id, pid, process_started_at);

ALTER TABLE processes
    ADD CONSTRAINT fk_process_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id),
    ADD CONSTRAINT fk_process_device FOREIGN KEY (device_id) REFERENCES devices(device_id);
ALTER TABLE os_events
    ADD CONSTRAINT fk_os_event_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id),
    ADD CONSTRAINT fk_os_event_device FOREIGN KEY (device_id) REFERENCES devices(device_id);

-- Run after deployment account seeding: grant the platform administrator access
-- only to workspace 1, which contains the pre-migration records.
