# ADR-004: Supabase over Neon for free Postgres

- **Status:** Accepted
- **Date:** 2026-06-10

## Context

The gateway needs a free managed Postgres. Neon and Supabase are the
two serious candidates, and they meter their free tiers differently:

- **Neon** meters *compute hours* (~190/month free) and scales to zero
  on idle. That model assumes intermittent connections.
- **Supabase** caps *storage* (500 MB) and pauses projects after 7 days
  of full inactivity, but has no compute-hour meter.

This gateway is the worst case for Neon's model: it holds persistent
Ecto connections 24/7 and **Oban polls the jobs table every second**,
so the compute never idles. ~190 free hours ÷ 24 h/day ≈ the database
dies on day 8 of every month (ROADMAP risk #3). A "free" tier that
expires mid-month under normal operation is a trap, not a tier.

## Decision

**Supabase**, frozen here so nobody swaps providers casually:

- No compute-hour meter — an always-on, constantly-polling gateway is
  fine. 500 MB is ample (conversations are TTL-pruned nightly).
- Connection path: direct IPv6 from Fly (`ECTO_IPV6=true`) or Supavisor
  **session mode**; Ecto `pool_size: 5`.
- `Oban.Notifiers.PG` instead of Postgres LISTEN/NOTIFY, so nothing
  depends on NOTIFY surviving a pooler (it also matches the single-node
  design, ADR-000).
- The 7-day inactivity pause is defeated structurally: nightly Oban
  cron jobs write to the database every day.

Fallback if Supabase's free tier degrades: Neon **with its meter
respected** — aggressive idle disconnects and a raised Oban poll
interval — documented as a known-worse configuration, not the default.

## Consequences

- Database hosting stays at $0 with no month-end cliff.
- Session-mode pooling (not transaction mode) is required — Ecto holds
  session state; this is written into the deployment runbook.
- The provider choice is load-bearing for Oban's configuration; anyone
  revisiting it must re-check the notifier and polling assumptions, and
  supersede this ADR to do so.
