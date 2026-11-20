import type { Readiness } from "@synapse/contracts";

export async function getReadiness(
  apiOrigin: string,
  request: typeof fetch = fetch,
): Promise<Readiness | null> {
  try {
    const response = await request(new URL("/api/v1/health/ready", apiOrigin), {
      cache: "no-store",
      signal: AbortSignal.timeout(5_000),
    });
    if (!response.ok) return null;
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "status" in body && body.status === "ready") {
      return { status: "ready" };
    }
  } catch {
    // A status page must still render while the trusted API is unavailable.
  }
  return null;
}
