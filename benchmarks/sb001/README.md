# SB-001 · Managed sandbox benchmark

The benchmark compares E2B and Daytona using the same authored workload and matched resource profiles. The initial repository contains tools and fixture tests. The provider scorecard requires real measurements.

## Prepare and measure

1. Build the minimal and OrderFlow images using the [workload preparation commands](workloads/README.md). Record each published image digest and the corresponding private, immutable provider template. The interactive profile uses the OrderFlow image.
2. Configure the standard profile at 2 vCPUs, 4 GiB RAM and at least 8 GiB storage, or the stress profile at 4 vCPUs, 8 GiB RAM and at least 16 GiB storage. Record the actual allocation, process limits, region, and enforced resource lifetime for each provider. Keep the source mapping and measurements together.
3. Validate the configuration offline with `python -m benchmarks.sb001.run CONFIG.json`. Run the [measurement driver](DRIVERS.md) against approved accounts to collect JSON Lines. Cold and warm series must reflect a known preparation state. Record errors, timeouts, cleanup outcomes and incomplete attempts.
4. For each provider and configuration, collect 30 cold and 30 warm samples. Run the separate 110-minute interactive scenario and retain its PTY measurements. A configured network policy, a successful readiness check, or a short-lived instance alone cannot verify isolation or longevity.
5. Summarize lifecycle measurements from the repository root:

```sh
python -m benchmarks.sb001.report measurements.jsonl
```

The report groups by provider, region, SDK version, image digest, resource profile, workload, and start kind. Times are in milliseconds. The median, nearest-rank P95, and maximum use observed durations. Incomplete attempts and unverified cleanup remain visible in the denominator. A group meets the initial lifecycle targets when it has at least 30 observations, P95 readiness is at most 30 seconds cold or 10 seconds warm, P95 deletion is at most 30 seconds, and every attempt completed with confirmed cleanup. A lifecycle result alone cannot select a provider.

## Reconcile cost

Use one USD billing period and one matched assessment cohort per input. Supply one reconciled row per attempt with the columns below. Use actual billed usage, including usage from failed and abandoned attempts. Allocate the cohort's share of subscription or base fees once on the command line. Keep AI, transcription and human review costs separate.

```csv
run_id,outcome,compute_usd,storage_usd,network_usd,snapshot_usd
```

`outcome` is `completed`, `failed`, or `abandoned`. Use the documented 90-minute assessment plus operational buffer to measure assessment economics. Short provisioning samples measure startup expense. They cannot supply the completed-assessment denominator.

```sh
python -m benchmarks.sb001.cost invoice-rows.csv --allocated-period-fees-usd "$ALLOCATED_FEES_USD"
```

The result includes usage by outcome, allocated period fees, and total cost divided by completed assessments. The provisional target is USD 5 per completed assessment.

## Selection evidence

Retain the raw measurements and provider bills. Document PostgreSQL transaction correctness, restart and application-consistent recovery during writes, restored source integrity, response to lease expiry or interrupted provisioning, terminal reconnect and revocation, hidden grader isolation, and observed resource and network containment. Verify the database-free image separately.

Record each mandatory gate as passed, failed, or unmeasured and cite its evidence. Apply the weighted scorecard only after all mandatory gates pass. The proposed selection threshold is 80/100 overall, at least 3/5 in each category, with cost and operational complexity as tie-breakers when candidate experience is comparable. Record the decision in a provider-selection ADR. [SB-001 scorecard and gates](../../remaining_decisions.md#7-provider-scorecard)
