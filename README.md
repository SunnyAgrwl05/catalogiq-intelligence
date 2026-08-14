# CatalogIQ — Turning Messy Product Data into Clean, Ready-to-Use Records

This project takes messy, incomplete product data (like a spreadsheet
of part numbers with missing or inconsistent info) and turns it into
clean, complete, standardized product listings — the kind a big
catalog or online store actually needs.

Built for a real problem: Unilog needs to clean and complete around
150,000 products every month.

**Try it live:** https://catalogiq-intelligence-yr8ctj9uouksvm3zbjhv8b.streamlit.app/
**Demo video:** _[add link here]_

---

## What we focused on

The challenge had 9 steps in total. We were told upfront: *"You don't
need to do all 9 steps perfectly — doing 2-3 steps really well beats
doing all 9 half-heartedly."* So that's what we did.

**Fully built, tested, and working in the live demo:**
- Cleaning up messy part numbers (removing junk text, extra spaces, placeholder values)
- Matching manufacturer/brand names correctly, even when they're spelled differently
- Checking product details against an approved list of correct values
- Converting measurements into a standard format (like turning "0.5 inch" into "1/2 inch")
- Writing 5 different versions of each product description, all within strict length limits
- Giving every product a trust score, and flagging anything that needs a human to double-check it

**Planned but not built yet (see Roadmap below):**
- Automatically sorting products into categories (right now we use simple keyword matching, not smart AI-based sorting)
- Automatically searching manufacturer websites for extra product specs
- Automatically finding product images, spec sheets, and safety documents

We didn't fake these parts. If something isn't built yet, the README
says so clearly — because guessing wrong is worse than saying "not
done yet."

---

## How it works (step by step)

```
                     ┌─────────────────────────┐
  Messy CSV file ──▶ │ 1. Clean up the data     │
                     │    (remove junk text)    │
                     └───────────┬─────────────┘
                                 ▼
                     ┌─────────────────────────┐
                     │ 2. Match brand/          │
                     │    manufacturer names    │
                     └───────────┬─────────────┘
                                 ▼
                     ┌─────────────────────────┐
                     │ 3. Sort into categories  │  (basic version now,
                     │                          │   smarter AI later)
                     └───────────┬─────────────┘
                                 ▼
                     ┌─────────────────────────┐
        (planned) ──▶│ 4. Search manufacturer   │
                     │    websites for specs    │
                     └───────────┬─────────────┘
                                 ▼
                     ┌─────────────────────────┐
                     │ 5. Check values against  │
                     │    the approved list     │
                     └───────────┬─────────────┘
                                 ▼
                     ┌─────────────────────────┐
                     │ 6. Standardize units     │
                     │    (e.g. 0.5in → 1/2in)  │
                     └───────────┬─────────────┘
                                 ▼
                     ┌─────────────────────────┐
                     │ 7. Write 5 product       │
                     │    descriptions          │
                     └───────────┬─────────────┘
                                 ▼
                     ┌─────────────────────────┐
        (planned) ──▶│ 8. Find images, PDFs,    │
                     │    safety documents      │
                     └───────────┬─────────────┘
                                 ▼
                     ┌─────────────────────────┐
                     │ 9. Give a trust score +  │
                     │    flag for review       │
                     └───────────┬─────────────┘
                                 ▼
                     Final, clean product record
```

## What it does — in detail

### 1. Cleaning up messy text

Real product data is often messy — extra spaces, weird symbols,
placeholder text like "N/A". This step cleans all of that up first.

**Example:**
```
Before: "  ABC-123 / N/A "
After:  "ABC-123"
```

### 2. Matching brand names correctly

Sometimes a brand is written differently across different files —
like "ACME" vs "ACME INC." This step matches them to one correct,
official name, and tells you how confident it is about the match.

**Example:**
```
Input:     "ACME INC."
Matched to: "ACME"
Confidence: 94%  (match type: close but not exact)
```

If the match isn't confident enough, it gets flagged so a person can
check it — the tool never just guesses silently.

