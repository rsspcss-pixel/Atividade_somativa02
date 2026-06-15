#!/bin/sh
set -e

mkdir -p "${DATABASE_PATH:-/root/.flowise}"

flowise start &
FLOWISE_PID=$!

python3 /bootstrap/wait_and_seed.py

wait "$FLOWISE_PID"
