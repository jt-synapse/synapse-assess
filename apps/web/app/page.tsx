import { getReadiness } from "../lib/status";

export const dynamic = "force-dynamic";

export default async function StatusPage() {
  const readiness = await getReadiness(process.env.API_ORIGIN ?? "http://127.0.0.1:8000");
  return (
    <main>
      <header>Synapse Assess</header>
      <h1>System status</h1>
      <dl>
        <dt>Assessment control plane</dt>
        <dd className={readiness ? "available" : "unavailable"}>
          <span aria-hidden="true" className="indicator" />
          {readiness ? "Ready" : "Unavailable"}
        </dd>
      </dl>
    </main>
  );
}
