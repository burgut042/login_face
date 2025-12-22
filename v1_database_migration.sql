-- ============================================================================
-- V1 DATABASE MIGRATION: Add V2 Face Recognition Fields
-- ============================================================================
-- This migration adds columns needed for V2 face recognition integration
-- and creates the login_logs table for tracking inspector logins
--
-- Database: crime_report_db
-- Date: 2025-12-22
-- ============================================================================

-- Connect to the database
\c crime_report_db;

BEGIN;

-- ============================================================================
-- STEP 1: Add new columns to inspectors table
-- ============================================================================

-- Add photo field (path to face image)
ALTER TABLE inspectors
ADD COLUMN IF NOT EXISTS photo VARCHAR(255);

-- Add face_encoding field (JSON - 128-dimensional vector for face recognition)
ALTER TABLE inspectors
ADD COLUMN IF NOT EXISTS face_encoding JSONB;

-- Add registered_at timestamp (when inspector was registered in the system)
ALTER TABLE inspectors
ADD COLUMN IF NOT EXISTS registered_at TIMESTAMP DEFAULT NOW();

COMMENT ON COLUMN inspectors.photo IS 'Yuz rasmi path (faces/ directory)';
COMMENT ON COLUMN inspectors.face_encoding IS 'Face recognition uchun 128-dimensional vector (JSON)';
COMMENT ON COLUMN inspectors.registered_at IS 'Ro''yxatdan o''tgan vaqt';

-- ============================================================================
-- STEP 2: Create login_method enum type
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'login_method') THEN
        CREATE TYPE login_method AS ENUM ('FACE', 'PASSPORT');
    END IF;
END $$;

-- ============================================================================
-- STEP 3: Create login_logs table
-- ============================================================================

CREATE TABLE IF NOT EXISTS login_logs (
    id VARCHAR(36) PRIMARY KEY,
    inspector_id VARCHAR(36) NOT NULL,
    login_method login_method NOT NULL,
    login_time TIMESTAMP NOT NULL DEFAULT NOW(),
    login_photo VARCHAR(255),
    ip_address VARCHAR(45) NOT NULL,
    confidence DOUBLE PRECISION,
    success BOOLEAN NOT NULL DEFAULT TRUE,

    -- Foreign key constraint
    CONSTRAINT fk_login_logs_inspector
        FOREIGN KEY (inspector_id)
        REFERENCES inspectors(id)
        ON DELETE CASCADE
);

-- ============================================================================
-- STEP 4: Create indexes for better performance
-- ============================================================================

-- Index on inspector_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_login_logs_inspector_id
    ON login_logs(inspector_id);

-- Index on login_time (descending) for sorting recent logins
CREATE INDEX IF NOT EXISTS idx_login_logs_login_time
    ON login_logs(login_time DESC);

-- Composite index for inspector + login_time (descending)
CREATE INDEX IF NOT EXISTS idx_login_logs_inspector_time
    ON login_logs(inspector_id, login_time DESC);

-- ============================================================================
-- STEP 5: Add table comments
-- ============================================================================

COMMENT ON TABLE login_logs IS 'Inspector kirish tarixi (V2 face recognition system)';
COMMENT ON COLUMN login_logs.id IS 'UUID primary key';
COMMENT ON COLUMN login_logs.inspector_id IS 'Inspector ID (foreign key to inspectors table)';
COMMENT ON COLUMN login_logs.login_method IS 'Kirish usuli: FACE (yuz tanish) yoki PASSPORT (pasport)';
COMMENT ON COLUMN login_logs.login_time IS 'Kirish vaqti';
COMMENT ON COLUMN login_logs.login_photo IS 'Login vaqtida olingan rasm path (login_photos/YYYY/MM/DD/)';
COMMENT ON COLUMN login_logs.ip_address IS 'Foydalanuvchi IP manzili';
COMMENT ON COLUMN login_logs.confidence IS 'Face recognition ishonch darajasi (0-100%)';
COMMENT ON COLUMN login_logs.success IS 'Kirish muvaffaqiyatli bo''ldimi';

-- ============================================================================
-- VERIFY MIGRATION
-- ============================================================================

-- Show inspectors table structure
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'inspectors'
ORDER BY ordinal_position;

-- Show login_logs table structure
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'login_logs'
ORDER BY ordinal_position;

-- Show indexes on login_logs
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'login_logs';

COMMIT;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- Next steps:
-- 1. Run this migration: psql -U postgres -d crime_report_db -f v1_database_migration.sql
-- 2. Update Prisma client: cd v1 && npx prisma generate
-- 3. Test v2 Django connection: cd v2 && python manage.py check
-- ============================================================================
