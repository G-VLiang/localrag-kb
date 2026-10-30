#!/usr/bin/env bash
# 从备份恢复数据库（会覆盖现有数据，谨慎操作）
set -euo pipefail

FILE="${1:-}"
if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
  echo "用法: $0 <备份文件.sql.gz>"
  exit 1
fi

echo "恢复 $FILE 到数据库（将覆盖现有数据）..."
gunzip -c "$FILE" | docker compose exec -T db psql -U "${POSTGRES_USER:-kb}" -d "${POSTGRES_DB:-kb}"
echo "恢复完成"
