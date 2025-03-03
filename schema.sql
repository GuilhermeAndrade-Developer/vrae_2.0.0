CREATE TABLE IF NOT EXISTS devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    protocol ENUM('RTSP', 'HTTP', 'ONVIF') NOT NULL,
    ip VARCHAR(255) NOT NULL,
    model VARCHAR(255),
    username VARCHAR(255),
    password VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_device (name, ip)
);

CREATE TABLE IF NOT EXISTS users (
    id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY username (username)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS login_logs (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    token VARCHAR(255) NOT NULL,
    login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY user_id (user_id),
    CONSTRAINT login_logs_ibfk_1 FOREIGN KEY (user_id) 
    REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB;