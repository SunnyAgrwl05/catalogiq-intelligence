[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Live Demo](https://img.shields.io/badge/Live-Demo-brightgreen)](#) [![Source Code](https://img.shields.io/badge/Source-Code-blue)](https://github.com/SunnyAgrwl05/catalogiq-intelligence) [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md) [![Tests](https://github.com/SunnyAgrwl05/catalogiq-intelligence/actions/workflows/tests.yml/badge.svg)](https://github.com/SunnyAgrwl05/catalogiq-intelligence/actions/workflows/tests.yml)


# 🧠 CatalogIQ Intelligence

### Evidence-Driven Product Intelligence for Industrial Commerce

Built by **Team UniCode** · UniHack Hackathon 2026

CatalogIQ turns incomplete, messy industrial product data into structured, validated, commerce-ready product intelligence. Every important output is backed by **visible evidence**, a **deterministic confidence score**, and a clear decision: `AUTO_APPROVE`, `REVIEW`, or `INVESTIGATE`.

---

## ⚠️ Data Provenance

This repository ships with small **synthetic/sample data**, not the official UniHack benchmark files.

| File | Purpose |
|---|---|
| `data/sample_input.csv` | 20 intentionally messy sample product rows |
| `data/sample_ground_truth.csv` | Expected values for the bundled sample |
| `data/synthetic_scale_1000.csv` | 1,000-row throughput demonstration |
| `data/manufacturer_brand_master.csv` | Sample manufacturer/brand reference data |
| `data/lov_master.csv` | Sample list-of-values reference data |
| `data/uom_standards.csv` | Sample unit-of-measure standards |

> No official benchmark results are claimed here.

---

## Demo

![CatalogIQ Dashboard](assets/catalogiq-demo.png)

---

## Problem

Industrial product information is often fragmented, incomplete, inconsistent, and difficult to validate at catalog scale.

CatalogIQ answers:

- What manufacturer is this product associated with?
- What brand and category are most likely?
- What evidence supports that decision?
- Are the available signals consistent or contradictory?
- Should the result be automatically approved or sent for human review?

---

## Solution

1. Normalize raw product fields and placeholders
2. Resolve manufacturer, brand, and MPN
3. Gather multiple evidence signals
4. Fuse evidence while detecting contradictions
5. Validate against LOV, UOM, and anomaly rules
6. Calculate deterministic field-level confidence
7. Route to `AUTO_APPROVED`, `REVIEW_REQUIRED`, or `INVESTIGATE`
8. Export enriched, explainable product intelligence

---

## Key Innovations

| Innovation | Description |
|---|---|
| **Evidence Graph** | Every field result contains structured supporting evidence |
| **Contradiction Engine** | Detects genuine conflicts instead of averaging them away |
| **Field-Level Trust** | Confidence and decisions are calculated independently per field |
| **Human-in-the-Loop** | Non-auto-approved fields are surfaced for review |
| **Correction Memory** | Human corrections can become future evidence for matching products |
| **Live Benchmarking** | Evaluation is computed from the available ground-truth file |

---

## Architecture

```
RAW PRODUCT
    ↓
preprocessing
    ↓
entity resolution
    ↓
evidence gathering
    ↓
correction memory
    ↓
contradiction detection
    ↓
validation
    ↓
confidence scoring
    ↓
decision routing
    ↓
EXPLAINABLE / REVIEWABLE / EXPORTABLE OUTPUT
```

---

## Project Structure

```
catalogiq-intelligence/
├── app.py
├── requirements.txt
├── data/
├── pipeline/
│   ├── schemas.py
│   ├── reference_data.py
│   ├── preprocessing.py
│   ├── entity_resolution.py
│   ├── evidence.py
│   ├── contradiction.py
│   ├── confidence.py
│   ├── validation.py
│   ├── correction_memory.py
│   ├── enrichment.py
│   └── icons.py
├── evaluation/
│   └── scorer.py
└── tests/
```

---

## Evidence Graph

A field result contains the selected value, confidence, supporting evidence, validation information, and decision.

```json
{
  "field": "manufacturer",
  "value": "Moen Incorporated",
  "confidence": 0.9831,
  "decision": "AUTO_APPROVED",
  "is_conflict": false
}
```

The app exposes this information in **Product Explainability** so reviewers can understand why a value was selected.

### How confidence is calculated

CatalogIQ turns the available evidence for a field into a confidence score between `0.0` and `1.0`. The score is deterministic: the same evidence, validation results, and conflict state always produce the same result.

- **Evidence agreement sets the starting score.** Evidence that supports the selected value contributes to its support. When multiple signals agree, their support increases confidence with diminishing returns so that repeated agreement helps without pushing the score above `1.0`. If there is no usable evidence, confidence is `0.0`.
- **Validation failures reduce confidence.** Each failed validation check (LOV, UOM, rules, or source validation) halves the current validation multiplier. Multiple failed checks compound, so fields with several validation problems are penalized more heavily.
- **Conflicts reduce confidence further.** The contradiction engine reports a conflict severity between `0.0` and `1.0`. Higher severity applies a larger penalty, up to a 50% reduction in confidence. A field that is explicitly marked as conflicting is routed to `INVESTIGATE` even if its numeric confidence would otherwise be high enough for another decision.
- **The final score determines the normal routing.** When there is no explicit conflict, confidence of `0.90` or higher is `AUTO_APPROVED`, confidence from `0.65` up to `0.90` is `REVIEW_REQUIRED`, and anything below `0.65` is `INVESTIGATE`.

In short, strong agreeing evidence raises confidence, while validation failures and contradictory evidence lower it. The decision layer then uses the resulting score together with the conflict flag to decide whether the field can be accepted automatically, should be reviewed by a person, or needs investigation.

---


## Human Review & Correction Memory

The **Human Review** section supports:

- ✅ Accept
- ✏️ Correct
- ❓ Mark Unknown

Corrections are stored in a transparent lookup table keyed by field, normalized MPN, and input manufacturer. This is **correction memory**, not a trained ML model.

---

## Validation

CatalogIQ includes:

- LOV allowed-value checks
- UOM normalization and formatting
- Placeholder detection
- Contextual anomaly checks

Unsupported values can be routed for review instead of being fabricated.

---

## Evaluation

The bundled sample currently reports:

| Metric | Result |
|---|---|
| Overall field accuracy | 96.7% (58/60) |
| Manufacturer accuracy | 95.0% (19/20) |
| Brand accuracy | 95.0% (19/20) |
| Category accuracy | 100.0% (20/20) |

> These figures are for the bundled 20-item sample only, not official UniHack benchmark results.

---

## Scalability

The bundled 1,000-row synthetic file is a throughput demonstration.

**Measured locally:** ~1,000 products in ~0.26 seconds (~3,800 products/sec)

> This is a single-process development-environment measurement, not a production SLA.

---

## Tech Stack

`Python 3.12` · `Streamlit` · `pandas` · Python standard library · `csv` · `difflib` · `dataclasses`

---

## Running Locally

```bash
git clone https://github.com/SunnyAgrwl05/catalogiq-intelligence.git
cd catalogiq-intelligence
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, typically `http://localhost:8501`.

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `CATALOGIQ_GROUND_TRUTH_PATH` | Path to a custom ground-truth CSV for benchmarking | `data/sample_ground_truth.csv` |

Example:

```bash
export CATALOGIQ_GROUND_TRUTH_PATH=/path/to/my/ground_truth.csv
streamlit run app.py
```

---

## API

CatalogIQ also provides a REST API via FastAPI alongside the Streamlit UI.

### Start the API server

```bash
uvicorn api:app --reload
```

OpenAPI interactive docs at `http://localhost:8000/docs`.

### `GET /health`

```bash
curl http://localhost:8000/health
```

### `POST /enrich` (JSON)

```bash
curl -X POST http://localhost:8000/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "products": [
      {
        "product_id": "P001",
        "manufacturer": "Moen",
        "mpn": "MN-7000",
        "description": "Single handle kitchen faucet, chrome finish",
        "category": "Faucets"
      }
    ]
  }'
```

### `POST /enrich/csv` (CSV upload)

```bash
curl -X POST http://localhost:8000/enrich/csv \
  -F "file=@catalog.csv"
```

---

## Demo Flow

1. **Dashboard** → click `RUN INTELLIGENCE ENGINE`
2. **Product Explainability** → inspect the evidence graph
3. **Contradictions** → inspect conflicting signals
4. **Human Review** → review or correct a field
5. **Benchmark & Quality** → run the live benchmark
6. **Scale Test** → run the 1,000-row throughput test
7. **Raw vs Enriched / Export** → compare and export the enriched catalog

---

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests cover normalization, placeholders, measurement extraction, entity resolution, contradiction detection, confidence scoring, validation, and correction memory.

---

## Custom Validation Rules

You can extend the validation pipeline without modifying Python source code by uploading a YAML or JSON rules file through the Dashboard.

See [`data/custom_rules_sample.yaml`](data/custom_rules_sample.yaml) for a complete example.

### Supported Sections

```yaml
# Additional allowed-value lists
lov:
  Faucets:
    Finish: ["Polished Nickel", "Matte Black"]
  Valves:
    Material: ["Brass", "Stainless Steel", "PVC"]

# Additional unit-of-measure entries
uom:
  m:
    normalized: "m"
    template: "{value} m"
  cm:
    normalized: "cm"
    template: "{value} cm"

# Category-specific anomaly thresholds
anomaly_rules:
  - category: "Valves"
    attribute: "weight"
    unit: "kg"
    max_value: 200
    message: "Valve weight over 200 kg is unusual for this category"
```

Custom rules are merged with the built-in reference data at runtime. When no rules file is provided, existing behavior is preserved.

---

## Limitations

- Bundled reference and ground-truth data are synthetic/sample data
- Category does not currently use a fully trained independent classifier
- Live manufacturer-site sourcing is not enabled in the bundled pipeline
- `difflib` is suitable for the current small reference set but may need a more scalable matcher for large catalogs
- The scale result is a local single-process measurement

---

## Future Scope

- [ ] Verified manufacturer/source-discovery evidence
- [ ] Stronger category classification
- [ ] Scalable fuzzy matching for large reference masters
- [ ] Batch/multiprocessing workers
- [ ] Expanded validation and measurement rules
- [ ] Official benchmark integration when available

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, the PR checklist, and how to report bugs or propose features. Please also review the [Code of Conduct](CODE_OF_CONDUCT.md) before participating.

Good first areas to contribute:

- Additional validation rules (`pipeline/validation.py`)
- Broader test coverage under `tests/`
- A production-grade fuzzy matcher to replace `difflib` for large reference masters

---

## License

This project is licensed under the [MIT License](LICENSE) — free to use, modify, and distribute, including commercially, with attribution.

---

<div align="center">

**CatalogIQ**

Built with ❤️ by **Sunny Kumar** & **Team UniCode** · UniHack Hackathon 2026

</div>
