CREATE DATABASE IF NOT EXISTS os_dbx;

USE os_dbx;

# USER TABLE CREATED BY "KRISHNA NITIN ANASANE"
CREATE TABLE users (
    user_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    uid_linux BIGINT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


# PROCESS TABLE CREATED BY "KRISHNA NITIN ANASANE"
CREATE TABLE processes (
    process_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    pid BIGINT NOT NULL UNIQUE,
    ppid BIGINT NULL,
    user_id BIGINT NULL,
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
    event_type VARCHAR(100) NOT NULL,
    file_path VARCHAR(1000),
    timestamp DATETIME,
    details TEXT
);