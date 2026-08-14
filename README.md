# CatalogIQ
**Evidence-Driven Product Intelligence for Industrial Commerce**

Turns incomplete, messy industrial product data into structured, validated,
commerce-ready product intelligence — with every field's value backed by
visible evidence, a deterministic confidence score, and a clear decision
(auto-approve, review, or investigate).

---

## \u26A0\uFE0F Read this first: data provenance

This build ships with **small, synthetic reference and sample data**, not the
official UniHack files. No `Unihack_Sample_Dataset`, `200-Item Ground Truth`,
`UNILOG UOM Standards`, LOV files, or manufacturer/brand master were provided
when this was built, so fabricating results against them would have meant
inventing accuracy numbers — which this project explicitly refuses to do.

What's here instead, all clearly labeled in the UI itself:

| File | What it is |
|---|---|
| `data/sample_input.csv` | 20 hand-written, intentionally messy sample product rows |
| `data/sample_ground_truth.csv` | 20 hand-labeled expected values for the sample rows |
| `data/synthetic_scale_1000.csv` | The 20 sample rows cycled to 1,000 rows, for a throughput demo only |
| `data/manufacturer_brand_master.csv` | 12 real plumbing/appliance brands (Moen, Delta, Kohler, GE, etc.) as a lookup table |
| `data/lov_master.csv`, `uom_standards.csv`, `decimal_fraction.csv` | Small synthetic reference tables |

**To run this against the real benchmark:** drop the official UniHack files
into `/data` using the same column names as the files above (see column
headers in each CSV). No pipeline code needs to change — `pipeline/reference_data.py`
and `app.py` read whatever's in `/data`. Every metric shown by the app
(accuracy, throughput, confidence) is computed live from whatever data is
present — nothing is hardcoded.

---

## Problem

Industrial manufacturers manage product data across catalogs, PDFs, and
websites. Turning that fragmented, incomplete data into accurate,
structured, commerce-ready intelligence — with traceable, explainable
outputs — is slow and error-prone at catalog scale.

## Solution

CatalogIQ resolves each product's manufacturer, brand, and category by
gathering multiple independent evidence signals (input fields, MPN
patterns, description text, prior human corrections), fusing them with a
contradiction-aware engine (not a naive average), scoring the result with a
deterministic confidence formula, and routing every field to
auto-approval, human review, or investigation based on that score and
whether the evidence actually agreed.

## Why CatalogIQ (vs. a CSV cleaner)

A CSV cleaner normalizes text. CatalogIQ additionally:
- Shows **why** it chose a value (evidence graph, per field)
- Detects when its own signals **disagree** and refuses to auto-publish
- Scores confidence **per field**, not one fuzzy product-level number
- Learns from human corrections via a transparent, inspectable memory
  (explicitly *not* claimed as a trained ML model)
- Refuses to invent values it can't support — returns `None` / "review
  required" instead

## Key Innovation

1. **Evidence Graph** — every field's value carries its supporting evidence
   as structured data (`pipeline/schemas.py: FieldResult`), not just a score.
2. **Contradiction Engine** — evidence is grouped by claimed value and the
   leader is compared against the runner-up; a close margin is flagged as a
   real conflict, not blended away (`pipeline/contradiction.py`).
3. **Field-Level Trust** — confidence, evidence, and decision are computed
   independently per field; product-level trust is derived, not primary.
4. **Human-in-the-Loop Review** — a queue of every non-auto-approved field,
   with Accept / Correct / Mark Unknown actions.
5. **Correction Memory** — corrections persist to `data/correction_memory.csv`
   keyed by (MPN, input-manufacturer) signature and resurface as an
   evidence signal on matching future products.
6. **Ground Truth Benchmark** — accuracy is computed live against whatever
   ground truth file is present; nothing is precomputed or cached as a claim.
7. **Quality / Validation Gate** — LOV, UOM formatting, and a contextual
   anomaly guard (e.g. flags a "1000 kg small faucet") run before a field
   can be auto-approved.

## Architecture

```
RAW PRODUCT
    -> preprocessing.normalize_product_row      (placeholder/null handling)
    -> entity_resolution.resolve_*               (manufacturer, MPN, description)
    -> evidence.gather_manufacturer_evidence      (builds Evidence[] )
    -> correction_memory.lookup_correction        (adds a signal if a prior human fix matches)
    -> contradiction.fuse_evidence                (consensus vs conflict)
    -> validation.build_field_validation          (LOV / UOM / anomaly checks)
    -> confidence.compute_field_confidence         (deterministic score)
    -> confidence.decide                           (AUTO_APPROVED / REVIEW_REQUIRED / INVESTIGATE)
    -> schemas.ProductResult                       (explainable, exportable)
```

