## Summary

<!-- What changed and why? Include badge/provenance impact if figures changed. -->

## Verification

- [ ] `ruff check . && ruff format --check .`
- [ ] `pytest` with the CI coverage gate (`--cov-fail-under=85`)
- [ ] `static/openapi.json` regenerated if routes changed
- [ ] README claims still true (numbers, badges, limitations)
- [ ] `pip-audit --strict` clean for changed dependencies

## Provenance

- [ ] No VERIFIED badge without an official source URL and `as_of`
- [ ] New datasets carry version + source URL in `data/`
