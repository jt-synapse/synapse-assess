"""Exercise PostgreSQL logical backup in the disposable SB-001 image smoke test."""

import os
import pwd
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import psycopg
from psycopg import sql

PG_BIN = Path("/usr/lib/postgresql/16/bin")
SOCKET = "/run/postgresql"
SOURCE = "orderflow"


def connect(database: str, *, autocommit: bool = False):
    return psycopg.connect(
        host=SOCKET, user="postgres", dbname=database, connect_timeout=3, autocommit=autocommit
    )


def verify_snapshot(database: str, table: sql.Identifier, baseline: list, *, write: bool):
    with connect(database) as db:
        db.execute("SET LOCAL ROLE candidate")
        migrations = db.execute("SELECT name FROM schema_migrations ORDER BY name").fetchall()
        inventory = db.execute("SELECT sku, available FROM inventory ORDER BY sku").fetchall()
        markers = db.execute(
            sql.SQL("SELECT state FROM {} ORDER BY state").format(table)
        ).fetchall()
        if migrations != [("001_reservations.sql",)] or inventory != baseline:
            raise RuntimeError(
                "Schema migration or committed seed inventory changed across restore"
            )
        if markers != [("committed",)]:
            raise RuntimeError("Snapshot did not preserve the committed transaction boundary")
        if write:
            db.execute(sql.SQL("INSERT INTO {} VALUES ('after-restore')").format(table))
    if write:
        with connect(database) as reader:
            reader.execute("SET LOCAL ROLE candidate")
            result = reader.execute(sql.SQL("SELECT state FROM {} ORDER BY state").format(table))
            if result.fetchall() != [("after-restore",), ("committed",)]:
                raise RuntimeError("Restored database did not persist a fresh transaction")


def run_backup(probe_schema: str, target: str, backup: Path):
    schema = sql.Identifier(probe_schema)
    table = sql.Identifier(probe_schema, "markers")
    with connect(SOURCE) as db:
        db.execute("SET LOCAL ROLE candidate")
        baseline = db.execute("SELECT sku, available FROM inventory ORDER BY sku").fetchall()
        if baseline != [("DEMO-BOOK", 8), ("DEMO-LAST", 1)]:
            raise RuntimeError("Expected a freshly seeded synthetic database")
        db.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
        db.execute(sql.SQL("CREATE TABLE {} (state text PRIMARY KEY)").format(table))
        db.execute(sql.SQL("INSERT INTO {} VALUES ('committed')").format(table))

    try:
        with connect(SOURCE) as writer:
            writer.execute("SET LOCAL ROLE candidate")
            writer.execute(sql.SQL("INSERT INTO {} VALUES ('pending')").format(table))
            held = writer.execute(
                "UPDATE inventory SET available=available-1 WHERE sku='DEMO-BOOK' RETURNING available"
            ).fetchone()
            if held != (7,):
                raise RuntimeError("Failed to establish the open inventory transaction")
            subprocess.run(
                [
                    PG_BIN / "pg_dump",
                    "-h",
                    SOCKET,
                    "-U",
                    "postgres",
                    "--role=candidate",
                    "--format=custom",
                    "--no-owner",
                    "--no-acl",
                    "-f",
                    backup,
                    SOURCE,
                ],
                check=True,
                timeout=60,
            )
            # The writer still sees its private row after the dump completed.
            if writer.execute(sql.SQL("SELECT count(*) FROM {}").format(table)).fetchone() != (2,):
                raise RuntimeError("The test transaction ended before the backup completed")
            writer.rollback()
        with connect("postgres", autocommit=True) as admin:
            target_name = sql.Identifier(target)
            admin.execute(
                sql.SQL("CREATE DATABASE {} OWNER candidate TEMPLATE template0").format(target_name)
            )
            try:
                subprocess.run(
                    [
                        PG_BIN / "pg_restore",
                        "-h",
                        SOCKET,
                        "-U",
                        "postgres",
                        "--role=candidate",
                        "--no-owner",
                        "--no-acl",
                        "--exit-on-error",
                        "--single-transaction",
                        "-d",
                        target,
                        backup,
                    ],
                    check=True,
                    timeout=60,
                )
                verify_snapshot(target, table, baseline, write=True)
            finally:
                admin.execute(sql.SQL("DROP DATABASE {}").format(target_name))
        verify_snapshot(SOURCE, table, baseline, write=False)
    finally:
        with connect(SOURCE) as db:
            db.execute("SET LOCAL ROLE candidate")
            db.execute(sql.SQL("DROP TABLE {}").format(table))
            db.execute(sql.SQL("DROP SCHEMA {}").format(schema))


def main():
    if (
        os.environ.get("SB001_DISPOSABLE_IMAGE_TEST") != "1"
        or Path("/opt/sb001/profile").read_text().strip() != "orderflow"
        or pwd.getpwuid(os.getuid()).pw_name != "postgres"
        or not Path("/var/lib/postgresql/data/sb001/sb001-initialized").is_file()
    ):
        raise RuntimeError("Run this probe only inside the disposable SB-001 OrderFlow image test")
    token = uuid4().hex
    with TemporaryDirectory() as tmp:
        run_backup(f"sb001_probe_{token}", f"sb001_restore_{token}", Path(tmp) / "orderflow.dump")
    print("SB001_LOGICAL_RESTORE_OK")


if __name__ == "__main__":
    main()
