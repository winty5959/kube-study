#!/usr/bin/env bash
# Create .env for docker-compose with random credentials. Never overwrites an existing file.
# .env is gitignored; nothing printed here contains the generated values.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  echo ".env already exists; leaving it untouched"
  exit 0
fi
rand() { openssl rand -hex 16; }
umask 077
cat > .env <<EOF
POSTGRES_PASSWORD=$(rand)
MINIO_ROOT_USER=album-$(openssl rand -hex 4)
MINIO_ROOT_PASSWORD=$(rand)
EOF
echo ".env created (mode 600)"
