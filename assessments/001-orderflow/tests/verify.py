"""Exercise only the bundled authored starter and references against a new local cluster."""

import argparse
import os
import shutil
import sys
import tarfile
from contextlib import contextmanager
from pathlib import Path
from subprocess import Popen, TimeoutExpired, run
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from uuid import uuid4

import httpx
import psycopg
from package import ROOT, build_candidate
from psycopg import sql
from psycopg.conninfo import make_conninfo


@contextmanager
def database_cluster(work, binaries):
    socket = work / "pg"
    socket.mkdir(mode=0o700)
    data = work / "data"
    # Local trust is limited to the private socket directory of this disposable cluster.
    run(
        [
            binaries / "initdb",
            "-D",
            data,
            "-U",
            "package_author",
            "-A",
            "trust",
            "--no-locale",
            "--encoding=UTF8",
        ],
        check=True,
    )
    options = f"-c listen_addresses='' -c unix_socket_directories='{socket}'"
    pg_ctl = [binaries / "pg_ctl", "-D", data, "-w"]
    run([*pg_ctl, "-l", work / "postgres.log", "-o", options, "start"], check=True)
    try:
        yield make_conninfo(host=str(socket), port=5432, user="package_author", dbname="postgres")
    finally:
        run([*pg_ctl, "-m", "fast", "stop"], check=True)


@contextmanager
def running_app(source, socket, env):
    socket.unlink(missing_ok=True)
    with (source.parent / "app.log").open("ab") as log:
        process = Popen(
            [sys.executable, "-m", "uvicorn", "orderflow.main:app", "--uds", str(socket)],
            cwd=source,
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            with httpx.Client(
                transport=httpx.HTTPTransport(uds=str(socket)),
                base_url="http://orderflow",
                timeout=5,
            ) as client:
                deadline = monotonic() + 10
                while monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError("OrderFlow stopped during startup")
                    try:
                        if client.get("/health").status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    sleep(0.05)
                else:
                    raise RuntimeError("OrderFlow did not become ready")
                yield client
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except TimeoutExpired:
                process.kill()
                process.wait()


def prepare_source(archive, source, variant):
    source.mkdir()
    with tarfile.open(archive) as bundle:
        bundle.extractall(source, filter="data")
    reference = ROOT / "evaluator" / "reference"
    if variant in ("stage_a", "stage_b"):
        for module in (reference / "stage_a").glob("*.py"):
            shutil.copy(module, source / "orderflow")
    if variant == "stage_b":
        shutil.copy(reference / "stage_b" / "reservations.py", source / "orderflow")
        shutil.copy(reference / "stage_b" / "002_idempotency.sql", source / "migrations")


def verify_variant(work, admin, archive, variant):
    print(f"Checking {variant}", flush=True)
    source = work / variant
    prepare_source(archive, source, variant)
    app_role = f"app_{variant}"
    with psycopg.connect(admin, autocommit=True) as db:
        db.execute(
            sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
                sql.Identifier(app_role)
            )
        )
        db.execute(
            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(variant), sql.Identifier(app_role)
            )
        )
        db.execute(
            sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(variant))
        )
    author_dsn = make_conninfo(admin, dbname=variant)
    socket = work / "api.sock"
    # This private authoring harness needs only a scoped attempt credential.
    # The application process does not inherit platform or evaluator variables.
    app_env = {
        "PATH": os.defpath,
        "ORDERFLOW_DATABASE_URL": make_conninfo(
            admin, dbname=variant, user=app_role, application_name="orderflow-api"
        ),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for _ in range(2):
        run([sys.executable, "-m", "orderflow.setup"], cwd=source, env=app_env, check=True)
    run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=source, env=app_env, check=True)
    evaluator_env = {
        "PATH": os.defpath,
        "EVALUATOR_DATABASE_URL": author_dsn,
        "EVALUATOR_API_SOCKET": str(socket),
    }
    hidden = ROOT / "evaluator" / "hidden"
    probes = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        str(hidden / "test_independent.py"),
    ]
    if variant == "starter":
        probes.append("--verify-starter-defects")
    if variant == "stage_b":
        probes.append(str(hidden / "test_assisted.py"))
    with running_app(source, socket, app_env) as client:
        run(probes, cwd=work, env=evaluator_env, check=True)
        if variant == "stage_b":
            request = {"sku": "DEMO-BOOK", "quantity": 1}
            headers = {"Idempotency-Key": uuid4().hex}
            first = client.post("/reservations", json=request, headers=headers)
            assert first.status_code == 201, first.text
    if variant == "stage_b":
        with running_app(source, socket, app_env) as fresh_client:
            retried = fresh_client.post("/reservations", json=request, headers=headers)
            assert retried.status_code == 201 and retried.json() == first.json(), retried.text
        print("Passed committed retry across a full API process restart.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--postgres-bin",
        type=Path,
        required=True,
        help="Directory containing PostgreSQL 16 initdb and pg_ctl",
    )
    args = parser.parse_args()
    with TemporaryDirectory(prefix="orderflow-", dir="/tmp") as directory:
        work = Path(directory).resolve()
        archive = work / "candidate.tar"
        build_candidate(ROOT / "candidate", archive)
        with database_cluster(work, args.postgres_bin) as admin:
            for variant in ("starter", "stage_a", "stage_b"):
                verify_variant(work, admin, archive, variant)


if __name__ == "__main__":
    main()
