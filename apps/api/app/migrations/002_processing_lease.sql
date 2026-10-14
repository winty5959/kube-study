ALTER TABLE photos ADD COLUMN processing_started_at TIMESTAMPTZ;
UPDATE photos SET processing_started_at = created_at WHERE status = 'PROCESSING';
CREATE INDEX photos_processing_started_idx ON photos (processing_started_at)
    WHERE status = 'PROCESSING';
