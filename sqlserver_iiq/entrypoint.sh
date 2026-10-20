#!/bin/bash
set -euo pipefail
: "${MSSQL_SA_PASSWORD:?Set MSSQL_SA_PASSWORD}"
[ "${ACCEPT_EULA:-}" = Y ] || { echo "Review and accept the Microsoft SQL Server EULA" >&2; exit 1; }
python3 /opt/iiq/configure-tls.py
/opt/mssql/bin/sqlservr &
server_pid=$!
trap 'kill -TERM "$server_pid" 2>/dev/null || true' TERM INT
if ! /opt/iiq/startup.sh; then
  kill -TERM "$server_pid" 2>/dev/null || true
  wait "$server_pid" || true
  exit 1
fi
wait "$server_pid"
