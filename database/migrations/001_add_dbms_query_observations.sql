CREATE TABLE IF NOT EXISTS dbms_query_observations (
    observation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    source_thread_id BIGINT NOT NULL,
    source_event_id BIGINT NOT NULL,
    connection_id BIGINT NULL,
    processlist_user VARCHAR(255),
    database_name VARCHAR(255),
    query_type VARCHAR(50) NOT NULL,
    query_text TEXT NOT NULL,
    execution_time_ms FLOAT NOT NULL,
    rows_affected BIGINT NOT NULL,
    status VARCHAR(50) NOT NULL,
    observed_at DATETIME NOT NULL,
    CONSTRAINT uq_dbms_query_source
        UNIQUE (source_thread_id, source_event_id)
);
