CREATE TYPE photo_status AS ENUM ('PENDING', 'PROCESSING', 'DONE', 'FAILED');

CREATE TABLE photos (
    id               UUID PRIMARY KEY,
    filename         VARCHAR(255) NOT NULL,
    content_type     VARCHAR(100) NOT NULL,
    size_bytes       BIGINT       NOT NULL,
    original_key     VARCHAR(255) NOT NULL,
    thumb_small_key  VARCHAR(255),
    thumb_medium_key VARCHAR(255),
    status           photo_status NOT NULL DEFAULT 'PENDING',
    processed_by     VARCHAR(255),
    retry_count      INT          NOT NULL DEFAULT 0,
    error            TEXT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    processed_at     TIMESTAMPTZ
);

CREATE INDEX photos_created_at_idx ON photos (created_at DESC);
CREATE INDEX photos_status_idx ON photos (status);
