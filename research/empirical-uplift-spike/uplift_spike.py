"""
Empirical-uplift spike — a "completely different angle" on Sidira accuracy.

Thesis under test:
    For a *feature-expressible* product change, an empirical causal/uplift model
    fit on the customer's OWN behavioral logs can recover the true effect SIGN
    where a naive "more-is-better" read (the LLM's uncontrolled prior) gets it
    WRONG -- and it can do so today, with no LLM call, no real-money panel.

We also test the BOUND: when the true driver is unobserved (out of the feature
store's support), even causal ML fails -> that is the LLM engine's territory.

Self-contained: a Streamly-like 6-segment synthetic feature store with a KNOWN
(by-construction) heterogeneous treatment effect, so we have ground truth.

Change under test ("autoplay-next on the home feed"):
  helps low-engagement users (discovery) but HURTS high-engagement users
  (disrupts their curated flow -> churn). Because high-engagement users have a
  high retention base (more to lose), the NET 30-day-retention effect is
  NEGATIVE -- the opposite of the obvious "more engagement = good" prior.

Assignment is OBSERVATIONAL & CONFOUNDED (autoplay was rolled out to already-
engaged users first), exactly like a real product log -- so naive diff-in-means
is biased toward the wrong (positive) sign.
"""
import numpy as np
from sklearn.linear_model import LogisticRegression

RNG = np.random.default_rng(20260627)
N = 2500  # match the Streamly fixture size

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))

# ---------------------------------------------------------------------------
# 1. Streamly-like feature store: 6 segments, observed covariates
# ---------------------------------------------------------------------------
SEGMENTS = [
    # name           share  mean_engagement
    ("Binger",        0.18,  0.85),
    ("Curator",       0.12,  0.78),
    ("Daily-Habit",   0.20,  0.62),
    ("Weekender",     0.22,  0.45),
    ("Drifter",       0.18,  0.30),
    ("Dormant-ish",   0.10,  0.15),
]

seg_idx = RNG.choice(len(SEGMENTS), size=N, p=[s[1] for s in SEGMENTS])
seg_mean_eng = np.array([SEGMENTS[i][2] for i in seg_idx])

# observed covariates (these live in the feature store)
engagement = np.clip(seg_mean_eng + RNG.normal(0, 0.07, N), 0.01, 0.99)
tenure_m   = np.clip(RNG.gamma(2.0, 6.0, N), 0, 60)
plan_tier  = RNG.integers(0, 3, N)                 # 0 free, 1 std, 2 premium
content_div= np.clip(engagement * 0.6 + RNG.normal(0, 0.15, N), 0, 1)
age_band   = RNG.integers(0, 5, N)

# latent driver that is NOT in the feature store (used only in Scenario 2)
brand_affinity = np.clip(RNG.normal(0.5, 0.2, N), 0, 1)

X = np.column_stack([engagement, tenure_m / 60.0, plan_tier / 2.0, content_div, age_band / 4.0])
FEAT_NAMES = ["engagement", "tenure", "plan_tier", "content_div", "age_band"]

# ---------------------------------------------------------------------------
# 2. Potential outcomes (ground truth) for a scenario
# ---------------------------------------------------------------------------
def potential_outcomes(tau_logit, base_extra=0.0):
    """Given a per-user treatment effect on the retention logit, return
    (p0, p1, y0, y1) — control/treated retention probs and sampled outcomes.
    `base_extra` lets a scenario push an UNOBSERVED driver into the baseline."""
    base_logit = (-0.4 + 3.2 * engagement + 0.6 * (tenure_m / 60.0)
                  + 0.4 * (plan_tier / 2.0) + base_extra)
    p0 = sigmoid(base_logit)
    p1 = sigmoid(base_logit + tau_logit)
    y0 = (RNG.random(N) < p0).astype(int)
    y1 = (RNG.random(N) < p1).astype(int)
    return p0, p1, y0, y1

def assign_treatment(propensity_logit):
    e = sigmoid(propensity_logit)
    T = (RNG.random(N) < e).astype(int)
    return T, e

# ---------------------------------------------------------------------------
# 3. Estimators
# ---------------------------------------------------------------------------
def naive_diff_in_means(T, Y):
    return Y[T == 1].mean() - Y[T == 0].mean()

def t_learner(Xc, T, Y):
    """Two-model uplift: fit P(Y|X) on treated and control separately,
    predict both potential outcomes for everyone, average the difference."""
    m1 = LogisticRegression(max_iter=2000).fit(Xc[T == 1], Y[T == 1])
    m0 = LogisticRegression(max_iter=2000).fit(Xc[T == 0], Y[T == 0])
    p1 = m1.predict_proba(Xc)[:, 1]
    p0 = m0.predict_proba(Xc)[:, 1]
    cate = p1 - p0
    return cate.mean(), cate

def ipw_ate(Xc, T, Y):
    """Inverse-propensity-weighted ATE (propensity from observed covariates)."""
    ps = LogisticRegression(max_iter=2000).fit(Xc, T).predict_proba(Xc)[:, 1]
    ps = np.clip(ps, 0.02, 0.98)
    return (T * Y / ps - (1 - T) * Y / (1 - ps)).mean()

