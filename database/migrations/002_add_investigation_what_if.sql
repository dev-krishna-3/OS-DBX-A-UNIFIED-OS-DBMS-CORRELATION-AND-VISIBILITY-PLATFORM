CREATE TABLE IF NOT EXISTS incident_replays (
    replay_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    incident_id INT NOT NULL,
    replayed_at DATETIME NOT NULL,
    outcome VARCHAR(50) NOT NULL,
    steps_json LONGTEXT NOT NULL,
    summary TEXT,
    CONSTRAINT fk_replay_incident
        FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)
);

CREATE TABLE IF NOT EXISTS what_if_scenarios (
    scenario_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    analysis_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    input_json LONGTEXT NOT NULL,
    result_json LONGTEXT NOT NULL,
    created_at DATETIME NOT NULL
);
