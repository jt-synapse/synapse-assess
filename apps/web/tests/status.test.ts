import assert from "node:assert/strict";
import test from "node:test";
import { getReadiness } from "../lib/status.ts";

test("requests uncached readiness from the configured API", async () => {
  const result = await getReadiness("http://api:8000", async (input, init) => {
    assert.equal(String(input), "http://api:8000/api/v1/health/ready");
    assert.equal(init?.cache, "no-store");
    return Response.json({ status: "ready" });
  });
  assert.deepEqual(result, { status: "ready" });
});

test("reports unavailable for a failed dependency, a malformed response or a network error", async () => {
  for (const response of [
    new Response(null, { status: 503 }),
    Response.json({ status: "unexpected" }),
    new Response("unexpected"),
  ]) {
    assert.equal(await getReadiness("http://api:8000", async () => response), null);
  }
  assert.equal(await getReadiness("http://api:8000", async () => { throw new Error("offline"); }), null);
});
