#!/usr/bin/env bash
# changedetection.io datastore günlük yedeği.
# 14 gün saklanır, eski yedekler otomatik silinir.
set -euo pipefail

DATA_DIR="/home/khan/docker/changedetection/data"
BACKUP_DIR="/home/khan/rakip-analizi/backups/cd"
KEEP_DAYS=14

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/cd-datastore-$STAMP.tar.zst"

# root:root sahipliğindeki data'yı okumak için docker exec ile tar üretiyoruz;
# stdout'u host tarafında zstd ile sıkıştırıp yazıyoruz.
docker exec changedetection tar -C /datastore -cf - . 2>/dev/null \
  | zstd -T0 -3 -q -o "$OUT"

echo "[backup-cd] oluşturuldu: $OUT ($(du -h "$OUT" | cut -f1))"

# Retention
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'cd-datastore-*.tar.zst' -mtime "+$KEEP_DAYS" -print -delete \
  | sed 's/^/[backup-cd] silindi: /'
