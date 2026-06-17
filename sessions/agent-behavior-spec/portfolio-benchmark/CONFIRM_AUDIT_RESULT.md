# Class-A confirmatory set — adversarial valence audit result (2026-06-17)

## Headline: the set is well-blinded, AND independently confirmed to be hard the right way
An independent auditor, shown ONLY the neutral arm descriptions (winners stripped:
CONFIRM_BLINDED_FOR_AUDIT.json), guessed each winner blind.
- **Auditor blind-guess accuracy = 6/14 = 0.429 — BELOW chance (0.5).** The wording does
  not leak winners; if anything the cases read counter-intuitively.
- The auditor guessed "treatment" on **10/14** cases and got the 8 control-won cases right
  only **2/8** — i.e. a capable LLM made the SAME pro-change error we expect the simulator
  to make. This is an independent PREVIEW that these cases genuinely stress the pro-change
  tilt: the naive expert/LLM prior is wrong on them (the counter-intuitive property we need).

## Leaks flagged + handled
Auditor flagged 6 residual benefit-word / asymmetric-framing leaks. Note: 4 of the 6
(ascarza, kanuri, algesheimer, lambrecht) pointed toward the LOSER — so they were the
auditor's own pro-change prior surfacing on benefit-ish words, not outcome leaks. Only 2
(dholakia, bing_antimalware) aligned with a correct guess; bing_antimalware (conf 0.65) was
the one genuine strong leak ("injection"/"blocks"/"first-party only").
- **Applied ALL 6 auditor rewrites verbatim** anyway — benefit words could bias the
  SIMULATOR via wording rather than its intrinsic tilt, which would contaminate the
  control-class endpoint. Removing them keeps the endpoint a clean measure of the sim's own
  prior. (Cases: ascarza, kanuri, algesheimer, lambrecht, dholakia, bing_antimalware.)
- 8 cases passed clean (no rewrite): anderson_installment, sale_sign, office_help_widget,
  alibaba, low_default_charity, growthrock, bionicgloves, blivakker. Their auditor guesses
  reflect real-world priors the neutral mechanics legitimately make salient (form friction,
  social proof, anchoring) — that is the case being hard, not a leak.

## Final sealed cases
PORTFOLIO_CASES_CONFIRM.json, canonical SHA-256:
  82d3086ff5abdd75a8b4a1417c9274572923043de462b89cd37cb089ff447566
(held-out probe bing_social_media_integration correctly absent from the scored audit — it is
in held_out_memorization_probe, not scored.)
