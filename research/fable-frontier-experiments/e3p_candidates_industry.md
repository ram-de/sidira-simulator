# E3-P Candidate Audit Log — Source (2): Kohavi publications + first-party engineering blogs

Assembled 2026-07-01, after prereg seal, per PREREG_E3P_BACKLOG_PREVALENCE.md "Case sourcing".

**BLINDING NOTE:** Lines for INCLUDED candidates are outcome-free. Exclusion reasons for
EXCLUDED candidates may unavoidably reference outcome-validity issues (e.g., "result was an
instrumentation artifact") — these describe excluded cases only. The prediction runner should
nonetheless not read this file until predictions are sealed (defense in depth).

**Assembly rule followed:** sources processed in a fixed order; within each collection, every
experiment encountered was logged in order of appearance; assembly stopped when the 20-case
target ceiling was reached (per tasking: target 15–20, stop at target). Remaining fixed-list
sources not consulted are listed at the end as a limitation.

## Sources consulted (in order)

1. Kohavi, Deng, Longbotham, Xu — "Seven Rules of Thumb for Web Site Experimenters", KDD 2014. https://exp-platform.com/Documents/2014%20experimentersRulesOfThumb.pdf (full text read)
2. Kohavi, Deng, Frasca, Longbotham, Walker, Xu — "Trustworthy Online Controlled Experiments: Five Puzzling Outcomes Explained", KDD 2012. https://exp-platform.com/Documents/puzzlingOutcomesInControlledExperiments.pdf (full text read)
3. Kohavi & Thomke — "The Surprising Power of Online Experiments", HBR Sept–Oct 2017. https://hbr.org/2017/09/the-surprising-power-of-online-experiments (fetched; one concrete example, duplicate of Bing ad-titles class; see C48)
4. Netflix TechBlog — "What is an A/B Test?" (Decision Making at Netflix series). https://netflixtechblog.com/what-is-an-a-b-test-b08cc1b57962 (fetched)
5. First Round Review — "The Tenets of A/B Testing from Duolingo's Master Growth Hacker" (interview with Gina Gotthilf, VP Growth, Duolingo). https://review.firstround.com/the-tenets-of-a-b-testing-from-duolingos-master-growth-hacker/ (fetched twice, second time to verify quotes verbatim; secondhand-with-concrete-details tier — interview transcript with a first-party operator)

## Candidate log

| # | Source | Candidate (one line) | Decision |
|---|--------|----------------------|----------|
| C01 | KDD2014 §Rule1 | Colleen Szot infomercial phone-line copy change (via Yes! book) | EXCLUDED — not an online controlled experiment; TV anecdote |
| C02 | KDD2014 §Rule1 | Doctor FootCare: coupon-code field removed at checkout (via Eisenberg/ClickZ) | EXCLUDED — third-party anecdote cited skeptically by the source itself; no stats/rigor available |
| C03 | KDD2014 §Rule1 | "$300 Million Button": registration requirement removed at checkout (via Spool/UIE) | EXCLUDED — retailer anonymized; consultant account; unverifiable |
| C04 | KDD2014 §Rule1 | MSN UK home page (Aug 2008): Hotmail link opens in new tab vs same tab, ~900k users | INCLUDED → ind_01 |
| C05 | KDD2014 §Rule1 | MSN US (Jun 2010): same Hotmail new-tab treatment on 2.7M US users | EXCLUDED — replication of ind_01's treatment on a different population; duplicate/correlated case |
| C06 | KDD2014 §Rule1 | MSN US (Apr 2011): home-page search results open in new tab/window, 12M+ users | INCLUDED → ind_02 |
| C07 | KDD2014 §Rule1 | Bing (2013): CSS font-color shade changes on SERP (title blue / caption green / body black) | INCLUDED → ind_03 (limitation: write-up concretely describes one variant from a set of color experiments) |
| C08 | KDD2014 §Rule1 | Amazon (2004): credit-card offer moved from home-page slot to shopping-cart add page with savings math | INCLUDED → ind_04 |
| C09 | KDD2014 §Rule1 | Bing: override third-party DOM modification (malware-injected ads) for affected users, 3.8M triggered users | INCLUDED → ind_05 |
| C10 | KDD2014 §Rule1 | Bing: "two other small changes, which are confidential" (ad revenue) | EXCLUDED — no description (confidential); insufficient description |
| C11 | KDD2014 §Rule2 | Microsoft Office Online: page redesign with stronger call-to-action + price shown; metric = clicks on revenue links | INCLUDED → ind_06 |
| C12 | KDD2014 §Rule2 | Bing: additional JavaScript added to SERP ("more clicks from a slower page") | EXCLUDED — reported click movement attributed to click-beacon instrumentation fidelity, not real user behavior; no valid behavioral truth |
| C13 | KDD2014 §Rule2 | Bing Edge CDN: beacon-based vs redirect-based click tracking | EXCLUDED — instrumentation-fidelity experiment; primary quantity is click-loss rate, not a user-behavior product metric |
| C14 | KDD2014 §Rule2 | MSN→Bing auto-suggest: new suggestion algorithm on MSN search box | EXCLUDED — result invalidated: new code issued two searches per user selection (instrumentation/behavior artifact) |
| C15 | KDD2014 §Rule3 | Google (via Marissa Mayer Web 2.0 talk): 10 → 30 search results per page | INCLUDED → ind_07 (limitation: secondhand account of a first-party talk; latency confound noted in source) |
| C16 | KDD2014 §Rule4 | Bing: deliberate server-side slowdown (+100ms / +250ms, 10% of users each, 2 weeks) | INCLUDED → ind_08 |
| C17 | KDD2014 §Rule4 | Google (Brutlag, Google Research blog): 100–400ms artificial delay to search results page | INCLUDED → ind_09 (first-party blog: googleresearch.blogspot.com/2009/06/speed-matters.html) |
| C18 | KDD2014 §Rule4 | Bing: 20 results instead of 10 with an additional mainline ad | EXCLUDED — one-sentence account of a bundled/compound arm; ambiguous which arm was measured |
| C19 | KDD2014 §Rule4 | Amazon (via Greg Linden "Make Data Useful"): +100ms page delay | INCLUDED → ind_10 (limitation: retrospective talk/slide account by a former insider; thin detail) |
| C20 | KDD2014 §Rule4 | Bing: right-pane ("snapshot") elements delayed by an additional 250ms, ~20M users | INCLUDED → ind_11 |
| C21 | KDD2014 §Rule5 | Bing: related-searches block removed from SERP right column, 10M+ users | INCLUDED → ind_12 |
| C22 | KDD2014 §Rule5 | Bing: inline related searches pinned to bottom of page below bottom ads, 5M+ users | INCLUDED → ind_13 |
| C23 | KDD2014 §Rule5 | Bing: SERP truncated to 4 algorithmic results on deep-link/navigational queries, 8M triggered users | INCLUDED → ind_14 |
| C24 | KDD2014 §Rule5 | Bing: on back-button/reissue, extend SERP to 20 results (vs 14) and remove related searches, 3M+ triggered users | INCLUDED → ind_15 |
| C25 | KDD2014 §Rule5 | Bing: ad background color change on SERP, 10M+ users | INCLUDED → ind_16 (limitation: specific color values not disclosed) |
| C26 | KDD2014 §Rule6 | LinkedIn Unified Search (2013): first experiment with all components lumped (unified search + landing-page overhaul) | INCLUDED → ind_17 (limitation: bundled multi-component treatment, noted in source) |
| C27 | KDD2014 §Rule6 | LinkedIn Contacts page: new contacts feature | EXCLUDED — experiment invalidated by whitelist/eligibility bug (treatment users removed from experiment after first exposure) |
| C28 | KDD2014 §Rule3 | Neil Patel: "free trial" vs "money back guarantee" wording claim | EXCLUDED — third-party listicle claim; no experiment details or stats |
| C29 | KDD2014 §Rule3 | Joshua Porter: "Red Beats Green" call-to-action button | EXCLUDED — third-party claim without concrete stats; source itself flags non-generality |
| C30 | KDD2014 §Rule3 | Dr. James Lind (1747): citrus vs regular diet for scurvy | EXCLUDED — historical medical trial, not an online product A/B |
| C31 | KDD2012 §1 | MSN Real Estate "Find a home" widget: 6 design variants, OEC = revenue/user | EXCLUDED — multi-variant test; collapsing to the binary control/treatment schema requires assembler arm selection that is outcome-informed (blinding hazard); no outcome-neutral binarization |
| C32 | KDD2012 §3.1 | Bing: bug produced very degraded algorithmic results in an experiment | EXCLUDED — accidental treatment (bug), not a deliberate product change; treatment severity unspecified |
| C33 | KDD2012 §3.2 | Bing: related-search click updates page in place instead of navigating to new URL | EXCLUDED — reported feature-usage movement attributed to click-beacon loss artifact |
| C34 | KDD2012 §3.2 | MSN Hotmail new-tab reanalysis (click-tracking discussion) | EXCLUDED — reanalysis of C04/ind_01, not a new case (analysis noted in truths-file notes for ind_01) |
| C35 | KDD2012 §3.5 | Bing: unnamed experiment with counterintuitive movements on unrelated metrics (carryover-effect illustration) | EXCLUDED — treatment never described; insufficient description |
| C36 | KDD2012 §3.3 | Bing: A/A test cumulative-effect trend example | EXCLUDED — A/A test; no treatment |
| C37 | Web-search summary of Kohavi survey (DMKD 2009) | Coach (retailer): vendor-run test of a new site search engine ("200%" claim) | EXCLUDED — vendor-proof anecdote in secondhand summary; primary source not consulted; no concrete arms/metric detail |
| C38 | Netflix TechBlog (series) | Netflix: "Top 10 in [country]" row added to member homepage | INCLUDED → ind_18 |
| C39 | Netflix TechBlog (search result, not opened) | Netflix: artwork selection via A/B testing (methodology post) | EXCLUDED — not evaluated (target ceiling nearly reached; post is methodology-focused per title/summary) |
| C40 | First Round Review (Gotthilf interview) | Duolingo: red badge dot on app icon | INCLUDED → ind_19 (limitation: interview account; numbers verified verbatim in article text) |
| C41 | First Round Review (Gotthilf interview) | Duolingo: delayed sign-up (soft wall; lesson before sign-up; "Later" vs "Discard my progress") | INCLUDED → ind_20 (limitation: interview account; numbers verified verbatim) — **target of 20 reached; assembly stopped** |
| C42 | First Round Review (Gotthilf interview) | Duolingo: streak notification timing (23.5h) | EXCLUDED — not evaluated; target ceiling reached before this item |
| C43 | First Round Review (Gotthilf interview) | Duolingo: notification copy personalization | EXCLUDED — not evaluated; target ceiling reached |
| C44 | First Round Review (Gotthilf interview) | Duolingo: Weekend Amulet streak protection | EXCLUDED — not evaluated; target ceiling reached |
| C45 | First Round Review (Gotthilf interview) | Duolingo: achievement badges v1 ("You signed up") | EXCLUDED — not evaluated; target ceiling reached |
| C46 | First Round Review (Gotthilf interview) | Duolingo: achievement badges v2 (meaningful badges collection) | EXCLUDED — not evaluated; target ceiling reached |
| C47 | First Round Review (Gotthilf interview) | Duolingo: in-app coach / growth-mindset encouragement copy | EXCLUDED — not evaluated; target ceiling reached |
| C48 | HBR 2017 (Kohavi & Thomke) | Bing: ad headline display change (longer ad titles) | EXCLUDED — encountered while sourcing; article gives revenue delta but arm descriptions too thin in the free text to translate ("changed the way ad headlines display"); also overlaps the confidential-changes class (C10) |

## Counts

- Candidates logged: 48
- INCLUDED: 20 (ind_01 … ind_20)
- EXCLUDED: 28

## Assembly limitations

1. **Inline-outcome exposure (prereg-anticipated):** all sources state outcomes inline with descriptions; the assembler read outcomes while extracting descriptions. Mitigation per prereg: descriptions were recorded neutrally, no outcome words or directional hints were written into `e3p_backlog_industry.json`, and truths were written only to `e3p_truths_industry.json`.
2. **Kohavi-collection skew:** the two KDD papers are teaching collections that over-represent Bing/Microsoft (13 of 20 included cases are Microsoft properties) and latency experiments (4 of 20). Every qualifying experiment in each collection was taken in order — no interestingness filtering — but the population is not a random draw from any company's backlog.
3. **Sources on the fixed list NOT consulted (target ceiling reached first):** Kohavi "Online Controlled Experiments at Large Scale" (KDD 2013, consulted only via its citation inside KDD 2014), "Unexpected Results in Online Controlled Experiments" (SIGKDD Expl. 2011), "Controlled experiments on the web: survey" (DMKD 2009), "Trustworthy Online Controlled Experiments" book, Microsoft ExP blog, Booking.com, Airbnb, LinkedIn engineering, Pinterest, Etsy blogs. If E3-P later needs N ≥ 25 from this source class, resume from these in this order.
4. **Secondhand cases:** ind_07 (Google 30 results — Kohavi/Linden accounts of a Mayer talk), ind_10 (Amazon 100ms — Linden retrospective), ind_19/ind_20 (Duolingo — First Round interview with the VP of Growth, concrete quotes verified verbatim). All flagged in per-case availability notes.
5. **No per-arm tables anywhere:** none of the 20 write-ups publish per-arm rates with per-arm sample sizes; `arm_b_tables` is null for all cases. Published quantities are prose-level summaries only. Total exposed-user counts, where published, are recorded in availability notes (sample size is not outcome information).
6. **Multi-variant exclusions:** one otherwise-qualifying case (C31 MSN Real Estate) was excluded because binarizing a 6-variant test requires outcome-informed arm selection. Bing font colors (ind_03) was retained despite being drawn from "a set of experiments" because the source concretely describes only one variant; this residual publication-bias channel is acknowledged.
