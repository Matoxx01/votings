-- =========================
-- DATABASE
-- =========================
CREATE DATABASE IF NOT EXISTS voting
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE voting;

-- =========================
-- TABLE: role
-- =========================
CREATE TABLE role (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
) ENGINE=InnoDB;

-- =========================
-- TABLE: maintainer
-- =========================
CREATE TABLE maintainer (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_role INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    lastname VARCHAR(100) NOT NULL,
    mail VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    CONSTRAINT fk_maintainer_role
        FOREIGN KEY (id_role) REFERENCES role(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB;

-- =========================
-- TABLE: user
-- =========================
CREATE TABLE user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    lastname VARCHAR(100) NOT NULL,
    mail VARCHAR(150) NOT NULL UNIQUE,
    rut VARCHAR(20) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
) ENGINE=InnoDB;

-- =========================
-- TABLE: voting
-- =========================
CREATE TABLE voting (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    start_date DATETIME NOT NULL,
    finish_date DATETIME NOT NULL
) ENGINE=InnoDB;

-- =========================
-- TABLE: subject
-- =========================
CREATE TABLE subject (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    id_voting INT NOT NULL,
    CONSTRAINT fk_subject_voting
        FOREIGN KEY (id_voting) REFERENCES voting(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;

-- =========================
-- TABLE: count
-- =========================
CREATE TABLE `count` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_subject INT NOT NULL,
    number INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_count_subject
        FOREIGN KEY (id_subject) REFERENCES subject(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;

-- =========================
-- TABLE: user_data
-- =========================
CREATE TABLE user_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_voting INT NOT NULL,
    rut VARCHAR(20) NOT NULL,
    `register` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_user_data_voting
        FOREIGN KEY (id_voting) REFERENCES voting(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;
