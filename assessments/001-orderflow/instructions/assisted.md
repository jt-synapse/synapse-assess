# Stage B · Safe retries

You have 40 minutes and access to the platform's AI assistant. Implement retry-safe reservation creation. Add tests that establish how your implementation behaves across concurrent requests and application restarts. Explain how you verified an AI suggestion you used, changed, or rejected.

An optional `Idempotency-Key` header is an opaque, case-sensitive string of 1–128 characters. Without the header, preserve the existing API. Each key belongs to the `POST /reservations` endpoint in this attempt's OrderFlow instance, across all clients and SKUs. Equivalent payloads have identical validated `sku` and integer `quantity`; JSON formatting and field order do not matter.

Persist a successful creation and its original HTTP 201 response together. A concurrent retry waits for the first transaction's outcome. If it committed, replay the same status, ID and body. A committed key reused with a different payload returns HTTP 409 with `{"detail":"IDEMPOTENCY_CONFLICT"}`. Validation failures, unknown SKUs, unavailable inventory and failed transactions leave the key free for a later attempt. If a request committed but its response was lost, retrying after a process restart must recover that success.
