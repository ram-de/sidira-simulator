// In-character framing ONLY. NEVER the words "research / study / experiment"
// (kills social-desirability) and NEVER the persona reveal (would contaminate
// behavior). This is the social-game wrapper around a blinded A/B harness.
export function Intro({ onStart }: { onStart: () => void }) {
  return (
    <div className="screen">
      <h1>Split The Loot</h1>
      <p className="lede">
        A quick 5-minute money game. Make your calls, build a pot, and find out your{' '}
        <span className="coins">Trader Type</span> at the end.
      </p>
      <div className="card">
        <p>
          1 in 20 players gets their final pot paid out at <span className="coins">20×</span> —
          real stakes, so play how you actually think.
        </p>
      </div>
      <p className="lede">Taps only. No typing. Let&apos;s go.</p>
      <div className="spacer" />
      <button className="btn" onClick={onStart}>Start playing</button>
    </div>
  );
}