# ---------------------------------------------------------------------------
# 4. Scenario runner
# ---------------------------------------------------------------------------
def run(name, tau_logit, propensity_logit, Xobs, blurb, base_extra=0.0):
    p0, p1, y0, y1 = potential_outcomes(tau_logit, base_extra)
    true_ate = (p1 - p0).mean()
    T, _ = assign_treatment(propensity_logit)
    Y = np.where(T == 1, y1, y0)        # observed outcome only

    naive   = naive_diff_in_means(T, Y)
    tl, cate= t_learner(Xobs, T, Y)
    ipw     = ipw_ate(Xobs, T, Y)
    prior   = +1                         # "more engagement is good" -> predicts +

    def line(label, est, has_sign=True):
        sign_ok = "—"
        if has_sign:
            sign_ok = "OK " if np.sign(est) == np.sign(true_ate) else "WRONG"
        err = f"{abs(est-true_ate)*100:5.2f}pp" if has_sign else "  —  "
        return f"  {label:<34} {est*100:+6.2f}pp   sign:{sign_ok:<6} |Δ|:{err}"

    print(f"\n{'='*74}\nSCENARIO: {name}\n{blurb}\n{'-'*74}")
    print(f"  TRUE ATE (oracle, by construction)  {true_ate*100:+6.2f}pp   "
          f"({'helps' if true_ate>0 else 'HURTS'} retention)")
    print(f"  treated share {T.mean()*100:.0f}%  |  "
          f"mean engagement treated {engagement[T==1].mean():.2f} vs control {engagement[T==0].mean():.2f}")
    print()
    print("  PRIOR-DRIVEN (stands in for the LLM's uncontrolled prior):")
    print(line("more-is-better prior", prior*abs(true_ate) if true_ate>0 else prior*0.04, True))
    print("  EMPIRICAL on the feature store (no LLM):")
    print(line("naive diff-in-means (confounded)", naive))
    print(line("IPW (propensity-adjusted)", ipw))
    print(line("T-learner / uplift (covariate-adj)", tl))
    return dict(name=name, true_ate=true_ate, naive=naive, ipw=ipw, t_learner=tl)

# ---------------------------------------------------------------------------
# SCENARIO 1 — feature-expressible change, confounded log  (the WIN)
# ---------------------------------------------------------------------------
# tau: +0.9 for the least engaged, sliding to strongly negative for the most.
tau1 = 0.9 - 2.6 * engagement
prop1 = -1.4 + 2.8 * engagement           # autoplay rolled out to engaged users
r1 = run(
    "S1 — feature-expressible, observational/confounded log",
    tau1, prop1, X,
    "Autoplay helps casual users, hurts power users; rolled out to engaged users\n"
    "first. The effect driver (engagement) IS in the feature store.")

# ---------------------------------------------------------------------------
# SCENARIO 2 — UNOBSERVED CONFOUNDER on the baseline  (the BOUND -> LLM territory)
# ---------------------------------------------------------------------------
# True effect: autoplay modestly HURTS everyone (constant negative). But a latent
# loyalty (brand_affinity) NOT in the feature store both (a) lifts baseline
# retention and (b) drove who got autoplay first. Adjusting on observed columns
# cannot see it -> every empirical estimate is biased toward the wrong sign.
tau2  = np.full(N, -0.22)                            # autoplay MILDLY hurts all
prop2 = -1.8 + 4.2 * brand_affinity                 # strongly: loyal users got it first
base2 = 3.4 * (brand_affinity - 0.5)                # loyalty strongly lifts baseline
r2 = run(
    "S2 — UNOBSERVED confounder (real driver not in the feature store)",
    tau2, prop2, X,
    "Autoplay mildly hurts everyone, but a latent loyalty that lifts retention AND\n"
    "drove rollout is NOT a column. Empirical adjustment can only use what it sees.",
    base_extra=base2)

# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------
def verdict(r):
    naive_ok = np.sign(r['naive']) == np.sign(r['true_ate'])
    tl_ok    = np.sign(r['t_learner']) == np.sign(r['true_ate'])
    return naive_ok, tl_ok

n1_ok, t1_ok = verdict(r1)
n2_ok, t2_ok = verdict(r2)
print(f"\n{'='*74}\nVERDICT\n{'-'*74}")
print(f"  S1 (feature-expressible): naive read {'right' if n1_ok else 'WRONG'} sign, "
      f"uplift ML {'RIGHT' if t1_ok else 'wrong'} sign")
print(f"      -> empirical route {'WINS where the obvious prior fails' if (t1_ok and not n1_ok) else 'no clear win'}.")
print(f"  S2 (driver unobserved):   uplift ML {'right' if t2_ok else 'WRONG'} sign")
print(f"      -> empirical route {'cannot help; hand the baton to the LLM' if not t2_ok else 'still ok'}.")
print(f"\n  Read: Sidira can give a provably-accurate, LLM-free prediction for the")
print(f"  feature-expressible slice (S1). The LLM engine earns its keep on S2.\n")
