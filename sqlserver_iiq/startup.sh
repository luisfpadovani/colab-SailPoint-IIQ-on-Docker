#!/bin/bash
set -euo pipefail
SQLCMD=/opt/mssql-tools18/bin/sqlcmd
export SQLCMDPASSWORD="${MSSQL_SA_PASSWORD:?Set MSSQL_SA_PASSWORD}"
# SQLCMD expands these variables in SQL literals; reject characters that can alter SQL.
for key in APP_MOCK_PASSWORD HEALTHCHECK_PASSWORD IIQ_DB_PASSWORD IIQ_PLUGIN_PASSWORD IIQ_AH_PASSWORD; do
  value="${!key:-}"
  [[ "$value" =~ ^[A-Za-z0-9_@%+=:,./!?-]{16,128}$ ]] || {
    echo "$key must be 16-128 characters using letters, digits or _@%+=:,./!?-" >&2; exit 1;
  }
done
ready=false
for _ in $(seq 1 90); do
  if "$SQLCMD" -N -b -l 3 -S sqlserver -U sa -Q "SELECT 1" >/dev/null 2>&1; then
    ready=true; break
  fi
  sleep 2
done
$ready || { echo "SQL Server readiness timed out" >&2; exit 1; }
[ ! -f /var/opt/mssql/.initialized ] || exit 0
# A partially failed bootstrap requires an explicit restore/reset, never rerun destructive DDL.
[ ! -f /var/opt/mssql/.initializing ] || {
  echo "Previous SQL bootstrap failed; restore/reset the lab database volume" >&2; exit 1;
}
touch /var/opt/mssql/.initializing
while IFS= read -r -d '' entry; do
  "$SQLCMD" -N -b -r 1 -S sqlserver -U sa -i "$entry"
done < <(find /opt/iiq-scripts -maxdepth 1 -type f \( -name '*.sql' -o -name '*.sqlserver' \) -print0 | sort -zV)
mv /var/opt/mssql/.initializing /var/opt/mssql/.initialized
