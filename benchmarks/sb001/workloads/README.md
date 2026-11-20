# SB-001 synthetic workloads

Prepare an isolated OCI build context for each image. The only assessment input is the reviewed candidate tar. The minimal context contains Python and a workspace readiness check. OrderFlow adds the authored starter, hashed Python dependencies, PostgreSQL 16, and Git. Interactive measurements reuse the same OrderFlow image to keep the underlying workload comparable.

```sh
python benchmarks/sb001/workloads/prepare.py minimal /tmp/sb001-minimal
python benchmarks/sb001/workloads/prepare.py orderflow /tmp/sb001-orderflow
docker build -t sb001-minimal /tmp/sb001-minimal
docker build -t sb001-orderflow /tmp/sb001-orderflow
```

Build and publish the prepared contexts through the approved image pipeline. Record the registry digest against the provider template in SB-001 inputs. Provisioning must select the correct image and apply the benchmark profile's CPU, memory, storage, process, lifetime, and deny-by-default network policy. OCI images cannot enforce provider-level quotas or network isolation.

The managed sandbox's init service must start the image entrypoint. The OrderFlow image runs its database supervisor under the unprivileged `postgres` OS account. The broker must run every synthetic workload command and PTY as `candidate`. The database accepts local Unix peers, restricts the `candidate` role to the attempt's OrderFlow database, and caps role connections. The supervisor reads bootstrap SQL from its read-only image layer, supervises PostgreSQL independently of interactive PTYs, and bounds crash restart attempts. Provision each workload with fresh storage owned by the attempt and reclaim it with the sandbox.

Run `/opt/sb001/ready minimal`, `/opt/sb001/ready orderflow`, or `/opt/sb001/ready interactive` under the candidate identity. Success prints exactly `SB001_READY` followed by the workload name. The probe round-trips a workspace file. Database workloads also check PostgreSQL privileges, migrations, seed rows, and the FastAPI health endpoint on a local Unix socket. Measure terminal latency and snapshot recovery separately.

The starter intentionally exhibits the assessed business defects. Its expected failure signatures belong to package validation. Provider correctness measurements should use known-correct synthetic PostgreSQL transactions with invariant assertions. The private reference solution and hidden tests belong only in the trusted evaluator.

`bash benchmarks/sb001/workloads/verify-images.sh` builds both synthetic images and exercises them in disposable development containers. For logical PostgreSQL recovery it holds an inventory change and a marker insertion open during `pg_dump`, restores the backup into a fresh database, and checks the committed marker, original seed balances, migration record and a new committed write. It also checks the source after rollback. Managed-provider snapshot recovery remains a separate live benchmark.
