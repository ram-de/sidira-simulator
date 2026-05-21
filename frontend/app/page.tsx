export default function HomePage() {
  return (
    <main style={{ maxWidth: 720, margin: "80px auto", padding: "0 24px" }}>
      <h1 style={{ fontSize: 36, marginBottom: 8 }}>Pythia</h1>
      <p style={{ color: "#555", marginBottom: 32 }}>
        Validate product hypotheses before you build them.
      </p>
      <ul style={{ lineHeight: 1.8 }}>
        <li>
          <a href="/simulations/new">Run a new simulation</a>
        </li>
        <li>
          <a href="/simulations">View past simulations</a>
        </li>
      </ul>
      <p style={{ marginTop: 48, color: "#999", fontSize: 14 }}>
        Backend health:{" "}
        <code>
          GET /health
        </code>{" "}
        on the API service.
      </p>
    </main>
  );
}
