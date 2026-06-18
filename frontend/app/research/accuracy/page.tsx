import type { Metadata } from "next";
import { ConsoleShell } from "@/components/v2";
import "@/styles/v2-theme.css";

// Login-gated research surface (middleware: "/research(.*)" is a protected
// route — the gate + redirect live in middleware.ts, untouched here). The
// customer-facing accuracy & methodology report, honest-null framing. Authored
// as JSX per the repo convention (no markdown runtime). Reskinned into the dark
// "Reading Console" language (styles/v2-theme.css tokens) to match the other
// public surfaces. The internal disclosure-boundary appendix is deliberately
// NOT published here.
export const metadata: Metadata = {
  title: "How we measure Sidira — Accuracy & Methodology",
  description: "How Sidira measures its own accuracy, the benchmarks we run, and what they show.",
  robots: { index: false, follow: false },
};

const SECTION: React.CSSProperties = {
  marginTop: 56,
};

const H2: React.CSSProperties = {
  fontSize: 22,
  fontWeight: 600,
  letterSpacing: "-0.02em",
  lineHeight: 1.15,
  color: "var(--text-hi)",
  margin: "0 0 18px 0",
};

const BODY: React.CSSProperties = {
  fontSize: 16,
  lineHeight: 1.7,
  color: "var(--text)",
  margin: "0 0 18px 0",
};

const LEAD: React.CSSProperties = {
  ...BODY,
  fontSize: 18,
};

const LI: React.CSSProperties = {
  fontSize: 16,
  lineHeight: 1.65,
  color: "var(--text)",
  marginBottom: 12,
};

const STRONG: React.CSSProperties = { fontWeight: 600, color: "var(--text-hi)" };

const MONO_FIGURE: React.CSSProperties = {
  fontFamily: "var(--v2-font-mono)",
  fontSize: 13,
  fontVariantNumeric: "tabular-nums",
  color: "var(--text-hi)",
};

function Term({ children }: { children: React.ReactNode }) {
  return <span style={STRONG}>{children}</span>;
}

const RESULTS: { benchmark: string; tested: string; result: string }[] = [
  {
    benchmark: "Upworthy headline CTR",
    tested: "Which of two headlines earns more clicks",
    result:
      "Reader-roleplay was a flat null (rank-ρ −0.11). The expert-forecaster comparison recovers a weak but real signal (Spearman +0.28, sign accuracy ~0.63 over 300 pre-registered cases) — above chance, still below decision-grade. Headline text alone is a sub-decision-grade ceiling.",
  },
  {
    benchmark: "Hillstrom email RCT",
    tested: "The direction of a real email campaign's effect, and which audience responds more",
    result:
      "Initially predicted the wrong direction; a fix corrected it (direction accuracy to 1.0 at power) and certified the per-segment who-responds-more ranking (rank-ρ +0.42, p=0.01) — pre-registered, and validated end-to-end through the engine.",
  },
  {
    benchmark: "Product-change portfolio",
    tested: "Which version of a real product change wins",
    result:
      "Re-run with the comparative-forecaster: 0.500 (7/14), up from 0.286 but still at chance. It gets cases where the added feature won, but a 'more-is-better' bias persists on counter-intuitive changes where doing less won. No certified signal yet.",
  },
  {
    benchmark: "Metric calibration",
    tested: "Turning a ranking into a calibrated number",
    result:
      "Deliberately left un-fit — no reliable ranking signal yet appeared to calibrate against.",
  },
];