### 3. Sorting products into categories

Right now, this uses simple keyword matching (e.g. if the text says
"hex bolt," it's tagged as a Bolt under Fasteners).

**Example:**
```
"stainless steel hex bolt"  →  Fasteners → Bolts
```

**Future improvement:** use smarter AI-based matching instead of just
keywords, so it understands meaning, not just exact words.

### 4. Searching manufacturer websites (not built yet)

The idea: automatically visit a manufacturer's website, search for
the exact product, and pull extra details from there.

This part isn't switched on yet — we didn't want to risk it failing
live during the demo. But the groundwork is already there: there are
spots ready in the data to store manufacturer links and reference
URLs once this is built.

### 5. Checking values against an approved list

Some fields (like material type) need to match an official, approved
list of values — this step checks for and fixes small mistakes like
typos.

**Example:**
```
Input:    "Stainless Steal"
Correct:  "Stainless Steel"
Result:   Automatically corrected (or flagged if unsure)
```

### 6. Standardizing measurements

Different files describe sizes differently. This step makes them all
consistent — including converting decimals into fractions.

**Example:**
```
Input:      0.5 in
Standard:   1/2 in
```

It supports converting any fraction from 1/64 up to 63/64.

### 7. Writing product descriptions

The tool writes 5 different versions of a product description, each
one following a strict character limit — because catalogs and online
stores often have tight length rules for descriptions. It writes
directly within that limit, instead of writing something long and
then cutting it short (which usually looks broken).

### 8. Finding images and documents (not built yet)

The plan is to automatically find product images, spec sheets (PDFs),
and safety data sheets. This is on the roadmap, not built yet.

### 9. Trust score + human review

Every product gets a score out of 100 showing how trustworthy the
final data is, based on things like: how confident the brand match
was, whether values passed the approved list check, and how complete
the descriptions are.

**Example:**
```
Trust Score: 94%

Brand match accuracy       98%
Approved value check      100%
Unit conversion accuracy  100%
Description quality        92%
How complete the data is   80%
```

It's not just a number — you can see exactly why it got that score.

## When something needs a human to check it

If the trust score is too low, the product gets flagged automatically
with a plain-English reason.

**Example:**
```
Trust Score: 61%
Needs a human to check: YES

Why:
The brand match wasn't confident enough.
Some information is missing.
```

This way, the system never quietly inserts data it isn't sure about —
it asks for help instead.

## How AI is used (and where it's kept out)

We kept AI (like Claude) out of the parts that need to be 100%
reliable. Things like matching brand names, converting units, and
checking approved values are all done with plain, predictable logic
— not AI guesses.

AI is only used, optionally, for writing extra marketing-style text
(like a catchy product blurb) — never for the core structured data.

**Why we did it this way:**
- Less risk of AI making things up
- Lower cost (no AI calls needed for most of the work)
- Faster processing
- The whole tool still works even without internet or an AI service

You can turn on AI-written marketing text by adding an
`ANTHROPIC_API_KEY`, but everything else works fine without it.

## What the demo shows you

- **Accuracy** — how closely the results match a known correct answer set
- **Description length checks** — confirms every description stays within its limit
- **Brand matching results** — how many were exact matches, close matches, or no match
- **How many products need human review**, and why

## Tests

The project includes automated tests that check all the core logic —
text cleanup, brand matching, unit conversion, description limits,
approved value checks, and trust scoring.

Run them with:

```bash
pytest -q
```

## Project folders

```
catalogiq-intelligence/
│
├── pipeline/              # the main logic
│   ├── parsing.py          # step 1: cleanup
│   ├── normalize.py        # steps 2 & 6: brand matching + units
│   ├── describe_gen.py     # step 7: descriptions
│   ├── validator.py        # steps 5 & 9: approved values + trust score
│   └── orchestrator.py     # runs everything together
│
├── data/                  # reference data used by the pipeline
│   ├── manufacturer_list.csv
│   ├── uom_standards.csv
│   ├── decimal_fraction.csv
│   ├── lov.csv
│   ├── sample_input.csv
│   └── ground_truth.csv
│
├── evaluation/
│   └── accuracy_scorer.py
│
├── tests/
│
├── app.py                 # the Streamlit app you interact with
├── requirements.txt
└── README.md
```

## Running it on your own computer

Clone the project:

```bash
git clone https://github.com/SunnyAgrwl05/catalogiq-intelligence.git
cd catalogiq-intelligence
```

Install what it needs:

```bash
pip install -r requirements.txt
```

Start the app:

```bash
streamlit run app.py
```

Then upload a CSV file with these columns: `Mfg_Part_Num, Part_Desc,
E1_Brand, Unilog_Brand, DIB_Brand, Part_Manuf` — or just use the
sample file that's already included. The app will clean and enrich
the data, show you the results, compare them to known correct
answers, and flag anything that needs review.

## What a CSV input looks like

```csv
Mfg_Part_Num,Part_Desc,E1_Brand,Unilog_Brand,DIB_Brand,Part_Manuf
ABC-123,1/2 SS HEX BOLT,ACME,ACME,ACME,ACME
XYZ-456,3.5 IN PIPE CLAMP,ACME,ACME,ACME,ACME
```

## What you get back

A cleaned-up version of each product with: correct manufacturer name,
correct brand, category, standardized measurements, 5 description
formats, approved value checks, a trust score, whether it needs human
review (and why), and space for reference links.

## How this could scale up to handle way more products

To go from a small demo to handling hundreds of thousands of products
a month, here's the plan:

1. **Run things in parallel** — the cleanup, brand matching, unit
   conversion, and description steps don't depend on AI, so they can
   run on multiple computers at once.
2. **Remember past lookups** — once a brand name or approved value has
   been checked once, save the result so it doesn't need to be
   checked again.
3. **Handle website searching separately** — since visiting manufacturer
   websites takes longer, that part runs on its own, at its own pace,
   without slowing down everything else.
4. **Keep AI use limited and optional** — since AI is only used for
   extra marketing text, the main process never has to wait on it.

## What's next (roadmap)

**Already done:**
- [x] Cleaning up messy text
- [x] Brand/manufacturer matching
- [x] Approved value checking
- [x] Unit standardization
- [x] 5 description formats with length limits
- [x] Trust scoring + human review flagging
- [x] Working demo app
- [x] Automated tests

**Coming next:**
- [ ] Smarter, AI-based category sorting
- [ ] Automatic manufacturer website searching
- [ ] Automatic image/document finding
- [ ] Full-size approved values list

**After that — scaling up:**
- [ ] Splitting work across multiple computers
- [ ] Faster processing queue
- [ ] Shared memory/caching system
- [ ] Monitoring so we know if something breaks
- [ ] Automatic retry when something fails
- [ ] A dashboard to track large batches

## Being upfront about what's missing

- **Website searching** isn't switched on yet — it's built into the
  design, just not turned on for this version.
- **Finding images/documents** isn't built yet.
- **Category sorting** is basic keyword matching for now, not smart AI sorting.
- **Reference data** used here is a smaller sample version — the real
  system would use much larger, complete versions of the same files.

## Our approach, in plain terms

Cleaning up product data isn't just about filling in blanks — it's
about making sure what gets filled in is actually correct. So we
followed three simple rules:

1. **Use predictable logic wherever possible** — don't leave things to guesswork.
2. **Always be able to explain a decision** — if something looks uncertain, say why.
3. **Ask a human when unsure** — it's better to flag something than to guess wrong.

## Why we built it this way

We didn't want to build a tool that just makes things up to look
finished. Instead, we combined a few simple, reliable pieces:
predictable logic, smart text matching, standards checking, some
AI-assisted writing, a trust score, and human review.

That combination matters more for real business catalogs — because
wrong information is worse than missing information.

## Team

**Team UniCode**
Sunny Kumar — GitHub: https://github.com/SunnyAgrwl05

## License

Built as a hackathon project.
