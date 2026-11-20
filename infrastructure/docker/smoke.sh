#!/usr/bin/env bash
# Exercise a fresh, disposable Compose project without touching the development stack.
set -euo pipefail
project="assess-smoke-$(date +%s)-$$"
export API_PORT=0 WEB_PORT=0
compose=(docker compose --project-name "$project")
cleanup() {
    status=$?
    if (( status != 0 )); then "${compose[@]}" logs --tail 60 >&2 || true; fi
    "${compose[@]}" down --volumes --remove-orphans
}
trap cleanup EXIT
"${compose[@]}" up --build --detach --wait --wait-timeout 150
api=http://$("${compose[@]}" port api 8000)
web=http://$("${compose[@]}" port web 3000)
curl -fsS "$api/api/v1/health/ready" | grep -q '"ready"'
curl -fsS "$web" | grep -q '>Ready<'
"${compose[@]}" exec -T db psql -U platform -d platform --set=ON_ERROR_STOP=1 \
    -c "INSERT INTO assessment_versions(id,assessment_key,version,manifest) VALUES('00000000-0000-4000-8000-000000000001','smoke','1.0','{}')"
"${compose[@]}" stop db
status=$(curl -sS -o /dev/null -w '%{http_code}' "$api/api/v1/health/ready")
test "$status" = "503"
curl -fsS "$api/api/v1/health/live" | grep -q '"alive"'
curl -fsS "$web" | grep -q '>Unavailable<'
"${compose[@]}" start db
for attempt in {1..30}; do
    if curl -fsS "$api/api/v1/health/ready" >/dev/null 2>&1; then break; fi
    sleep 1
done
curl -fsS "$api/api/v1/health/ready" | grep -q '"ready"'
"${compose[@]}" run --rm migrate
"${compose[@]}" exec -T db psql -U platform -d platform -Atc \
    "SELECT version FROM assessment_versions WHERE assessment_key='smoke'" | grep -qx '1.0'
