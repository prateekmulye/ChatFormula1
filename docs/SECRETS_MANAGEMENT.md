# Secrets Management Guide

How credentials are handled across the ChatFormula1 monorepo. The rule:
**secrets live in the environment, never in the repo, and never in CI.**

## What secrets exist

| Secret | Used by | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | agent | Generation, analysis, and embeddings |
| `PINECONE_API_KEY` | agent | Vector store access |
| `TAVILY_API_KEY` | agent | Real-time web search |
| `INTERNAL_API_TOKEN` | agent + gateway | Static bearer token guarding every `/internal/*` route |

The Phase 2 gateway adds its own secrets (database URL, `SECRET_KEY_BASE`,
plus the shared `INTERNAL_API_TOKEN`); they will be documented with the
gateway's deployment runbook.

## Local development

```bash
cp agent/.env.example agent/.env
# fill in real values — agent/.env is gitignored
```

Generate a strong internal token:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Settings load lazily (`chatf1_agent/settings.py`): importing modules never
requires credentials, and code that talks to an external service calls
`Settings.require(...)` at construction time, which also rejects
placeholder `your_*` values.

## CI: dummy keys only, forever

`.github/workflows/agent.yml` hardcodes dummy values
(`test-openai-key`, ...). The test suite is designed to pass with no real
credentials; live-integration tests detect the `test-` prefix and skip.
Real secrets are never configured as Actions secrets for test jobs — the
v1 workflow that injected production keys into unit tests on public PRs
was deleted as a security fix in Phase 1.

## Production

Deployment targets (Render for the agent, Fly for the gateway — see
[ARCHITECTURE.md](ARCHITECTURE.md) §7) inject secrets through their
native environment-variable stores. Nothing is baked into images:
`agent/.dockerignore` excludes `.env*`, and the Dockerfile only consumes
`INTERNAL_API_TOKEN` at runtime for its health check.

## Best practices

1. **Never commit secrets** — `.env` is gitignored; only `.env.example`
   with placeholders is tracked.
2. **Fail closed** — the agent returns `503` if `INTERNAL_API_TOKEN` is
   unset rather than serving unauthenticated traffic.
3. **Constant-time comparison** — bearer tokens are checked with
   `secrets.compare_digest`.
4. **Scan before pushing**:
   ```bash
   grep -rE "(sk-[A-Za-z0-9]{20,}|pcsk_|tvly-)" --exclude-dir=.git . && echo "LEAK?"
   grep -r "your_.*_here" agent/.env 2>/dev/null && echo "placeholders left"
   ```
5. **Set provider-side caps** — an account-level OpenAI spend cap backs
   up the application-level budget controls (Phase 5).

## Rotation

1. Create the new key in the provider dashboard (OpenAI / Pinecone /
   Tavily) or generate a new `INTERNAL_API_TOKEN`.
2. Update the value in the deployment environment (and in the gateway's
   environment too for `INTERNAL_API_TOKEN` — both sides must rotate
   together).
3. Restart the service and verify `/internal/health` with the new token.
4. Revoke the old key.

## Verifying configuration

```bash
# Confirm the agent sees its credentials (prefix only — never echo full keys)
cd agent && poetry run python -c "
from chatf1_agent.settings import Settings
s = Settings()
for f in ('openai_api_key', 'pinecone_api_key', 'tavily_api_key', 'internal_api_token'):
    v = getattr(s, f)
    print(f, 'set' if v else 'MISSING', v[:6] + '…' if v else '')
"
```

## Additional resources

- [12-Factor App: Config](https://12factor.net/config)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
