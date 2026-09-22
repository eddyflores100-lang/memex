# Contributing to Memex

Memex is a product of AliceLabs LLC. We welcome contributions from the community.

## Getting started

```bash
git clone https://github.com/eddyflores100-lang/memex.git
cd memex
pip install -e ".[dev]"
pytest tests/ -v
```

## Code style

- Line length: 100
- Formatter/linter: `ruff check src/ tests/` and `ruff format src/ tests/`
- Target: Python 3.10+

## Pull requests

1. Fork and branch from `main`
2. Keep changes focused — one feature or fix per PR
3. Add a test if the change touches retrieval logic
4. Update `CHANGELOG.md` under `Unreleased`
5. Ensure CI passes (ruff + pytest)

## License

All contributions are licensed under the AliceLabs Proprietary License v1.0.
