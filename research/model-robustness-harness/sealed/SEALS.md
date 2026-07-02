# Sealed-prereg provenance & verification

The 3-artifact discipline: **sealed prereg ≠ blind prediction ≠ measured truth.** Each
prereg was sha256-committed before any estimator or LLM call ran; no harness was re-tuned
to its predictions.

Verify from this directory:

```bash
for f in PREREG_AMBDOM PREREG_GNCE; do
  shasum -a 256 -c "$f.sha256" 2>/dev/null || \
  { exp=$(awk '{print $1}' "$f.sha256"); act=$(shasum -a 256 "$f.md" | awk '{print $1}'); \
    [ "$exp" = "$act" ] && echo "$f: OK" || echo "$f: MISMATCH"; }
done
```

| prereg | seal is over | status |
|---|---|---|
| `PREREG_AMBDOM.md` | the `.md` itself (`47d6f06e…`) | **VERIFIED** — sha256 of the promoted `.md` matches. |
| `PREREG_GNCE.md` | the `.md` itself (`434fd8f0…`) | **VERIFIED** — sha256 of the promoted `.md` matches. |
| `PREREG_WAVE1.md` | `BAKEOFF_SEALED_PREDICTIONS.json` (`32b2918c…`) | historical — seals the wave's sealed-prediction JSON, not the `.md`; that JSON was not part of the promoted set, so this seal is **not re-verifiable** from the promoted files. |
| `PREREG_WAVE2.md` | `BAKEOFF_SEALED_PREDICTIONS_WAVE2.json` (`6fc83393…`) | historical — same as WAVE1. |
| `PREREG_WAVE3.md` | `BAKEOFF_SEALED_PREDICTIONS_WAVE3.json` (`789317d6…`) | historical — same as WAVE1. |

The Wave1-3 seal hashes are the same ids recorded in the `Prereg` column of
`../results/LEDGER.md`, tying each logged run back to the prediction set that was sealed
before it ran. The Wave preregs (`.md`) are the human-readable protocol; the AMBDOM/GNCE
preregs seal the `.md` directly (the later, self-contained pattern) and verify cleanly.
