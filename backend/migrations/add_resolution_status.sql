-- Migration: Add resolution status and related symptom tracking
-- Date: 2025-01-13

-- Add resolution status column
ALTER TABLE symptom_logs 
ADD COLUMN IF NOT EXISTS resolution_status VARCHAR(20) DEFAULT 'Unknown';

-- Add related symptom IDs column for linking symptoms
ALTER TABLE symptom_logs 
ADD COLUMN IF NOT EXISTS related_symptom_ids TEXT[];

-- Add follow-up date column
ALTER TABLE symptom_logs 
ADD COLUMN IF NOT EXISTS follow_up_date TIMESTAMP WITH TIME ZONE;

-- Add updated_at column for tracking status changes
ALTER TABLE symptom_logs 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Create index for resolution status queries
CREATE INDEX IF NOT EXISTS idx_symptom_logs_resolution_status 
ON symptom_logs(user_id, resolution_status);

-- Create index for follow-up date queries
CREATE INDEX IF NOT EXISTS idx_symptom_logs_follow_up 
ON symptom_logs(user_id, follow_up_date) 
WHERE follow_up_date IS NOT NULL;

-- Add constraint for valid resolution status values
ALTER TABLE symptom_logs 
ADD CONSTRAINT IF NOT EXISTS chk_resolution_status 
CHECK (resolution_status IN ('Ongoing', 'Resolved', 'Improved', 'Worsened', 'Unknown'));

-- Update existing records to have 'Unknown' status
UPDATE symptom_logs 
SET resolution_status = 'Unknown' 
WHERE resolution_status IS NULL; 