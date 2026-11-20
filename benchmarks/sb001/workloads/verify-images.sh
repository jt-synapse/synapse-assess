#!/usr/bin/env bash
# CI only: validate authored fixtures using ephemeral, network-isolated containers.
set -euo pipefail
work=$(mktemp -d)
base=$(cd "$(dirname "$0")" && pwd)
tag="sb001-test-$(basename "$work" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]')"
containers=()
images=()
cleanup() {
    set +u
    for container in "${containers[@]}"; do docker rm -fv "$container" >/dev/null 2>&1 || :; done
    for image in "${images[@]}"; do docker image rm "$image" >/dev/null 2>&1 || :; done
    rm -rf "$work"
}
trap cleanup EXIT
for workload in minimal orderflow; do
    python3 "$base/prepare.py" "$workload" "$work/$workload"
    docker build -t "$tag-$workload" "$work/$workload"
    images+=("$tag-$workload")
    container=$(docker run -d --network none --cap-drop ALL --security-opt no-new-privileges \
        --cpus 2 --memory 1g --pids-limit 128 "$tag-$workload")
    containers+=("$container")
    docker exec --user candidate "$container" /opt/sb001/ready "$workload"
    if [[ "$workload" == orderflow ]]; then
        docker exec --user candidate "$container" /opt/sb001/ready interactive
        # Verify git works end-to-end inside the image (not only git --version).
        docker exec --user candidate "$container" sh -ec '
            tmp=$(mktemp -d)
            trap "rm -rf \"$tmp\"" EXIT
            git -C "$tmp" init -q
            printf "hello\n" > "$tmp/sample.txt"
            git -C "$tmp" add sample.txt
            git -C "$tmp" status --short | grep -qx "A  sample.txt"
            printf "world\n" >> "$tmp/sample.txt"
            git -C "$tmp" diff --quiet && exit 1 || true
        '
        # The private service user can restart PostgreSQL independently from the API.
        docker exec --user postgres "$container" sh -ec \
            '/usr/lib/postgresql/16/bin/pg_ctl -D "$PGDATA" -m fast -w stop'
        docker exec --user candidate "$container" /opt/sb001/ready orderflow
        docker exec --interactive --user postgres --env SB001_DISPOSABLE_IMAGE_TEST=1 \
            "$container" python - < "$base/verify_restore.py"
        # Reject an application identity change to the database service account.
        if docker exec --user candidate "$container" \
            psql -h /run/postgresql -U postgres -d postgres -X -c 'SELECT 1' >/dev/null 2>&1; then
            echo "Database accepted an incorrect peer identity" >&2
            exit 1
        fi
    fi
done
