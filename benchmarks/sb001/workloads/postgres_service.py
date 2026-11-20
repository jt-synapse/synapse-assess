#!/usr/local/bin/python3
"""Run PostgreSQL as the dedicated postgres OS user for this synthetic workload."""

import os
import pwd
import signal
import subprocess
import sys
import time
from pathlib import Path

BIN = Path("/usr/lib/postgresql/16/bin")
ASSETS = Path("/opt/sb001")
SOCKET = "/run/postgresql"
AUTH = """local all postgres peer
local orderflow candidate peer
local all all reject
"""


def psql(database: str, commands: str):
    subprocess.run(
        [
            BIN / "psql",
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            SOCKET,
            "-U",
            "postgres",
            "-d",
            database,
        ],
        input=commands,
        text=True,
        check=True,
        timeout=15,
    )


def bootstrap():
    psql(
        "postgres",
        """
        CREATE ROLE candidate LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
            NOBYPASSRLS CONNECTION LIMIT 12;
        CREATE DATABASE orderflow OWNER candidate;
        REVOKE ALL ON DATABASE orderflow FROM PUBLIC;
    """,
    )
    schema = (ASSETS / "schema.sql").read_text()
    seed = (ASSETS / "seed.sql").read_text()
    psql(
        "orderflow",
        f"""
        SET ROLE candidate;
        BEGIN;
        CREATE TABLE schema_migrations (name text PRIMARY KEY);
        {schema}
        INSERT INTO schema_migrations VALUES ('001_reservations.sql');
        {seed}
        COMMIT;
    """,
    )


def supervise():
    if os.getuid() != pwd.getpwnam("postgres").pw_uid:
        raise RuntimeError("PostgreSQL supervisor requires the unprivileged postgres account")
    data = Path(os.environ["PGDATA"])
    marker = data / "sb001-initialized"
    if not data.exists():
        subprocess.run(
            [
                BIN / "initdb",
                "-D",
                data,
                "--no-locale",
                "--encoding=UTF8",
                "--auth-local=peer",
                "--auth-host=scram-sha-256",
            ],
            check=True,
        )
        (data / "pg_hba.conf").write_text(AUTH)
    elif not marker.is_file():
        raise RuntimeError("Incomplete synthetic database bootstrap; discard this sandbox")

    stopped = False
    process = None

    def stop(signum, frame):
        nonlocal stopped
        stopped = True
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGINT)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    for attempt in range(3):
        if stopped:
            return
        process = subprocess.Popen(
            [
                BIN / "postgres",
                "-D",
                data,
                "-c",
                "listen_addresses=",
                "-c",
                f"unix_socket_directories={SOCKET}",
                "-c",
                "max_connections=24",
                "-c",
                "shared_buffers=64MB",
                "-c",
                "idle_in_transaction_session_timeout=90s",
                "-c",
                "jit=off",
            ]
        )
        try:
            if not marker.is_file():
                deadline = time.monotonic() + 20
                while process.poll() is None and time.monotonic() < deadline:
                    probe = subprocess.run(
                        [
                            BIN / "pg_isready",
                            "-q",
                            "-h",
                            SOCKET,
                            "-d",
                            "postgres",
                            "-U",
                            "postgres",
                            "-t",
                            "1",
                        ],
                        check=False,
                    )
                    if probe.returncode == 0:
                        break
                    time.sleep(0.05)
                else:
                    raise RuntimeError("PostgreSQL did not enter service during bootstrap")
                bootstrap()
                marker.touch(mode=0o600)
            process.wait()
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                process.wait(timeout=10)
        if not stopped:
            time.sleep(0.25 * (attempt + 1))
    if not stopped:
        raise RuntimeError("PostgreSQL restart limit reached")


if __name__ == "__main__":
    try:
        supervise()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
