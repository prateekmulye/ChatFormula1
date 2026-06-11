# Contributing Guide

Thanks for considering a contribution. ChatFormula1 is a personal
portfolio project, but issues and pull requests are welcome.

## Ground rules

- Be respectful and constructive.
- **Scope is deliberately tight.** The showcase inventory in
  [ARCHITECTURE.md](ARCHITECTURE.md) §5 defines what this project is;
  anything off it (clustering, Redis, user accounts, a tool-calling
  agent rewrite) is cut by default — see ROADMAP risk #11. Open an
  issue before building a feature.
- **Honest framing is a hard rule.** No invented metrics, no
  capabilities the code doesn't have, no theater. PRs that add
  plausible-looking-but-unwired code will be declined.

## Reporting bugs / requesting features

Open a GitHub issue with reproduction steps (bugs) or the use case
(features). Check existing issues first.

## Development setup

```bash
git clone https://github.com/<your-fork>/ChatFormula1.git
cd ChatFormula1
make db       # postgres:16 via docker compose
make setup    # poetry install · mix deps + ecto setup · npm ci
make test     # all three suites — no API keys needed
```

Per-app details: [agent/README.md](../agent/README.md),
[gateway/README.md](../gateway/README.md), [web/README.md](../web/README.md).

## Quality gates

Every PR must pass the same gates CI runs:

| App | Gate |
|---|---|
| `agent/` | `make lint-agent` (ruff + black + mypy) · `make test-agent` (pytest, dummy keys) |
| `gateway/` | `make lint-gateway` (format + credo --strict) · `make test-gateway` (ExUnit, needs Postgres) |
| `web/` | `make test-web` (tsc + eslint + vitest) · codegen drift check (`make codegen-web`) |

Rules that protect the architecture:

- **The NDJSON protocol is frozen** ([STREAMING_PROTOCOL.md](STREAMING_PROTOCOL.md)).
  Changes to it are breaking changes: update the document and the
  contract tests on *both* sides in the same PR.
- **CI uses dummy keys only, forever.** Never add a real secret to a
  workflow; tests must pass without credentials.
- **GraphQL schema changes** must regenerate `web/schema.graphql` and
  the typed hooks (`make codegen-web`) — web CI fails on drift.
- Single-node invariants ([ADR-000](adr/000-single-node-invariants.md))
  hold unless that ADR is superseded.

## Style

- Python: PEP 8 via black/ruff, type hints, docstrings on public
  functions.
- Elixir: `mix format`, credo strict, `@moduledoc`/`@doc` on public
  modules — the codebase treats moduledocs as architecture docs.
- TypeScript: eslint flat config; design tokens and component rules per
  [web/DESIGN.md](../web/DESIGN.md).

## Commits and PRs

- Conventional-style, present-tense subject lines
  (`fix(gateway): …`, `docs: …`).
- Keep PRs focused; include tests for new behavior; note any doc that
  needed updating.
- CI must be green before review.

## Questions

Open a GitHub issue or discussion on
[the repo](https://github.com/prateekmulye/ChatFormula1).

## License

By contributing you agree your contributions are licensed under the
[MIT License](../LICENSE).
