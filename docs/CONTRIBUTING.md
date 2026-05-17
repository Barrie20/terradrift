# Contributing

Thanks for considering a contribution. This project is a research artifact
first and a tool second — please keep both audiences in mind.

## Quick start

```bash
make dev        # install dev deps + pre-commit
make test       # unit tests
make lint       # ruff
make type       # mypy strict
```

## Branching

- `main` is always green.
- Feature branches: `feat/<short-name>`
- Bug fix branches: `fix/<short-name>`
- Doc-only branches: `docs/<short-name>`

## Commit messages — Conventional Commits

Examples:
```
feat(drift): detect REGRESSED events using fixed-history set
fix(analyzer): handle Checkov v3 multi-framework JSON shape
docs(readme): add MSR 2026 target venue
chore(ci): pin actions/checkout to v4
```

Why this matters for *researchers*: a clean commit log lets a reviewer audit
how every result was produced.

## Pull requests

- Link an issue.
- Include before/after numbers if you touch the analyzer or drift logic.
- Run `make test` locally; CI will rerun anyway.

## Code of conduct

Be kind. Disagree about ideas, not people.
