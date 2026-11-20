#!/usr/local/bin/python3
"""Exercise the actual synthetic workspace before the broker marks it ready."""

import argparse
import fcntl
import os
import pwd
import subprocess
import sys
import tempfile
import time
from pathlib import Path

WORKSPACE = Path("/workspace")
PROFILE = Path("/opt/sb001/profile")
DATABASE = "host=/run/postgresql dbname=orderflow user=candidate application_name=orderflow-api"


def check_workspace():
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("unexpected Python runtime")
    if os.getuid() == 0 or os.getuid() != pwd.getpwnam("candidate").pw_uid:
        raise RuntimeError("readiness requires the candidate account")
    with tempfile.TemporaryFile(dir=WORKSPACE) as file:
        file.write(b"sb001")
        file.flush()
        file.seek(0)
        if file.read() != b"sb001":
            raise RuntimeError("workspace round-trip failed")


def check_database():
    import psycopg

    deadline = time.monotonic() + 20
    while True:
        try:
            with psycopg.connect(DATABASE, connect_timeout=2) as db:
                role = db.execute(
                    "SELECT current_user, rolsuper, rolcreatedb, rolcreaterole, "
                    "rolreplication, rolbypassrls FROM pg_roles WHERE rolname=current_user"
                ).fetchone()
                if role != ("candidate", False, False, False, False, False):
                    raise RuntimeError("unexpected application role privileges")
                if db.execute("SHOW listen_addresses").fetchone() != ("",):
                    raise RuntimeError("unexpected database network listener")
                has_schema = db.execute(
                    "SELECT EXISTS (SELECT FROM schema_migrations WHERE name='001_reservations.sql')"
                ).fetchone()[0]
                seeded = db.execute(
                    "SELECT count(*) FROM inventory WHERE sku IN ('DEMO-BOOK', 'DEMO-LAST')"
                ).fetchone()[0]
                if not has_schema or seeded != 2:
                    raise RuntimeError("schema or seed verification failed")
                return
        except (psycopg.OperationalError, psycopg.errors.UndefinedTable):
            if time.monotonic() >= deadline:
                raise RuntimeError("database readiness deadline exceeded") from None
            time.sleep(0.1)


def check_application():
    import httpx

    runtime = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".sb001"
    runtime.mkdir(mode=0o700, exist_ok=True)
    socket = runtime / "api.sock"
    with (runtime / "api.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with httpx.Client(
            transport=httpx.HTTPTransport(uds=str(socket)), base_url="http://orderflow", timeout=2
        ) as client:

            def healthy():
                try:
                    response = client.get("/health")
                    if response.status_code != 200 or response.json() != {"status": "ready"}:
                        raise RuntimeError("running API failed its readiness check")
                    return True
                except httpx.ConnectError:
                    return False

            if healthy():
                return
            socket.unlink(missing_ok=True)
            with (runtime / "api.log").open("ab") as log:
                process = subprocess.Popen(
                    [sys.executable, "-m", "uvicorn", "orderflow.main:app", "--uds", str(socket)],
                    cwd=WORKSPACE,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    env={"PATH": os.defpath, "ORDERFLOW_DATABASE_URL": DATABASE},
                    start_new_session=True,
                )
            deadline = time.monotonic() + 5
            while process.poll() is None and time.monotonic() < deadline:
                if healthy():
                    return
                time.sleep(0.05)
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)
            raise RuntimeError("OrderFlow API did not pass its database-backed health check")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workload", choices=("minimal", "orderflow", "interactive"))
    args = parser.parse_args()
    if PROFILE.read_text().strip() != ("minimal" if args.workload == "minimal" else "orderflow"):
        raise RuntimeError("workload does not match the image profile")
    check_workspace()
    if args.workload != "minimal":
        check_database()
        check_application()
    print(f"SB001_READY {args.workload}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
