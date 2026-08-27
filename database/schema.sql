CREATE DATABASE IF NOT EXISTS os_dbx;

USE os_dbx;

# USER TABLE CREATED BY "KRISHNA NITIN ANASANE"
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    uid_linux BIGINT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


# PROCESS TABLE CREATED BY "KRISHNA NITIN ANASANE"
CREATE TABLE processes (
    process_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    pid BIGINT NOT NULL UNIQUE,
    ppid BIGINT NULL,
    user_id INT NULL,
    name VARCHAR(255),
    state VARCHAR(50),
    cpu_percent DECIMAL(5,2),
    memory_percent DECIMAL(5,2),
    start_time DATETIME,
    end_time DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_process_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);

# THREADS TABLE CREATED BY "KRISHNA NITIN ANASANE" 
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

#SYSTEM_CALLS TABLE CREATED BY "KRISHNA NITIN ANASANE"
CREATE TABLE system_calls (
    syscall_id INT AUTO_INCREMENT PRIMARY KEY,
    process_id INT NOT NULL,
    syscall_name VARCHAR(100) NOT NULL,
    arguments TEXT,
    return_value VARCHAR(255),
    timestamp DATETIME,

    CONSTRAINT fk_syscall_process
        FOREIGN KEY (process_id)
        REFERENCES processes(process_id)
);
CREATE INDEX idx_system_calls_process
ON system_calls(process_id);
CREATE INDEX idx_system_calls_timestamp
ON system_calls(timestamp);


#OS_EVENTS TABLE CREATED BY "KRISHNA NITIN ANASANE"
CREATE TABLE os_events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    pid INT NOT NULL,
    ppid INT,
    user VARCHAR(255),
    event_type VARCHAR(100) NOT NULL,
    file_path VARCHAR(1000),
    timestamp DATETIME,
    details TEXT
);

#RESOURCE_METRICS TABLE CREATED BY "KRISHNA NITIN ANASANE"
CREATE TABLE resource_metrics (
    metric_id INT AUTO_INCREMENT PRIMARY KEY,
    process_id INT NOT NULL,
    cpu_usage FLOAT,
    memory_usage FLOAT,
    disk_io FLOAT,
    network_io FLOAT,
    recorded_at DATETIME
);
CREATE INDEX idx_resource_metrics_process
ON resource_metrics(process_id);
CREATE INDEX idx_resource_metrics_recorded_at
ON resource_metrics(recorded_at);


#FILES TABLE CREATED BY "KRISHNA NITIN ANASANE"
CREATE TABLE files (
    file_id INT AUTO_INCREMENT PRIMARY KEY,
    file_path VARCHAR(1000),
    owner_id INT,
    permissions VARCHAR(20),
    size_bytes BIGINT
);

#DIRECTORIES TABLE CREATED BY "KRISHNA NITIN ANASANE"
CREATE TABLE directories (
    directory_id INT AUTO_INCREMENT PRIMARY KEY,
    path VARCHAR(1000),
    parent_directory_id INT,

    CONSTRAINT fk_directory_parent
        FOREIGN KEY (parent_directory_id)
        REFERENCES directories(directory_id)
);

#PERMISSIONS TABLE CREATED BY "KRISHNA NITIN ANASANE"
CREATE TABLE permissions (
    permission_id INT AUTO_INCREMENT PRIMARY KEY,
    file_id INT NOT NULL,
    user_id INT NOT NULL,
    access_type VARCHAR(20),
    granted_at DATETIME
);