export default function AccuracyReportPage() {
  return (
    <ConsoleShell>
      <article style={{ maxWidth: 760, margin: "0 auto", padding: "56px 24px 128px" }}>
        <header
          style={{
            borderBottom: "1px solid var(--console-line-50)",
            paddingBottom: 32,
            marginBottom: 8,
          }}
        >
          <div
            style={{
              fontFamily: "var(--v2-font-mono)",
              fontSize: 11,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--text-mut)",
              marginBottom: 20,
            }}
          >
            Research &middot; Confidential to signed-in customers
          </div>
          <h1
            style={{
              fontSize: "clamp(2.4rem, 4vw, 2.875rem)",
              fontWeight: 700,
              letterSpacing: "-0.035em",
              lineHeight: 1.06,
              color: "var(--text-hi)",
              margin: 0,
              textWrap: "balance",
            }}
          >
            How we measure Sidira
          </h1>
          <p
            style={{
              fontSize: 17,
              lineHeight: 1.6,
              color: "var(--text-mut)",
              margin: "16px 0 0 0",
            }}
          >
            An accuracy &amp; methodology report. We disclose how we measure, what
            the benchmarks show today, and where the honest limits are.
          </p>
        </header>

        <section style={SECTION}>
          <p style={LEAD}>
            We hold ourselves to a simple standard: a vendor you should trust is one that shows
            you its measurement, including where it falls short. This report does that. Across
            four independent benchmarks the simulator does <Term>not</Term> yet clear a bar we
            would sell as &ldquo;predicts winners.&rdquo; What it does have today is a rigorous,
            auditable measurement program &mdash; and that discipline is the point.
          </p>
        </section>

        <section style={SECTION}>
          <h2 style={H2}>1. The problem</h2>
          <p style={BODY}>
            Online A/B tests are the gold standard for product decisions, but they are slow
            (weeks of live traffic), expensive (you ship to real users to learn), and gated on
            scale (small teams can&rsquo;t power a clean test). Teams want a faster way to ask
            &ldquo;which version is likely to win, and why?&rdquo; <Term>before</Term> committing
            traffic.
          </p>
          <p style={BODY}>
            Sidira simulates panels of audience-grounded agents to generate{" "}
            <Term>directional hypotheses</Term> and surface <Term>weaknesses</Term> ahead of a
            real test. The honest claim is a hypothesis generator, not a digital-clone oracle &mdash;
            and a chat with an agent is a hypothesis aid, never evidence.
          </p>
        </section>

        <section style={SECTION}>
          <h2 style={H2}>2. Why the obvious shortcut fails</h2>
          <p style={BODY}>
            A tempting shortcut is to ask a large language model &ldquo;which version wins?&rdquo;
            We reject that as invalid measurement: it tests the model&rsquo;s <Term>memory</Term>{" "}
            of published case studies, not its <Term>reasoning</Term> about an unseen change. Two
            failure modes shaped our whole evaluation design:
          </p>
          <ul style={{ paddingLeft: 22, margin: "0 0 18px 0" }}>
            <li style={LI}>
              <Term>Memorization.</Term> On famous textbook cases a model can recite the known
              answer while flunking obscure ones &mdash; skill-shaped on the surface, recall
              underneath. We detect this with held-out famous-case probes scored separately.
            </li>
            <li style={LI}>
              <Term>Priors-echoing.</Term> The engine tends to echo whatever prior its framing
              evokes rather than reason case by case. Framed as a marketing nudge it predicts
              &ldquo;people resist being marketed to&rdquo;; framed as a product change it predicts
              &ldquo;the new thing is better.&rdquo; Same engine, opposite bias, flipped by framing
              alone.
            </li>
          </ul>
          <p style={BODY}>
            So we evaluate the <Term>full simulation engine</Term> on a blinded
            control-vs-treatment stimulus (winner hidden, wording neutralized), scoring its
            directional prediction against real experimental ground truth &mdash; never by asking
            a model to name a winner.
          </p>
        </section>

        <section style={SECTION}>
          <h2 style={H2}>3. The evaluation framework</h2>
          <p style={BODY}>
            Every figure in this report is produced under the following discipline. Each control
            was added because it caught a real error of ours &mdash; they are not decorative.
          </p>
          <ul style={{ paddingLeft: 22, margin: 0 }}>
            <li style={LI}>
              <Term>External ground truth.</Term> We grade against real randomized experiments,
              not opinion.
            </li>
            <li style={LI}>
              <Term>Out-of-sample, pre-registered.</Term> Before each run we lock the prediction{" "}
              <em>and</em> the scoring rule into a file, fingerprinted with a cryptographic hash,
              committed before any result is seen. A prediction that turns out wrong in the
              un-flattering direction is therefore credible, not spin.
            </li>
            <li style={LI}>
              <Term>Replication, not just discovery.</Term> A promising number on the data that
              suggested it is only a hypothesis. We re-run locked predictions on fresh cases. If
              the number holds it replicated; if it collapses it was a sample artifact.
            </li>
            <li style={LI}>
              <Term>Null-integrity certificate.</Term> A label-permutation test confirms the
              statistical machinery is well-formed. Passing it is a validity check, not a win.
            </li>
            <li style={LI}>
              <Term>Independent leak audits.</Term> A separate reviewer, shown only the
              neutralized descriptions with winners stripped, tries to guess the winners. If its
              guesses track the truth, our wording leaks and we rewrite. On our hardest set the
              auditor scored below chance.
            </li>
            <li style={LI}>
              <Term>Honest baselines.</Term> A result must beat not just a coin flip but the
              strongest naive constant strategy on that specific set, and is anchored against
              human-expert baselines.
            </li>
            <li style={LI}>
              <Term>No silent truncation.</Term> Every stratum is reported, including the poor and
              underpowered ones.
            </li>
          </ul>
        </section>

        <section style={SECTION}>
          <h2 style={H2}>4. What the benchmarks show today</h2>
          <p style={BODY}>
            The honest standing is mixed. Under our best elicitation, copy and product-change
            benchmarks show weak-to-at-chance signal &mdash; real movement off the earlier nulls,
            but not yet decision-grade (and with two of our own false positives caught before they
            became claims). On the Hillstrom email RCT, after finding and fixing a directional bias,
            the first <Term>certified</Term> directional result &mdash; the per-segment &ldquo;who
            responds more&rdquo; ranking, pre-registered and permutation-tested (rank-&rho;{" "}
            <span style={MONO_FIGURE}>+0.42</span>, p=<span style={MONO_FIGURE}>0.01</span>).
            Magnitudes remain uncalibrated and out of scope.
          </p>
          <div
            style={{
              border: "1px solid var(--console-line-50)",
              borderRadius: "var(--r-panel)",
              overflow: "hidden",
              background: "var(--console-850)",
              boxShadow: "inset 0 1px 0 rgba(255,255,255,0.04)",
              margin: "8px 0 24px 0",
            }}
          >
            {RESULTS.map((row, i) => (
              <div
                key={row.benchmark}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr",
                  gap: 6,
                  padding: "16px 18px",
                  borderTop: i === 0 ? "none" : "1px solid var(--console-line-40)",
                }}
              >
                <div
                  style={{
                    fontFamily: "var(--v2-font-mono)",
                    fontSize: 12,
                    letterSpacing: "0.04em",
                    textTransform: "uppercase",
                    color: "var(--text-hi)",
                    fontWeight: 600,
                  }}
                >
                  {row.benchmark}
                </div>
                <div style={{ fontSize: 14, color: "var(--text-mut)", lineHeight: 1.5 }}>
                  {row.tested}
                </div>
                <div style={{ fontSize: 14.5, color: "var(--text)", lineHeight: 1.55 }}>
                  {row.result}
                </div>
              </div>
            ))}
          </div>

          <p style={BODY}>
            The product-change benchmark is the most instructive, because it shows the discipline
            working in real time:
          </p>
          <ul style={{ paddingLeft: 22, margin: 0 }}>
            <li style={LI}>
              An initial run looked biased toward &ldquo;the change wins.&rdquo; A self-audit found
              the cause was <Term>our own wording leaking the answer</Term>, not a model property.
              We neutralized it and re-sealed.
            </li>
            <li style={LI}>
              An expanded set scored below chance overall, but a blind split suggested a narrow
              skill on <Term>substantive</Term> changes survived while <Term>cosmetic</Term> ones
              were blank &mdash; a promising <span style={MONO_FIGURE}>0.70</span>.
            </li>
            <li style={LI}>
              The confirmatory test &mdash; 14 fresh substantive cases, balanced, independently
              blind-audited, prediction sealed first &mdash; came back{" "}
              <span style={MONO_FIGURE}>0.286 (4/14)</span>, below chance. The{" "}
              <span style={MONO_FIGURE}>0.70</span> did not replicate; it was favorable composition,
              not skill.
            </li>
          </ul>
          <p style={{ ...BODY, marginTop: 18 }}>
            A sharper diagnostic fell out: the residual bias is <Term>more-is-better</Term>, not
            pro-change &mdash; the engine tends to back the bigger, richer, more-featured option
            regardless of which one actually won, and the effect sizes are tiny. When the winning
            change was a <em>reduction</em>, it backed the status quo.
          </p>
        </section>

        <section style={SECTION}>
          <h2 style={H2}>5. Limits &amp; responsible use</h2>
          <ul style={{ paddingLeft: 22, margin: 0 }}>
            <li style={LI}>
              The engine is a <Term>directional hypothesis generator and weakness surfacer</Term>,
              not a calibrated predictor. Absolute metric calibration is unproven and on the
              roadmap, not claimed.
            </li>
            <li style={LI}>
              Where it shows promise on substantive product-change direction, that does{" "}
              <Term>not</Term> generalize to subtle/cosmetic changes or marketing nudges.
            </li>
            <li style={LI}>
              Chat with an agent is a hypothesis aid, <Term>never</Term> evidence; agents are a
              diverse, audience-grounded panel, not clones of real people.
            </li>
            <li style={LI}>
              The strongest path to a proven positive is validation on a customer&rsquo;s own real
              data with a change whose outcome is already known &mdash; published case studies have
              been exhausted as a ground-truth source.
            </li>
          </ul>
        </section>

        <section style={SECTION}>
          <h2 style={H2}>6. The takeaway</h2>
          <p style={BODY}>
            We pre-register predictions, fingerprint them before we look at results, run
            independent adversarial leak audits, demand replication on fresh data, and report the
            nulls. That discipline caught two of our own false positives before they could become
            claims.
          </p>
          <p style={BODY}>
            The product&rsquo;s present, defensible value is <Term>fast, diverse,
            audience-grounded directional hypotheses and weakness-surfacing</Term> to help you
            prioritize what to test &mdash; with honest limits, and a measurement program you can
            audit. When we can prove more, we will publish it here the same way: pre-registered,
            and exactly as the numbers come back.
          </p>
        </section>

        <footer
          style={{
            marginTop: 64,
            paddingTop: 24,
            borderTop: "1px solid var(--console-line-50)",
            fontSize: 13,
            lineHeight: 1.6,
            color: "var(--text-mut)",
          }}
        >
          Every figure above is drawn from a sealed, pre-registered run. Methodology is described
          at the level a customer needs to trust the measurement; the internals of how Sidira
          generates a prediction are not part of this report.
        </footer>
      </article>
    </ConsoleShell>
  );
}
