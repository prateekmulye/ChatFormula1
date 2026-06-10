# ChatFormula1 monorepo — fans out to the per-app toolchains.
# Only agent/ is implemented in Phase 1; gateway/ and web/ land in
# Phases 2-4 (see docs/ROADMAP.md).

.PHONY: help setup dev test lint \
	setup-agent dev-agent test-agent lint-agent \
	setup-gateway dev-gateway test-gateway lint-gateway \
	setup-web dev-web test-web lint-web \
	db ingest clean

help:
	@echo "ChatFormula1 monorepo targets:"
	@echo "  make setup    Install dependencies for all apps"
	@echo "  make dev      Run local development (postgres + agent)"
	@echo "  make test     Run all test suites"
	@echo "  make lint     Run all linters"
	@echo "  make db       Start the local Postgres container only"
	@echo "  make ingest   Run the agent ingestion pipeline over data/"
	@echo "  make clean    Remove caches and build artifacts"
	@echo ""
	@echo "Per-app targets: <verb>-agent, <verb>-gateway, <verb>-web"

setup: setup-agent setup-gateway setup-web
dev: dev-agent
test: test-agent test-gateway test-web
lint: lint-agent lint-gateway lint-web

# ─── agent (Python / LangGraph) ─────────────────────────────────────────────

setup-agent:
	cd agent && poetry install

dev-agent:
	docker compose up --build

test-agent:
	cd agent && poetry run pytest

lint-agent:
	cd agent && poetry run ruff check src ingestion tests
	cd agent && poetry run black --check src ingestion tests
	cd agent && poetry run mypy src ingestion

# ─── gateway (Elixir / Phoenix — Phase 2) ───────────────────────────────────

setup-gateway dev-gateway test-gateway lint-gateway:
	@echo "gateway: not yet — see docs/ROADMAP.md (Phase 2)"

# ─── web (React / Apollo — Phase 4) ─────────────────────────────────────────

setup-web dev-web test-web lint-web:
	@echo "web: not yet — see docs/ROADMAP.md (Phase 4)"

# ─── utilities ──────────────────────────────────────────────────────────────

db:
	docker compose up -d postgres

ingest:
	cd agent && poetry run f1-ingest --data-dir ../data ingest-all

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf agent/dist agent/htmlcov agent/.coverage