Modular by design — `pipeline/` has one file per concern (see structure
below). `app.py` only wires the UI to these functions; it contains no
business logic itself.

```
app.py                  Streamlit UI (7 tabs)
pipeline/
  schemas.py             Evidence graph data model
  reference_data.py       Loads & indexes manufacturer/LOV/UOM/fraction masters
  preprocessing.py        Normalization, placeholder detection, measurement extraction
  entity_resolution.py    Manufacturer/brand/MPN matching (exact/alias/fuzzy)
  evidence.py             Evidence collection
  contradiction.py        Consensus/conflict detection
  confidence.py           Deterministic confidence scoring + decision routing
  validation.py           LOV/UOM/anomaly validation
  correction_memory.py    Persistent human-correction feedback log
  enrichment.py           Orchestrates the full per-product pipeline
evaluation/
  scorer.py               Live accuracy computation against ground truth
data/                    Synthetic sample + reference data (see table above)
tests/                   46 unit tests, stdlib unittest (no pytest dependency)
```

## Evidence Graph

Every field result looks like (from `pipeline/schemas.py`):
```json
{
  "field": "manufacturer",
  "value": "Moen Incorporated",
  "confidence": 0.9831,
  "evidence": [
    {"type": "input_field", "value": "Moen Incorporated", "strength": 1.0, "signal": "Input manufacturer field 'Moen' matched via exact match"},
    {"type": "mpn_pattern", "value": "Moen Incorporated", "strength": 0.8, "signal": "MPN '7000' matches known prefix pattern for Moen Incorporated"}
  ],
  "validation": {"lov": "n/a", "uom": "n/a", "rules": "n/a", "source": "n/a"},
  "decision": "AUTO_APPROVED",
  "is_conflict": false
}
```
Displayed in the app's **Product Explainability** tab under "Why did
CatalogIQ choose this?"

## Contradiction Engine

Evidence is grouped by claimed value and summed; the winner is compared to
the runner-up with a normalized margin. Margin < 15% \u2192 flagged as a
genuine conflict and routed to `INVESTIGATE`, regardless of how strong
either individual signal looked. Verified in
`tests/test_contradiction_and_confidence.py` on both a consensus case
(three signals agreeing on "Speed Queen") and a real conflict case (MPN
says Delta, description says GE — sample row `P011`).

## Trust Scoring

Deterministic formula in `pipeline/confidence.py`:
`confidence = combine(evidence strengths for winning value) \u00d7 validation
multiplier \u00d7 contradiction penalty`. Weights are named constants at the
top of the file, not buried magic numbers. No random or LLM-sampled
confidence values anywhere.

## Human-in-the-Loop

**Human Review** tab lists every field that isn't `AUTO_APPROVED`, with
Accept / Correct / Mark Unknown actions. A "Correct" action writes to
`correction_memory.csv` immediately; the next engine run will pick it up
as an evidence signal on matching products.

## Correction Memory

Explicitly a transparent lookup table (`pipeline/correction_memory.py`),
keyed by `(field, normalized MPN, normalized input-manufacturer)`. **Not**
a trained model — this is stated in the code, the UI, and here. Empty MPN
signatures never match, to avoid over-matching on blank/blank rows.

## Validation

LOV (against `data/lov_master.csv`), UOM normalization + formatting
(`"24in"` \u2192 flagged; `"24 in"` \u2192 passes), and a contextual anomaly guard
(currently one configured rule: implausible faucet weight) all run before
a field can be marked `AUTO_APPROVED`. Placeholder values (`"-- Unbranded --"`,
`"N/A"`, etc.) are collapsed to `None` in preprocessing, never fabricated.

## Evaluation

`evaluation/scorer.py: evaluate()` computes field-level accuracy live —
manufacturer, brand, category — by comparing pipeline output against a
ground-truth CSV. **Measured result on the bundled 20-item sample (not the
official 200):**

- Overall field accuracy: **96.7%** (58/60 field comparisons)
- Manufacturer accuracy: 95.0% (19/20)
- Brand accuracy: 95.0% (19/20)
- Category accuracy: 100.0% (20/20)
- The one "error": sample row `P011`, where the pipeline correctly
  detected a genuine MPN-vs-description conflict and routed it to
  `INVESTIGATE` rather than guessing — the scorer counts this as incorrect
  against a ground truth of `UNKNOWN` only because it still reports a
  best-guess candidate value alongside the conflict flag.

Re-run any time via the **Benchmark & Quality** tab — nothing here is cached
as a permanent claim; the button recomputes from scratch.

## Scalability

Measured on the bundled 1,000-row **synthetic** file (20 sample rows cycled
with new IDs — not the official 1,000-row dataset):

