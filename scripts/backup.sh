#!/usr/bin/env bash
# 备份 PostgreSQL（含知识库全部数据）到 ./backups
set -euo pipefail

TS="$(date +%Y%m%d%H%M%S)"
OUT_DIR="${OUT_DIR:-./backups}"
mkdir -p "$OUT_DIR"
FILE="$OUT_DIR/localrag_db_${TS}.sql.gz"

echo "备份数据库到 $FILE ..."
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-kb}" -d "${POSTGRES_DB:-kb}" | gzip > "$FILE"
echo "完成：$FILE ($(du -h "$FILE" | cut -f1))"
