-- ==============================================================================
-- FitTrack - Gym Management System
-- Database Schema: MySQL Relational Database (fittrack_db)
-- ==============================================================================
-- DBMS CONCEPT EXPLANATION FOR VIVA:
-- Why Relational Database (MySQL) for core entities?
-- 1. ACID Compliance: Financial transactions, membership validity, and enrollments
--    demand strong consistency, atomicity, and durability.
-- 2. Normalization (3NF): Entities (plans, trainers, members, classes) are separated
--    to eliminate update, insertion, and deletion anomalies.
-- 3. Referential Integrity: Foreign keys ensure that member records cannot reference
--    non-existent plans or deleted trainers (handling using ON DELETE SET NULL).
-- 4. Unique Constraints: The email address must be strictly unique to prevent
--    duplicate account registrations.
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS `fittrack_db` 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `fittrack_db`;

-- Drop child tables first to avoid foreign key constraint violations
DROP TABLE IF EXISTS `classes`;
DROP TABLE IF EXISTS `members`;
DROP TABLE IF EXISTS `trainers`;
DROP TABLE IF EXISTS `plans`;

-- ------------------------------------------------------------------------------
-- Table 1: plans
-- Stores membership plans with duration in months and pricing.
-- ------------------------------------------------------------------------------
CREATE TABLE `plans` (
    `plan_id` INT AUTO_INCREMENT PRIMARY KEY,
    `plan_name` VARCHAR(100) NOT NULL,
    `duration_months` INT NOT NULL CHECK (`duration_months` > 0),
    `price` DECIMAL(10, 2) NOT NULL CHECK (`price` >= 0),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- Table 2: trainers
-- Stores certified gym trainers and their specialized fitness domains.
-- ------------------------------------------------------------------------------
CREATE TABLE `trainers` (
    `trainer_id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `specialization` VARCHAR(100) NOT NULL,
    `phone` VARCHAR(20) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- Table 3: members
-- Stores gym members. Linked to plans and assigned personal trainers.
-- Constraints:
-- - email is UNIQUE (enforces 1 account per email address)
-- - plan_id is FK referencing plans(plan_id) ON DELETE SET NULL
-- - trainer_id is FK referencing trainers(trainer_id) ON DELETE SET NULL
-- ------------------------------------------------------------------------------
CREATE TABLE `members` (
    `member_id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(150) NOT NULL UNIQUE,
    `phone` VARCHAR(20) NOT NULL,
    `join_date` DATE NOT NULL,
    `plan_id` INT NULL,
    `trainer_id` INT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_members_plan` 
        FOREIGN KEY (`plan_id`) REFERENCES `plans` (`plan_id`) 
        ON DELETE SET NULL 
        ON UPDATE CASCADE,
    CONSTRAINT `fk_members_trainer` 
        FOREIGN KEY (`trainer_id`) REFERENCES `trainers` (`trainer_id`) 
        ON DELETE SET NULL 
        ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- Table 4: classes
-- Group fitness classes (e.g. HIIT, Yoga, Zumba) mapped to a lead trainer.
-- ------------------------------------------------------------------------------
CREATE TABLE `classes` (
    `class_id` INT AUTO_INCREMENT PRIMARY KEY,
    `class_name` VARCHAR(100) NOT NULL,
    `schedule_time` VARCHAR(100) NOT NULL,
    `trainer_id` INT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_classes_trainer` 
        FOREIGN KEY (`trainer_id`) REFERENCES `trainers` (`trainer_id`) 
        ON DELETE SET NULL 
        ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ==============================================================================
-- Sample Seed Data Insertion
-- ==============================================================================

-- 1. Membership Plans
INSERT INTO `plans` (`plan_id`, `plan_name`, `duration_months`, `price`) VALUES
(1, 'Monthly Basic', 1, 1500.00),
(2, 'Quarterly Pro', 3, 4000.00),
(3, 'Half-Yearly Elite', 6, 7500.00),
(4, 'Annual Champion', 12, 13500.00);

-- 2. Certified Trainers
INSERT INTO `trainers` (`trainer_id`, `name`, `specialization`, `phone`) VALUES
(1, 'Arjun Verma', 'Strength & Conditioning', '+91 98765 43210'),
(2, 'Priya Nair', 'Yoga & Mobility Flow', '+91 98111 22334'),
(3, 'Vikram Singh', 'CrossFit & Functional Training', '+91 97222 33445'),
(4, 'Sarah Khan', 'Cardio, HIIT & Weight Loss', '+91 96333 44556');

-- 3. Gym Members
INSERT INTO `members` (`member_id`, `name`, `email`, `phone`, `join_date`, `plan_id`, `trainer_id`) VALUES
(1, 'Rahul Sharma', 'rahul.sharma@example.com', '+91 98234 56789', '2026-01-10', 1, 1),
(2, 'Ananya Sen', 'ananya.sen@example.com', '+91 98345 67890', '2026-02-01', 3, 2),
(3, 'Rohan Mehta', 'rohan.mehta@example.com', '+91 98456 78901', '2026-02-15', 2, 3),
(4, 'Sneha Patel', 'sneha.patel@example.com', '+91 98567 89012', '2026-03-01', 4, 1),
(5, 'Amit Joshi', 'amit.joshi@example.com', '+91 98678 90123', '2026-03-20', 1, 4),
(6, 'Kavita Roy', 'kavita.roy@example.com', '+91 98789 01234', '2026-04-05', 2, 2);

-- 4. Group Fitness Classes
INSERT INTO `classes` (`class_id`, `class_name`, `schedule_time`, `trainer_id`) VALUES
(1, 'Morning Power Yoga', 'Mon & Wed 06:30 AM - 07:30 AM', 2),
(2, 'High-Intensity CrossFit', 'Tue & Thu 07:00 AM - 08:00 AM', 3),
(3, 'Evening Strength Bootcamp', 'Mon, Wed, Fri 06:00 PM - 07:00 PM', 1),
(4, 'Spin & Cardio Blast', 'Sat & Sun 08:00 AM - 09:00 AM', 4);

-- End of schema.sql
