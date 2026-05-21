export default function AgentChatPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <main style={{ maxWidth: 720, margin: "80px auto", padding: "0 24px" }}>
      <h1>Chat with agent {params.id}</h1>
      <p>
        Stub. Will host: the agent&apos;s identity card, its initial reaction
        from the simulation (pinned), and a chat interface for follow-up
        questions.
      </p>
      <p style={{ marginTop: 16, color: "#666" }}>
        <strong>Identity continuity:</strong> the agent here is the SAME entity
        that participated in the simulation — frozen identity + frozen initial
        reaction + appendable conversation. Not a re-instantiation from the
        persona template.
      </p>
    </main>
  );
}
