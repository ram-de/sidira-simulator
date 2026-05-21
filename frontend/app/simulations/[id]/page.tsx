export default function SimulationDetailPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <main style={{ maxWidth: 720, margin: "80px auto", padding: "0 24px" }}>
      <h1>Simulation {params.id}</h1>
      <p>
        Stub. Will host: confidence score, weakness diagnosis, refinement
        suggestions, and a list of the agents that participated. Each agent is
        clickable → opens a chat with that exact agent (not a re-instantiation).
      </p>
    </main>
  );
}
