import { useState } from 'react';
import { postSellerCard } from '../lib/api';

// The "Seller Card" — 3 tap-only demographics, captured POST-game but
// PRE-reveal. These are PRE-treatment demographic features → Table A. Tap-only,
// no text entry. (tenure is faked here as a band; map to tenure_days server-side.)

const AGE = ['18-24', '25-34', '35-44', '45-54', '55+'];
const LOCALE = ['US', 'EU', 'UK', 'APAC', 'Other'];
const TENURE = [
  { label: 'First time here', days: 0 },
  { label: 'Played before', days: 30 },
  { label: 'Old hand', days: 365 },
];

export function SellerCard({ playerId, onDone }: { playerId: string; onDone: () => void }) {
  const [age, setAge] = useState<string | null>(null);
  const [locale, setLocale] = useState<string | null>(null);
  const [tenure, setTenure] = useState<number | null>(null);

  const ready = age && locale && tenure != null;

  function submit() {
    if (!ready) return;
    const device = /Mobi|Android|iPhone/i.test(navigator.userAgent) ? 'mobile' : 'desktop';
    void postSellerCard(playerId, {
      ageBand: age!,
      locale: locale!,
      device,
      tenureDays: tenure!,
    }).finally(onDone);
  }

  return (
    <div className="screen">
      <h2>Your Seller Card</h2>
      <p className="lede">Three taps to stamp your card. (No reveal yet — that&apos;s next.)</p>

      <p className="statline">Age band</p>
      <div className="choices grid">
        {AGE.map((a) => (
          <button key={a} className={`choice ${age === a ? 'selected' : ''}`} onClick={() => setAge(a)}>{a}</button>
        ))}
      </div>

      <p className="statline">Region</p>
      <div className="choices grid">
        {LOCALE.map((l) => (
          <button key={l} className={`choice ${locale === l ? 'selected' : ''}`} onClick={() => setLocale(l)}>{l}</button>
        ))}
      </div>

      <p className="statline">Your history</p>
      <div className="choices">
        {TENURE.map((t) => (
          <button key={t.days} className={`choice ${tenure === t.days ? 'selected' : ''}`} onClick={() => setTenure(t.days)}>{t.label}</button>
        ))}
      </div>

      <div className="spacer" />
      <button className="btn" onClick={submit} disabled={!ready}>Stamp my card</button>
    </div>
  );
}