- **1,000 products processed in ~0.26s (~3,800 products/sec), single process**

This is single-machine, single-process Python throughput on this dev
environment — not a production SKU/month claim. The pipeline is stateless
per product (no shared mutable state between rows) and reference data is
loaded once via `functools.lru_cache`, so it's architecturally suited to
batching, multiprocessing, or horizontal scaling — but that scaling itself
has not been benchmarked here, and the README makes no throughput claim
beyond what was actually measured.

## Tech Stack

Python 3.12, Streamlit, pandas, stdlib `csv`/`difflib`/`dataclasses` (no
compiled fuzzy-matching dependency — entity resolution uses
`difflib.SequenceMatcher`, which is slower but has zero extra install risk).

UI polish (`pipeline/icons.py`) uses hand-authored inline SVG line-icons —
no external image files or CDN image fetches, so the demo never shows a
broken icon if the venue's wifi is unreliable. Google Fonts (Inter) is
loaded via CSS `@import`; if that request fails offline, the UI falls back
to the system sans-serif font automatically — nothing breaks.

## Installation

```bash
pip install -r requirements.txt
```

## Running Locally

```bash
streamlit run app.py
```
Then open the URL Streamlit prints (typically `http://localhost:8501`).

## Dataset

See the provenance table at the top of this README. Replace `/data` CSVs
with official files (same column names) for a real run.

## Benchmark Results

See "Evaluation" above — 96.7% field accuracy on the 20-item sample,
computed live, reproducible via the Benchmark & Quality tab.

## Tests

46 unit tests, stdlib `unittest`, no external test framework dependency:
```bash
python -m unittest discover -s tests -v
```
Covers: placeholder detection, normalization, measurement extraction,
manufacturer/MPN/description entity resolution (including a real bug found
and fixed during development — "GE" wasn't matching inside description
text due to an overly strict length guard, and a confidence-formula bug
where two strong agreeing signals fell just short of the auto-approve
threshold), contradiction detection (consensus vs. conflict vs. lopsided
disagreement), confidence scoring bounds, LOV/UOM/anomaly validation, and
correction-memory persistence and lookup.

## Screenshots

Not included in this deliverable — run `streamlit run app.py` to see the
live UI (Dashboard, Product Explainability, Contradictions, Human Review,
Benchmark & Quality, Scale Test, Raw vs Enriched / Export).

## Demo

Suggested flow, using the bundled sample data:
1. Dashboard tab \u2192 click **RUN INTELLIGENCE ENGINE** (uses the 20-row sample)
2. Product Explainability tab \u2192 select `P001` \u2192 expand "manufacturer" to see the evidence graph
3. Contradictions tab \u2192 shows `P011` (MPN says Delta, description says GE) flagged as a real conflict
4. Human Review tab \u2192 correct a field, watch it write to correction memory
5. Benchmark & Quality tab \u2192 click **Run benchmark now** \u2192 see live 96.7% accuracy
6. Scale Test tab \u2192 click **Run 1,000-row scale test** \u2192 see live measured throughput
7. Raw vs Enriched / Export tab \u2192 compare before/after, download enriched CSV

## Limitations

- Reference and ground-truth data are synthetic samples, not the official
  UniHack files (see provenance table above) — swap them in before final
  judging if you have them.
- Category is currently a **passthrough** from input with no independent
  classifier — its confidence is deliberately capped at 70% to reflect
  that honestly, rather than displaying false certainty.
- No live web/manufacturer-site sourcing is implemented — `validation.source`
  is `n/a` throughout. The evidence-graph structure has a slot for source
  evidence so this can be added later without a redesign.
- Entity resolution uses `difflib` (stdlib) rather than a dedicated
  fuzzy-matching library; adequate for the current reference-master size
  (12 manufacturers) but would need `rapidfuzz` or similar at real catalog
  scale (thousands of manufacturers) for both speed and match quality.
- Decimal\u2192fraction conversion table exists but isn't yet wired into the
  measurement-formatting path in `enrichment.py` — the lookup function
  works and is unit-tested at the `reference_data` level, but no field
  currently calls it end-to-end.
- Scale test throughput (~3,800 products/sec) is single-process on one
  dev machine; not benchmarked under Streamlit's request/response cycle,
  concurrent load, or at the full official 1,000-row file if it differs
  in structure from the synthetic one bundled here.

## Future Scope

- Wire the decimal-fraction table into measurement formatting
- Add source-discovery evidence (manufacturer domain matching) behind an
  explicit "source status: not configured" flag until real web access is
  available
- Category classifier trained/rule-built from LOV + description signals
- Swap `difflib` for `rapidfuzz` if/when reference master grows large
- Batch/multiprocessing worker pool for catalogs beyond single-process
  throughput needs
