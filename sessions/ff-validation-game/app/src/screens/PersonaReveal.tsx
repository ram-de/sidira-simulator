// PERSONA REVEAL — the shareable "Trader Type" card and the F&F forwarding hook.
//
// CRITICAL: this renders ONLY after ALL outcomes are recorded (App gates it on
// the completed flag). Revealing a persona earlier would contaminate behavior —
// the player would start playing TO the type. This is one of the three named
// data-killers in the spec.
//
// NOTE (scaffold): the type shown here is a lightweight client-side heuristic
// for the forwarding loop's sake. The REAL persona pack is built OFFLINE by
// `run_pipeline` from Table A only (see scripts/export_features.js + README).
// This card is cosmetic and is NOT the engine's prediction.

const TYPES = [
  { name: 'The Closer', blurb: 'You move fast and trust your gut. Decisions, not deliberations.' },
  { name: 'The Analyst', blurb: 'You buy the hints, read the fine print, and back the math.' },
  { name: 'The Skeptic', blurb: 'Hard to sell to. Pressure makes you slower, not faster.' },
];

export function PersonaReveal({ playerId }: { playerId: string }) {
  // Deterministic-but-cosmetic pick from the player id.
  const idx = [...playerId].reduce((a, c) => a + c.charCodeAt(0), 0) % TYPES.length;
  const t = TYPES[idx];
  return (
    <div className="screen">
      <div className="persona">
        <p className="lede">Your Trader Type is…</p>
        <div className="title">{t.name}</div>
        <p className="lede">{t.blurb}</p>
      </div>
      <div className="spacer" />
      <button
        className="btn"
        onClick={() => {
          const url = window.location.origin; // ONE link — no arm, no token in the share URL
          if (navigator.share) void navigator.share({ title: 'Split The Loot', text: `I'm ${t.name}. What are you?`, url });
        }}
      >
        Share & challenge a friend
      </button>
      <p className="statline">Thanks for playing — payouts roll out after the round closes.</p>
    </div>
  );
}
