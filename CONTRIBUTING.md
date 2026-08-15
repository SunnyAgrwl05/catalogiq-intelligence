# Contributing to CatalogIQ Intelligence

Thanks for your interest in contributing! The repo ships **synthetic sample data**
only — never commit real benchmark files, personal data, or secrets.

## Getting started

```bash
git clone https://github.com/SunnyAgrwl05/catalogiq-intelligence.git
cd catalogiq-intelligence
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # mypy for type-checking
```

Run the app:

```bash
python app.py
```

Run the tests and type-check before opening a PR:

```bash
python -m pytest tests/ -q
# or
python -m unittest discover -s tests -v
mypy
```

## Finding something to do

- Look for issues labeled `good first issue` or `help wanted`.
- Open an issue first for larger changes so we can align on the approach.

## PR checklist

Before submitting a pull request, make sure:

- [ ] The change solves one problem and is focused in scope
- [ ] Code runs without errors (`python app.py`)
- [ ] Tests pass (`python -m pytest tests/ -q` / `python -m unittest discover -s tests -v`)
- [ ] Type-check passes (`mypy`)
- [ ] Tests added/updated where it makes sense
- [ ] README/docs updated if behavior changed
- [ ] No secrets, API keys, or non-synthetic benchmark data included
- [ ] My code follows the project style
- [ ] All existing tests pass locally

## Reporting bugs / requesting features

Use the issue templates: [bug report](.github/ISSUE_TEMPLATE/bug_report.md) and
[feature request](.github/ISSUE_TEMPLATE/feature_request.md).

Open an issue using the **Bug Report** template and include:

- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, browser)

Open an issue using the **Feature Request** template and describe:

- The problem you're solving
- Your proposed solution
- Alternatives you considered

## Code of Conduct

Please review the [Code of Conduct](CODE_OF_CONDUCT.md) before participating.
