# Running one lifecycle sample

Keep the provider SDKs in a separate benchmark environment. The driver checks the installed distribution version before making a request. The pinned distributions are [E2B 2.64.0](https://pypi.org/project/e2b/2.64.0/) and [Daytona 0.232.0](https://pypi.org/project/daytona/0.232.0/).

Use this configuration shape with actual release values:

```json
{
  "provider": "daytona",
  "region": "us",
  "template": "published-private-snapshot-name",
  "profile": "standard",
  "workload": "orderflow",
  "image_digest": "sha256:<replace with the measured OCI image digest>",
  "start_kind": "cold"
}
```

Run `python -m benchmarks.sb001.run CONFIG.json` from the repository root for offline validation. In an approved benchmark account, install the matching pin and configure its official SDK credentials outside the template. Run `python -m benchmarks.sb001.run CONFIG.json --measure measurements.jsonl` to allocate one sandbox. This command appends one JSON record, including failed readiness and unverified deletion. The exit status is successful only after both checks pass.

Use the immutable E2B template ID or release-specific Daytona snapshot created from the digest. Record the provider's template-to-image mapping, resource limits and region in the benchmark evidence. The provider template supplies the selected resource profile, a nonprivileged `candidate` account and the fixed `/opt/sb001/ready` binary or script. E2B region comes from the approved account/template placement. The operator supplies the cold/warm classification based on the provider pool's actual preparation. Both paths allocate a fresh sandbox. A cache state that cannot be established makes the series unsuitable for cold/warm comparison.

The driver requests denied outbound access, private ingress and a five-minute wall-clock lifetime. It measures request-to-workload-readiness, including a remote command as `candidate`. That command must exit zero and emit exactly `SB001_READY <workload>`. The OrderFlow image checks its actual database and seed. Deletion latency ends only after the provider confirms the resource is absent or destroyed. An ambiguous creation with no discoverable resource is recorded with unverified cleanup. The SDK request carries the run ID so the account operator can reconcile interrupted runs. The volatile controller's stderr also records the run ID before provisioning. A forcibly killed controller may require reconciliation against that ID and the provider lease. [E2B SDK](https://github.com/e2b-dev/E2B/tree/main/packages/python-sdk) · [Daytona lifecycle](https://www.daytona.io/docs/en/sandboxes/)

This short probe covers lifecycle timing only. SB-001 still requires the 110-minute longevity run, end-to-end PTY, resource isolation and cleanup evidence, application-consistent recovery, concurrency tests, and measured billing before selecting a provider.

For the separate longevity and PTY measurement, set `workload` to `interactive` and supply both `--measure measurements.jsonl` and `--interactive-detail pty.jsonl`. The main-thread POSIX runner requests a two-hour lease, performs the same readiness check, then records 110 minutes of synthetic interaction on the same sandbox. The two output paths must differ. The lifecycle row retains the initial readiness latency if the longer probe fails. Inspect the detail output for the PTY results.

The runner creates an exclusive, durable intent journal at `RESULTS.jsonl.runs/<run-ID>.jsonl` before allocating. This tracks ownership and the acknowledged provider ID outside the sandbox. For an interrupted run, invoke `python -m benchmarks.sb001.run CONFIG.json --reconcile RESULTS.jsonl --run-id RUN_ID`. Use the same isolated benchmark account, region and configuration. The command refuses an active local run. It verifies the run label before removing a recoverable resource and appends a missing failed result for an interrupted attempt. Repeating reconciliation preserves existing measurement rows and keeps subsequent cleanup observations in the journal. Provider TTL still applies if the controller never returns.

The interactive detail measures provider PTY latency and continuity. Browser rendering latency and stage-broker revocation are verified separately with the integrated IDE and session broker.

Recovery of an interrupted write preserves its unfinished bytes in a sibling `.partial` file before restoring JSONL framing. When the original completion record is missing, the result records an incomplete attempt with null timings. A later provider absence or deletion is captured in the run journal with reconciliation duration.
