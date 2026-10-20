-- 00_create_schema.sql

-- Create schema user
CREATE USER library IDENTIFIED BY "StrongPassword123";

-- Allow database connection
GRANT CREATE SESSION TO library;

-- Allow creation of database objects
GRANT CREATE TABLE TO library;
GRANT CREATE VIEW TO library;
GRANT CREATE SEQUENCE TO library;
GRANT CREATE PROCEDURE TO library;
GRANT CREATE TRIGGER TO library;
GRANT CREATE TYPE TO library;

-- Allow storage in USERS tablespace
ALTER USER library QUOTA UNLIMITED ON USERS;