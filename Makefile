# ChatFormula1 monorepo — fans out to the per-app toolchains.
# agent/ (Python/LangGraph), gateway/ (Elixir/Phoenix), web/ (React/Apollo);
# see docs/ROADMAP.md for what each phase shipped.

.PHONY: help setup dev test lint \
	setup-agent dev-agent test-agent lint-agent \
	setup-gateway dev-gateway test-gateway lint-gateway \
	setup-web dev-web test-web lint-web codegen-web \
	db ingest reindex clean

help:
	@echo "ChatFormula1 monorepo targets:"
	@echo "  make setup    Install dependencies for all apps (run 'make db' first —"
	@echo "                the gateway setup creates + migrates its database)"
	@echo "  make dev      Run postgres + agent via Docker (gateway and web run"
	@echo "                natively: make dev-gateway / make dev-web)"
	@echo "  make test     Run all test suites (gateway tests need Postgres up)"
	@echo "  make lint     Run all linters"
	@echo "  make db       Start the local Postgres container only"
	@echo "  make ingest   Run the agent ingestion pipeline over data/"
	@echo "  make reindex  Delete + recreate the Pinecone index (run BEFORE"
	@echo "                re-ingesting after any embedding model/dimension change)"
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

setup-gateway:
	cd gateway && mix deps.get && mix ecto.create && mix ecto.migrate

dev-gateway:
	cd gateway && mix phx.server

test-gateway:
	cd gateway && MIX_ENV=test mix ecto.create --quiet && \
	  MIX_ENV=test mix ecto.migrate --quiet && \
	  mix test

lint-gateway:
	cd gateway && mix format --check-formatted && mix credo --strict

# ─── web (React / Apollo) ────────────────────────────────────────────────────

setup-web:
	cd web && npm ci

dev-web:
	cd web && npm run dev

test-web:
	cd web && npx tsc -b && npx eslint . && npx vitest run

lint-web:
	cd web && npx eslint .

# Regenerate web/schema.graphql from the gateway, then the typed hooks.
codegen-web:
	cd gateway && mix absinthe.schema.sdl --schema ChatF1Web.Schema ../web/schema.graphql
	cd web && npm run codegen

# ─── utilities ──────────────────────────────────────────────────────────────

db:
	docker compose up -d postgres

ingest:
	cd agent && poetry run f1-ingest --data-dir ../data ingest-all

# Destroys and recreates the Pinecone index with the configured embedding
# dimension. Required whenever the embedding provider/model/dimension
# changes — ALWAYS reindex before re-ingesting, never after.
reindex:
	cd agent && poetry run f1-ingest --data-dir ../data reindex

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf agent/dist agent/htmlcov agent/.coverage
