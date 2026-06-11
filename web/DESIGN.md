# ChatFormula1 v2 — Web Frontend Design Specification

**The "Pit Wall" cockpit. Dark-first, telemetry-grade, motorsport-without-the-logo.**
A single-author design spec for a build agent to implement without guessing.

> Stack target: React 18 + TypeScript + Tailwind CSS v4 + shadcn/ui + Motion (framer). Static Vite build on Vercel. Apollo Client (split link: HTTPS queries/mutations, WSS `graphql-ws` subscriptions). Landing must paint < 1s on a cold backend.

---

## 0. Process Note — How This Spec Was Derived

**Sources consulted (per the mandated method):**

- **NotebookLM — "Advanced UI Design and Animation Resources"** (id `de2a7c73…`). Queried five concrete questions. Key cited takeaways used below and tagged `[NLM]`:
  1. **Token-stream readability:** Skeleton-First structural pre-allocation; `contain: layout`; `max-width: 65ch`; `min-height: 1.55em` baseline pre-allocation; line-height **1.55**; 16px floor; `font-variant-numeric: tabular-nums`; vertical word-group materialization (`translateY(8px)→0`, opacity 0→1) — never horizontal typewriter; the Luminous Caret (2px azure pill, spring `{150,15,0.1}` pulse per word, 300ms opacity oscillation on pause); `aria-live="polite"`.
  2. **Pipeline telemetry strip:** the **Traveling Signal** (SVG packet on `offset-path` + marching-ants `stroke-dashoffset`); Doherty timing (feedback <50ms, transition <400ms); departure anticipation `scale(0.95)` → flight → arrival follow-through `scale(1.1)` + glow → settle into 2–3s breathing; pair every color shift with an icon; reduced-motion = instant state-swap + 7:1 text labels.
  3. **Lights-out loader:** three phases (Ignition 0–5s, Building Tension 5–45s with a tech-log token every ~10s, Climax 45–60s with accelerated breathing + "Link 5 of 5" Zeigarnik); resolution = simultaneous extinguish then a 400ms green Luminous flash (Peak-End); **20% Speed Rule** for early completion (fast-forward staggers, never instant-jump); amber "active waiting" copy for overrun (never "broken").
  4. **Palette:** dark-first OKLCH motorsport-night palette **without brand red** (asphalt base, carbon surface, telemetry azure, electric-lime energy, thermal-amber caution, finish-line green); body text `oklch(95% 0.01 260)` for >7:1; carbon-fiber `feTurbulence` grain; replace red with amber + a caution/shield icon for colorblind legibility.
  5. **Anti-slop:** kill "Inter-for-everything," kill decorative magic gradients, replace with functional status signifiers (shield/loop/arrow), serif+mono editorial pairing, vertical word-stream (not typewriter), physics springs (not linear/bounce), >500ms grace transitions for "professional maturity."

- **Stitch MCP — DELIBERATELY NOT USED.** `[SOURCE SUBSTITUTED: Stitch]` Stitch's tool schema crashes this environment (known hard constraint). Visual grounding was done via NotebookLM + direct reading of `docs/ARCHITECTURE.md` (the exact GraphQL types, `AgentNode` enum, `ServiceMode`, `SystemStats`, the wake-on-paint choreography in §2, the streaming path in §4.6). All visual claims below are grounded in those two sources; anything inferred is tagged `[UNVERIFIED]`.

**Iterations (summarized — full reasoning in §1.1):** A "Broadcast Graphics" direction was explored and rejected as too imitative of TV F1 overlays (trademark risk + derivative). The chosen direction, **"The Pit Wall,"** reframes the UI as the *engineer's* console, not the *broadcaster's* graphic — original, defensible, and truer to the product thesis (the BEAM/GraphQL engineering is the star, the AI rides on top).

---

## 1. Design Concept & Mood (the story)

**ChatFormula1 is the pit wall, not the broadcast.** You are not a fan watching a race on TV — you are the race engineer sitting at the timing screens at 2 a.m., headset on, watching real telemetry scroll past on matte carbon-fiber surfaces lit by a single cold azure glow and the occasional flare of electric lime as a process fires. Every answer the AI gives arrives the way pit-wall data does: a signal travels down the strip (ANALYZE → ROUTE → SEARCH → RANK → GENERATE), citations resolve like sectors going green *before* the lap is even finished, and the words materialize token by token like a radio transcript coming through. The cold-start wait is not a spinner — it is the grid forming up, five lights illuminating one by one, pit-radio chatter confirming systems online, then **lights out**. The whole surface feels engineered, instrumented, and *alive*: numbers tick in tabular mono, nodes breathe on a 3-second cycle, and nothing ever just "loads" — it *spools up*. The emotional target is **competent calm under speed**: a recruiter should feel they are looking at something a real team built, that the system is honest about its own state (LIVE / DEGRADED / SHOWCASE shown plainly), and that even the failure modes were designed. Mood name: **"Telemetry Noir."**

### 1.1 Iteration trail (the two directions + the convergence)

- **Iteration A — "Broadcast Graphics."** Mimic the on-screen TV overlays: bold timing towers, sector mini-sectors flashing purple/green, a lower-third ticker. *Critique:* (1) trademark danger — it reads as an imitation of a specific broadcaster's graphics package and the brand's visual language; (2) it makes the *AI/data* the star and hides the actual engineering thesis; (3) it is derivative — every F1 fan-site does timing-tower cosplay. Von Restorff fails: nothing is distinctive. Rejected.
- **Iteration B — "The Pit Wall / Telemetry Noir."** Reframe from *broadcaster* to *engineer*. The UI is the instrument cluster the team itself watches. This (1) is original and trademark-safe (engineering telemetry is generic, not branded), (2) puts the BEAM/GraphQL/AI pipeline literally on screen as the hero (the TelemetryStrip *is* the LangGraph node tree), (3) gives the cold-start a story (the grid forming), and (4) lets honesty be a feature (the SHOWCASE/DEGRADED badges look like real ops telemetry, not an apology). **Chosen.** Everything below implements B.

**Why B wins:** it is inevitable (a pit wall is the obvious metaphor once named) yet surprising (nobody builds the *engineer's* view), it foregrounds the product's actual differentiator (the inspectable pipeline), and every required surface maps cleanly onto a real pit-wall artifact.

---

## 2. Design Tokens

All colors authored in **OKLCH** (for perceptual uniformity and clean dark-mode chroma) with hex fallbacks. Single dark theme. Body text meets **WCAG AA / AAA** on the base.

### 2.1 Color palette

| Semantic name | Token | OKLCH | Hex | Use |
|---|---|---|---|---|
| Base — Asphalt Night | `--bg` | `oklch(12% 0.015 260)` | `#111319` | App background, deepest layer |
| Surface 1 — Carbon | `--surface-1` | `oklch(16% 0.018 260)` | `#1a1d25` | Cards, message bubbles (assistant) |
| Surface 2 — Carbon raised | `--surface-2` | `oklch(20% 0.02 260)` | `#262a34` | Strip, panels, hover, popovers |
| Surface 3 — Edge | `--surface-3` | `oklch(26% 0.022 260)` | `#363b47` | Inputs, pressed states |
| Hairline | `--hairline` | `oklch(95% 0.01 260 / 8%)` | `rgba(238,240,245,.08)` | 1px borders, dividers (whitespace-as-box) |
| Hairline strong | `--hairline-2` | `oklch(95% 0.01 260 / 14%)` | `rgba(238,240,245,.14)` | Focused/active card edges |
| Text — Primary | `--text` | `oklch(95% 0.01 260)` | `#eef0f5` | Body, answers (>7:1 on base) |
| Text — Secondary | `--text-dim` | `oklch(72% 0.015 260)` | `#a3a8b4` | Labels, metadata, captions |
| Text — Faint | `--text-faint` | `oklch(52% 0.015 260)` | `#6b7180` | Disabled, ghost numerals |
| **Accent — Telemetry Azure** | `--azure` | `oklch(65% 0.12 245)` | `#4f95ff` | **Functional**: active signal, caret, links, focus ring, send |
| Azure dim | `--azure-dim` | `oklch(45% 0.09 245)` | `#2f5da8` | Idle connectors, muted azure |
| **Accent — Electric Lime** | `--lime` | `oklch(85% 0.18 105)` | `#d9ff45` | **Energy / live compute**: breathing active node, "GENERATE" pulse, LIVE dot. Use sparingly (Von Restorff). |
| Status — Thermal Amber | `--amber` | `oklch(70% 0.16 55)` | `#ff8b3d` | DEGRADED, caution, overrun, warming, retryable error (replaces red) |
| Status — Finish Green | `--green` | `oklch(65% 0.12 150)` | `#4ade80` | HEALTHY, complete, cached-success, lights-out resolution |
| Status — Critical | `--critical` | `oklch(58% 0.17 28)` | `#e5484d` | Hard DOWN / non-retryable only. **Rare.** Not a brand color; always paired with an icon. |
| Citation chip bg | `--chip` | `oklch(22% 0.03 245)` | `#222b3a` | Citation/source chip surface |

**Critical palette rules:**
- **No brand red as identity.** Red (`--critical`) appears only for hard `DOWN`/`INTERNAL` non-retryable states, always with a caution icon, never as a theme accent. Motorsport mood comes from carbon + azure + lime + amber, not red. `[NLM]`
- **Lime is rationed.** It marks *live energy* only (the currently-generating node, the LIVE pulse). Overuse kills its isolation effect.
- **Azure is functional, not decorative.** Every azure element means "active / interactive / signal." Never an azure background gradient on a card (anti-slop).
- **Status is never color-alone.** Each of HEALTHY/DEGRADED/DOWN, LIVE/SHOWCASE, cached/live pairs with a distinct **glyph** (see §4 iconography) for colorblind legibility. `[NLM]`

### 2.2 Texture

Carbon-fiber "Digital Soul" grain `[NLM]`: a single fixed SVG `feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3"` rendered into a full-viewport pseudo-element at **~3% opacity**, `mix-blend-mode: overlay`, `pointer-events:none`, `position:fixed`. One instance only (GPU budget). Plus an optional 2px twill diagonal repeating-linear-gradient at ~4% on `--surface-2` panels for a woven-carbon read. **Never** animate the grain. Disabled under `prefers-reduced-motion` is unnecessary (it is static) but it must not tank contrast — keep it under text via `z-index`.

### 2.3 Typography

Google Fonts, dark-tuned. Editorial serif + clean sans + tabular mono — the explicit anti-"Inter-for-everything" pairing `[NLM]`.

| Role | Family | Notes |
|---|---|---|
| **Display / headlines** | **Spectral** (serif, variable) | Editorial authority for hero/section titles. Newsreader is an acceptable substitute. Weights 500–600. NOT for body. |
| **Body / UI / answers** | **Inter** | The assistant *reading voice* and all UI text. 16px floor. Line-height 1.55 on answers. `[NLM]` |
| **Telemetry / mono** | **JetBrains Mono** | ALL numbers, node labels, latency/token badges, system stats, code, the user's own echoed query, pit-radio log. `font-variant-numeric: tabular-nums` mandatory on every counter. `[NLM]` |

**Type scale** (1.250 Major Third, rem):

| Token | Size | Line-height | Family | Use |
|---|---|---|---|---|
| `--fs-hero` | `clamp(2.5rem, 6vw, 4.2rem)` | 1.05 | Spectral | Countdown hero, lights-out title |
| `--fs-h1` | `2.027rem` | 1.15 | Spectral | Page titles |
| `--fs-h2` | `1.62rem` | 1.2 | Spectral | Section titles |
| `--fs-h3` | `1.296rem` | 1.3 | Inter 600 | Card titles |
| `--fs-body` | `1.0625rem` (17px) | **1.55** | Inter | Assistant answers, paragraphs |
| `--fs-ui` | `0.9375rem` (15px) | 1.45 | Inter | Buttons, inputs, chips |
| `--fs-meta` | `0.8125rem` (13px) | 1.4 | JetBrains Mono | Badges, node labels, captions |
| `--fs-micro` | `0.6875rem` (11px) | 1.3 | JetBrains Mono | Strip sub-labels, seq numbers |
| `--fs-numeral` | `clamp(3rem, 9vw, 6rem)` | 1 | JetBrains Mono tabular | Ghost numerals, big countdown digits |

Letter-spacing: mono labels `0.04em` uppercase for "instrument" feel; serif headlines `-0.01em`.

### 2.4 Spacing, radius, elevation

- **Spacing scale** (4px base): `0, 2, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 96`. Tailwind default scale is fine; standardize on multiples of 4.
- **Radius:** `--r-sm: 6px` (chips, badges), `--r-md: 10px` (buttons, inputs), `--r-lg: 14px` (cards, bubbles), `--r-xl: 20px` (panels, modals). Asymmetric bubble corner for the assistant: `14px 14px 14px 4px` (anchors it to the left rail, a small charm).
- **Elevation** (dark-mode = lighter surface + hairline + soft glow, never heavy drop-shadow):
  - `--e-0`: flat on `--bg`.
  - `--e-1`: `--surface-1` + `1px --hairline`.
  - `--e-2`: `--surface-2` + `1px --hairline-2` + `0 1px 0 rgba(255,255,255,.03) inset`.
  - `--e-glow-azure`: `0 0 0 1px var(--azure)/.4, 0 0 24px -8px var(--azure)/.5` (active signal).
  - `--e-glow-lime`: `0 0 20px -6px var(--lime)/.55` (live compute, used on the generating node only).

### 2.5 Motion tokens

Physics over duration where motion is "alive"; calm cubic-bezier where motion should read "mature." `[NLM]`

| Token | Value | Use |
|---|---|---|
| `--spring-signal` | `{ stiffness: 150, damping: 15, mass: 0.1 }` | Node activation, caret pulse, packet arrival, traveling signal `[NLM]` |
| `--spring-soft` | `{ stiffness: 120, damping: 18, mass: 0.4 }` | Card/chip entrance, hover lift |
| `--ease-reveal` | `cubic-bezier(0.16, 1, 0.3, 1)` | Token-group materialize, panel open, "professional maturity" transitions `[NLM]` |
| `--ease-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | Generic UI |
| `--d-micro` | `120ms` | Hover, focus, micro-feedback (<50ms perceived for the *start*) |
| `--d-fast` | `200ms` | Entrances, token-group reveal |
| `--d-base` | `320ms` | Node transitions (within the Doherty <400ms budget) `[NLM]` |
| `--d-grace` | `560ms` | Panel/route transitions ("professional maturity" >500ms) `[NLM]` |
| `--cycle-breathe` | `2800ms` | Active-node breathing (scale 1.0→1.03, opacity 0.8→1.0) `[NLM]` |
| `--cadence-token` | `40ms / 12-token batch` | Token-stream flush cadence — **matches the gateway's micro-batch** (ARCHITECTURE §4.4). Render reveals each arriving batch as one word-group. |

**Global rule:** every animation has a `prefers-reduced-motion: reduce` branch (specified per-component in §5). No linear easing on organic motion. No SaaS bounce.

### 2.6 Tailwind v4 config shape

Tailwind v4 uses CSS-first `@theme`. The build agent should author:

```css
/* app.css */
@import "tailwindcss";

@theme {
  /* colors — expose as utilities: bg-bg, text-azure, border-hairline, etc. */
  --color-bg: oklch(12% 0.015 260);
  --color-surface-1: oklch(16% 0.018 260);
  --color-surface-2: oklch(20% 0.02 260);
  --color-surface-3: oklch(26% 0.022 260);
  --color-hairline: oklch(95% 0.01 260 / 8%);
  --color-hairline-2: oklch(95% 0.01 260 / 14%);
  --color-text: oklch(95% 0.01 260);
  --color-text-dim: oklch(72% 0.015 260);
  --color-text-faint: oklch(52% 0.015 260);
  --color-azure: oklch(65% 0.12 245);
  --color-azure-dim: oklch(45% 0.09 245);
  --color-lime: oklch(85% 0.18 105);
  --color-amber: oklch(70% 0.16 55);
  --color-green: oklch(65% 0.12 150);
  --color-critical: oklch(58% 0.17 28);
  --color-chip: oklch(22% 0.03 245);

  /* fonts */
  --font-display: "Spectral", Georgia, serif;
  --font-sans: "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;

  /* radius */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;

  /* motion (durations as custom props; springs live in Motion config in TS) */
  --ease-reveal: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-standard: cubic-bezier(0.4, 0, 0.2, 1);
}

/* base layer */
@layer base {
  html { color-scheme: dark; }
  body {
    background: var(--color-bg);
    color: var(--color-text);
    font-family: var(--font-sans);
    -webkit-font-smoothing: antialiased;
  }
  .tabular { font-variant-numeric: tabular-nums; }
}
```

shadcn/ui CSS variables (`--background`, `--foreground`, `--primary`, `--border`, `--ring`, etc.) map onto these tokens so all shadcn primitives inherit the theme: `--primary → --color-azure`, `--background → --color-bg`, `--card → --color-surface-1`, `--border → --color-hairline`, `--ring → --color-azure`, `--destructive → --color-critical`.

---

## 3. Per-Surface Layout Specs

Breakpoints: mobile `< 768px`, tablet `768–1024px`, desktop `≥ 1024px`. Mobile-first. Max content width `1200px`, chat column `min(760px, 92vw)`.

### 3.0 Global shell

```
DESKTOP (≥1024)
┌──────────────────────────────────────────────────────────────────────┐
│ MASTHEAD  ◇ ChatF1   Chat · Standings · Calendar · Drivers  [STATUS▸] │ 56px, sticky, surface-1 + bottom hairline
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│                        << route content >>                            │
│                                                                        │
├──────────────────────────────────────────────────────────────────────┤
│ FOOTER — disclaimer (unofficial fan project) · links · build hash      │
└──────────────────────────────────────────────────────────────────────┘

MOBILE (<768)
┌──────────────────────────┐
│ ◇ ChatF1        [STATUS▸] │ 52px sticky
├──────────────────────────┤
│      route content        │
├──────────────────────────┤
│ [Chat][Stand][Cal][Driv]  │ bottom tab bar, 56px, icons+label, ≥44px targets (Fitts)
└──────────────────────────┘
│ disclaimer footer below tab bar on scroll-end │
```

- **◇ logo:** an original geometric mark — a single chevron/apex glyph (a stylized racing apex / cornering line), drawn as inline SVG. **Not** an F1-style logo, no number, no team reference.
- **[STATUS▸]:** the `StatusBadge` (§4) — always visible top-right; tapping opens the `PitWallPanel` (system status surface).
- Nav uses Jakob's Law (familiar top-nav desktop / bottom-tab mobile). Hick's Law: only 4 primary routes; the ops panel is a slide-over, not a 5th nav item.

### 3.1 Chat (default route) — the centerpiece

```
DESKTOP (≥1024)
┌──────────────────────────────────────────────────────────────────────┐
│ MASTHEAD                                                  [● LIVE ▸]   │
├──────────────────────────────────────────────────────────────────────┤
│  ┌── TELEMETRY STRIP (sticky under masthead, 64px) ──────────────────┐ │
│  │ ANALYZE › ROUTE › ⟨VECTOR⟩ › RANK › GENERATE      p95 312ms  ⚡48t/s │ │
│  │   ●━━━━━●━━━━━◉∙∙∙∙∙○━━━━━○        (signal traveling)              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│   conversation column — min(760px, 92vw), centered                    │
│                                                                        │
│   ┌─ user ───────────────────────────────────┐  (right, mono echo)    │
│   │  Who leads the drivers' championship?      │                       │
│   └────────────────────────────────────────────┘                       │
│                                                                        │
│   ┌─ assistant ────────────────────────────────────────────────┐       │
│   │ [VECTOR ◆ Regs 2026]  [WEB ◇ autosport.com]  ← chips FIRST  │       │
│   │ Verstappen leads with 312 points after▌  ← token stream     │       │
│   │ ─────────────────────────────────────                       │       │
│   │ 312ms · 48 tok/s · live          [👍][👎]  ← latency badges  │       │
│   └──────────────────────────────────────────────────────────────┘       │
│                                                                        │
│   ┌ suggested chips (Hick: max 4–5) ──────────────────────────────┐    │
│   │ [Next race?] [Tire strategy] [2026 rules] [Standings]          │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                                                                        │
│  ┌── COMPOSER (sticky bottom) ───────────────────────────────────────┐ │
│  │  ▸ Ask the pit wall…                                      [ ⌁ Send]│ │
│  └────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘

MOBILE (<768)
┌──────────────────────────┐
│ ◇ ChatF1        [● LIVE▸] │
├──────────────────────────┤
│ STRIP (horizontal-scroll, │  56px; active node auto-scrolls into view
│  active node centered)    │
├──────────────────────────┤
│   user bubble (right)     │
│   assistant bubble (full) │  full-width minus 16px gutters
│   chips below             │
│   ...                     │
├──────────────────────────┤
│ suggested chips (h-scroll)│
├──────────────────────────┤
│ ▸ Ask…            [⌁]     │ composer pinned above bottom tab bar
└──────────────────────────┘
```

- Citation chips render **above/before** the answer text as `SourcesResolved` arrives (ARCHITECTURE §4.4) — the "sectors going green before the lap finishes" beat. Peak moment.
- Composer keeps focus after send (rapid-fire chaining `[NLM]` console pattern); only moves focus to the new assistant message when it begins streaming, announced via `aria-live`.
- Empty state: a warm pit-wall greeting + the demo-question chips front and center (Serial Position — strongest items first/last in the chip row).

### 3.2 Warming-up state (cold-start, full takeover)

Renders inside the conversation column (or full-bleed on first cold load) when `NodeTransition{WARMING_UP}` events arrive or `systemHealth.agentService = DOWN/DEGRADED` during a send. See `LightsOutLoader` §4 and the timing diagram §5.1.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                        │
│                    SPOOLING UP THE ENGINES                            │  Spectral, --fs-hero
│                                                                        │
│                  ●     ●     ●     ●     ●                              │  five lights, illuminate L→R
│                ─────────────────────────────                          │  light gantry bar
│                                                                        │
│   ┌ PIT RADIO ─────────────────────────────────────────────────┐      │  mono log, aria-live
│   │ 0x01  GATEWAY ONLINE                            ✓ green      │      │
│   │ 0x02  WAKING INFERENCE ENGINE…                  ⟳ amber      │      │
│   │ 0x03  COLD START · RENDER FREE TIER · ~45s       … azure     │      │
│   │ 0x04  HYDRATING VECTOR INDEX…                               │      │  new line every ~10s
│   └──────────────────────────────────────────────────────────────┘      │
│                                                                        │
│             Link 4 of 5 · the wait is the demo                        │  caption, --text-dim
└──────────────────────────────────────────────────────────────────────┘
```

- The copy is honest and a little proud: it *tells you* it is a free-tier cold start and frames it as part of the show. Never the word "Error" or "Loading…".
- On the landing/hero (wake-on-paint, ARCHITECTURE §2): the hero copy itself is the cover for the cold start — the lights loader only takes over if the user submits before the agent is warm.

### 3.3 Standings / Calendar / Drivers

```
STANDINGS (desktop)                         CALENDAR (desktop)
┌─────────────────────────────────┐        ┌─────────────────────────────────┐
│ 2026 DRIVERS' STANDINGS    [⇅]   │        │  ┌ COUNTDOWN HERO ─────────────┐ │
│ ┌─────────────────────────────┐ │        │  │ NEXT · ROUND 9               │ │
│ │ P  DRIVER         PTS  W  P° │ │        │  │ Spielberg Circuit, Austria   │ │
│ │ 1  VERSTAPPEN     312  7  9  │ │ rows   │  │   02 : 14 : 33 : 07          │ │  big tabular numerals
│ │ 2  NORRIS         268  3  8  │ │ hover  │  │   DD   HH   MM   SS          │ │  digits flip on tick
│ │ 3  LECLERC        241  2  7  │ │ →azure │  └──────────────────────────────┘ │
│ │ …                            │ │ rail   │  ┌ round cards (grid, 3-col) ──┐ │
│ └─────────────────────────────┘ │        │  │ R10 │ R11 │ R12 │           │ │
│  PTS / W / P° columns = mono     │        │  └──────────────────────────────┘ │
└─────────────────────────────────┘        └─────────────────────────────────┘

MOBILE: standings table collapses — each row becomes a card:
┌──────────────────────────┐
│ P1  VERSTAPPEN     312pts │  pos as a left "grid slot" tab
│     7 wins · 9 podiums    │
└──────────────────────────┘
Calendar: countdown hero stacks; round cards single-column.
DRIVERS: card grid (driver number as oversized ghost mono numeral behind the name + code).
```

- All numeric columns are JetBrains Mono tabular-nums, right-aligned, so they form clean vertical telemetry columns.
- Countdown digits update every second with **no layout shift** (tabular-nums + fixed-width digit slots); the seconds digit gets a subtle 120ms flip/fade on change (reduced-motion: instant).
- Driver number rendered as a `--fs-numeral` ghost numeral at `--text-faint` behind the card content (Von Restorff "grid slot" feel; original styling, not a team font).

### 3.4 System status surface (the public ops panel)

A right-side **slide-over** (desktop) / full-screen sheet (mobile) opened from `[STATUS▸]`. Renders `systemHealth` + `systemStats` (ARCHITECTURE §3). Updates live via `systemHealthChanged` subscription.

```
┌── PIT WALL · OPS ──────────────────────────────[✕]─┐
│  MODE   ● LIVE        (or ◐ DEGRADED / ▣ SHOWCASE) │
│  ───────────────────────────────────────────────── │
│  GATEWAY      ● HEALTHY      AGENT     ◐ DEGRADED    │  service rows w/ glyph+color
│  DATABASE     ● HEALTHY      BREAKER   ◯ HALF_OPEN   │
│  ───────────────────────────────────────────────── │
│  LIVE TELEMETRY                                     │
│   ACTIVE CONVERSATIONS         12                   │  big mono tabular numerals
│   BEAM PROCESSES               4,318                 │
│   P95 FIRST TOKEN              312 ms                │
│   THROUGHPUT                   48.2 tok/s            │  ramps to true value, not timer
│   UPTIME                       6d 14:22:08           │
│  ───────────────────────────────────────────────── │
│   LLM SPEND TODAY        $0.42 / $2.00 remaining    │  thin progress bar (azure→amber near cap)
│   OBAN JOBS 24h          37    LAST SYNC  2h ago     │
│  ───────────────────────────────────────────────── │
│  [a tiny sparkline of tok/s over the last minute]   │
└─────────────────────────────────────────────────────┘
```

- The mode badge at top mirrors the masthead `StatusBadge` (shared component, same tokens — system unity `[NLM]`).
- `THROUGHPUT` increments are welded to visible events (each batch arrival nudges the number) — causality, not a periodic timer `[NLM]`.

### 3.5 Footer (disclaimer — prominent, mandatory)

```
┌──────────────────────────────────────────────────────────────────────┐
│ ⚠ ChatFormula1 is an unofficial fan project. Not affiliated with,      │
│   endorsed by, or connected to Formula 1, the FIA, or any F1 team.     │
│   ───────────────────────────────────────────────────────────────     │
│   GitHub · Architecture · GraphiQL    ·    build 97b316a · $0/mo       │
└──────────────────────────────────────────────────────────────────────┘
```

- Disclaimer is **always visible text** (not hidden in a tooltip), `--text-dim` but ≥ AA contrast, with a small caution glyph (the `⚠` is an original inline-SVG triangle, not an emoji).
- Footer is high-contrast enough to be read but visually quiet; it appears on every route.

---

## 4. Component Inventory

shadcn/ui primitives provide accessible scaffolding; custom components carry the design identity. **No emoji anywhere** — all glyphs are inline SVG from an original set (see iconography).

### 4.1 Mapped to shadcn/ui primitives

| Need | shadcn primitive | Theming |
|---|---|---|
| Composer input | `Textarea` (auto-grow) | surface-3, azure focus ring, mono placeholder `▸ Ask the pit wall…` |
| Send / buttons | `Button` | `primary`=azure, `ghost`, `secondary`=surface-2 |
| Suggested + demo chips | `Badge` (interactive) or `Button` size=sm | chip surface, hover → azure hairline + 2px lift |
| Ops panel | `Sheet` (right side) | surface-1, grace transition 560ms |
| Standings table | `Table` | mono numeric cols, hover row → azure left-rail |
| Driver/round cards | `Card` | surface-1 + hairline, ghost numeral |
| Status detail tabs | `Tabs` | mono labels |
| Tooltips (badge meanings) | `Tooltip` | surface-2, explains glyph+color |
| Toasts (errors) | `Sonner` | amber for retryable, critical for hard down |
| Mobile nav | `Tabs`/custom | bottom bar |
| Skeletons | `Skeleton` | shimmer in azure-dim, pre-allocates height |

### 4.2 Custom components

**`TelemetryStrip`** — the live pipeline indicator. Horizontal row of pipeline nodes mapped 1:1 to the `AgentNode` enum (ARCHITECTURE §3), connected by edges, with a `p95 / tok/s` mini-readout on the right.
- Nodes: ANALYZE_QUERY · ROUTE · VECTOR_SEARCH / WEB_SEARCH / PARALLEL_RETRIEVAL · RANK_CONTEXT · GENERATE · FORMAT_RESPONSE. (WARMING_UP and REPLAYING_CACHE are special states, see below.)
- States per node: `idle` (faint, hairline ring) → `active` (azure ring + breathing) → `complete` (green check, dim). Routing branch (VECTOR vs WEB vs PARALLEL) shown as a fork; only the taken branch lights.
- Driven by `NodeTransition` events. Active node = the strip's focus; a **Traveling Signal** packet animates along the connector from the previous node into the active one (the causality money-shot). `GENERATE` node gets the lime glow + faster breathe (the "engine firing"). `[NLM]`
- `REPLAYING_CACHE` state: the whole strip shifts to a neutral/amber tint with a "▣ REPLAY" label and a "replayed from cache" honest badge (SHOWCASE mode). No fake node flight — a single calm REPLAY indicator.
- Right readout: `p95FirstTokenMs` and `tokensPerSecond` in mono tabular, updating live.

**`TokenStream` (assistant bubble)** — the streaming answer.
- Skeleton-first: on `PENDING`, reserve `min-height: 1.55em` × est. lines; `contain: layout`; `max-width: 65ch`. Zero CLS. `[NLM]`
- Renders `TokenDelta` batches (40ms/12-token cadence from the gateway) as **word-group materializations**: each batch fades+rises (`opacity 0→1, translateY(8px)→0`, 200ms `--ease-reveal`). Never per-character typewriter. `[NLM]`
- **Luminous Caret** trails the last token: 2px azure pill, `1em` tall, spring-pulses `{150,15,0.1}` on each batch, oscillates opacity 0.4↔1.0 (300ms) during pauses. Removed on `MessageCompleted`. `[NLM]`
- Cache-hit path: gateway synthesizes one full `TokenDelta` (ARCHITECTURE §4.5) — the bubble reveals the whole text as one fast graceful materialization + a `cached` badge; no fake token-ticking.
- Safe inline renderer (no `dangerouslySetInnerHTML`, no md lib): group blank-line-separated paragraphs and `- ` runs into `<ul>`; `**bold**`→`<strong>`. Re-parse each tick so structure appears progressively. (Reuses the proven approach from prior work `[UNVERIFIED transfer]`.)
- Footer row: `latencyMs` · `tok/s` · `live|cached` badge · feedback 👍/👎 (`submitFeedback`).

**`LightsOutLoader`** — the warming-up state. Five-light F1-start gantry + pit-radio log. Full spec & timing in §5.1.

**`StatusBadge`** — the LIVE / DEGRADED / SHOWCASE pill. Glyph + color + mono label. `● LIVE` (green), `◐ DEGRADED` (amber, slow pulse), `▣ SHOWCASE` (amber, "replayed from cache" on hover). Click → opens `PitWallPanel`. Lives in masthead AND at the top of the panel (shared). Drives off `systemHealth.mode` + `systemHealthChanged` subscription so it flips in real time.

**`CitationChip`** — a source as a chip. `◆`=VECTOR (filled diamond, azure), `◇`=WEB (hollow diamond, azure-dim) + truncated title + score on hover. Appears *before* the answer completes (`SourcesResolved`). Staggered entrance (100ms, scale 0.96→1, `--spring-soft`). ≥44px touch target. Opens `url` in new tab (`rel="noopener"`, "(opens in a new tab)" SR label) when WEB; VECTOR shows a snippet popover.

**`CountdownHero`** — next-race hero on Calendar (and a compact variant on the chat empty-state). Round number, circuit, country, big DD:HH:MM:SS tabular numerals counting down to `nextRace.startsAt`. Digit slots fixed-width; seconds flips 120ms. The country/circuit are plain text (no flags-as-emoji, no track logos).

**`StandingsTable`** — see §3.3. Mono numeric columns, hover azure left-rail, mobile→cards. Driver→constructor shown inline (the Dataloader no-N+1 showcase is invisible to the user but the data is dense and correct).

**`PitWallPanel`** — the ops slide-over (§3.4). Renders `systemStats` + `systemHealth`. Big tabular numerals, service-status rows, spend progress bar, tok/s sparkline. Throughput welded to event arrivals `[NLM]`.

**`PitRadioLog`** — the mono `aria-live` log used inside `LightsOutLoader` and reusable for the ops event feed. Each line: `0x__  MESSAGE  status-glyph`. Lines enter `translateY(8px)→0`.

### 4.3 Original iconography (NO emoji, NO F1 marks)

A single inline-SVG icon set, `currentColor`, 1.5px stroke, geometric/instrument style:
- **apex** ◇ (logo — cornering line)
- **signal** ● / packet dot
- **vector** ◆ filled diamond · **web** ◇ hollow diamond
- **shield** (guardrail), **loop** (idempotent/retry), **arrow** (transit) — the functional status signifiers `[NLM]`
- **check** (complete/healthy), **caution-triangle** (degraded/warning — replaces ⚠ emoji), **x-octagon** (down/critical), **half-disc ◐** (degraded), **square ▣** (showcase/replay)
- **bolt ⚡→⌁** (energy/send — drawn as a clean lightning glyph), **clock** (latency/uptime)
- All status glyphs are visually distinct in *shape* so they read without color (colorblind-safe). `[NLM]`

---

## 5. Animation Specs

Every spec below includes its reduced-motion fallback. Token-stream text must never shift layout while animating.

### 5.1 Lights-out warming sequence (timing diagram)

Maps to `WARMING_UP` events / cold-start. Honest about the ~30–60s Render cold start (ARCHITECTURE §7). `[NLM]`

```
T (s) │ LIGHTS                    │ PIT-RADIO LOG                       │ NOTES
──────┼───────────────────────────┼─────────────────────────────────────┼──────────────────────
0.0   │ all dark                  │ 0x01 GATEWAY ONLINE        ✓green    │ PHASE 1 — Ignition
0.4   │ light 1 ● ON (azure)      │   (light snaps on, spring 150/15/.1) │ <50ms ack per light
0.8   │ light 2 ● ON              │ 0x02 WAKING INFERENCE…     ⟳amber    │
1.2   │ light 3 ● ON              │                                     │
1.6   │ light 4 ● ON              │ 0x03 COLD START ~45s       …azure    │
2.0   │ light 5 ● ON (all five)   │                                     │ all lit by ~2s
2.0–  │ all five BREATHE          │ (log idle)                          │ PHASE 2 — Building
45.0  │  scale 1.0→1.03 @2800ms   │ every ~10s a new tech-log token:    │   Tension
      │  azure, gentle            │   0x04 HYDRATING VECTOR INDEX…      │ Onion-peel info layering
      │                           │   0x05 COMPILING GRAPH…             │
      │                           │   0x06 NEGOTIATING UPSTREAM…        │
45.0– │ breathe → faster (1000ms) │ "Link 5 of 5 · almost green"        │ PHASE 3 — Climax
60.0  │  + slight amber warm tint │ (Zeigarnik tension, Goal-Gradient)  │
──────┼───────────────────────────┼─────────────────────────────────────┼──────────────────────
RESOLVE (agent ready / first NodeTransition arrives):
      │ all 5 extinguish together │ 0x07 LIGHTS OUT · STREAMING   ✓green│ Peak-End: 400ms green
      │ (200ms) → 400ms GREEN     │                                     │   Luminous flash, then
      │ Luminous flash            │                                     │   View-Transition morph
      │ → morph into TokenStream  │                                     │   strip into chat
```

- **Early completion (< target):** never jump. **20% Speed Rule** `[NLM]` — fast-forward any unlit lights with 300ms staggers, then resolve. The system must visually "earn" the finish.
- **Overrun (> 60s):** lights go **amber**, copy switches to active-waiting technical metadata ("Negotiating high-latency gateway…", "Render free tier · still spooling"), **never** "broken." A subtle retry affordance appears at ~75s.
- **Reduced motion:** no light snaps, no breathing, no flash. Static five amber/green dots showing progress as a determinate-ish stepper, the pit-radio log still prints (it is informative text), and resolution is an instant swap. Copy carries the whole experience.
- **a11y:** the pit-radio log is the `aria-live="polite"` spine — every phase has a text equivalent ("Gateway online. Waking inference engine. Cold start, about 45 seconds."). The lights are `aria-hidden` decoration.

### 5.2 Token-stream cadence

- Gateway flushes **40ms / 12 tokens** (ARCHITECTURE §4.4). The client renders each flush as one **word-group** materialization: `opacity 0→1`, `translateY(8px)→0`, 200ms `--ease-reveal`, no stagger inside a group (the group is the unit). `[NLM]`
- Caret behavior as in `TokenStream` §4.2.
- **No layout shift:** `min-height` pre-allocation + `max-width: 65ch` + line-height 1.55 + `contain: layout`. Verified mentally against CLS: incoming words extend the already-reserved block; the bubble height grows in whole line increments only.
- **Reduced motion:** each flush appears instantly at `opacity:1` (no rise, no caret pulse — a steady non-blinking caret or none). Text still streams (content arrival is not motion).

### 5.3 Node-transition strip behavior

Per `NodeTransition` event, within the Doherty <400ms budget `[NLM]`:
```
T+0    departure node → anticipation scale(0.95), 150ms
T+50   Traveling-Signal packet launches along connector (offset-path) +
       marching-ants stroke-dashoffset on the edge
T+250  packet arrives at target node → follow-through pulse scale(1.1) +
       azure glow (spring 150/15/.1); previous node settles to "complete" (green check, dim)
T+320  target node settles into breathing (2800ms cycle); GENERATE adds lime glow + 1800ms breathe
```
- The right-side `p95 / tok/s` readout updates on arrival, welded to the event (causality).
- **Reduced motion:** no packet flight, no scale pulses, no breathing. Instant state-swap: previous→complete (green check), target→active (azure ring + 7:1 mono label). The strip remains fully legible as a labeled stepper. `[NLM]`

### 5.4 Micro-interactions

- **Chip / button hover:** 2px lift (`translateY(-2px)`), hairline→azure hairline, 120ms `--spring-soft`. Reduced motion: color-only.
- **Composer focus:** azure ring fades in 120ms; placeholder dims. Send button enabled state = azure fill; disabled = surface-2 + faint.
- **Citation chip entrance:** stagger 100ms, scale 0.96→1, `--spring-soft`. Reduced motion: instant.
- **StatusBadge flip (LIVE→SHOWCASE etc.):** cross-fade label + glyph 200ms, a single soft pulse of the new color. Reduced motion: instant swap.
- **Countdown second tick:** 120ms digit fade/flip. Reduced motion: instant.
- **Standings row hover:** azure left-rail (3px) slides in 120ms. Reduced motion: instant border.
- **Route transitions:** View Transitions API where supported, 560ms `--d-grace` cross-fade; fallback opacity fade. Reduced motion: instant. The chat↔warming morph uses a View Transition to morph the lights gantry into the strip.

### 5.5 Ambient / "alive" motion (used sparingly)

- Active strip node breathing (2800ms), GENERATE breathing (1800ms + lime).
- LIVE dot in StatusBadge: slow 3.4s opacity pulse. SHOWCASE/DEGRADED: amber, same cadence.
- Throughput numbers nudge on event arrival (not a timer).
- **All ambient motion fully disabled under reduced motion.** Nothing should loop forever for a reduced-motion user.

---

## 6. Accessibility Notes (per component)

Baseline: WCAG **AA** (body text AAA at >7:1), full keyboard operability, visible azure focus rings (never `outline:none` without replacement), every interactive target ≥44×44px (Fitts), `prefers-reduced-motion` honored everywhere, `prefers-contrast` respected (hairlines strengthen).

- **Global shell:** semantic landmarks (`<header><nav><main><footer>`); skip-to-content link; nav `aria-current="page"`; one visible `<h1>` per route.
- **TelemetryStrip:** decorative canvas/SVG packet flight is `aria-hidden`. A parallel `aria-live="polite"` text spine announces transitions ("Vector search active", "Generating response"). Each node has an accessible name + state (`aria-label="Rank context — complete"`). Color always paired with glyph + text label. `[NLM]`
- **TokenStream:** answer container `aria-live="polite"` `aria-atomic="false"` so SRs read incremental additions without re-reading the whole message; caret `aria-hidden`. Final message is a normal readable block. Code/links keyboard-focusable.
- **LightsOutLoader:** lights `aria-hidden`; the `PitRadioLog` is the `aria-live="polite"` source of truth with full sentence equivalents for each phase; an `aria-busy="true"` on the region; resolution announces "Connected, response streaming."
- **StatusBadge:** `<button>` with `aria-haspopup="dialog"`, `aria-label="System status: live. Open ops panel."`; the dot/glyph is supplementary to the text label.
- **CitationChip:** `<a>` or `<button>`; SR label includes kind + title ("Source, vector: 2026 regulations"); external links announce "(opens in a new tab)"; score available to SR.
- **CountdownHero:** the live ticking digits are NOT in an aggressive live region (would spam SRs every second); instead an `aria-label` on the container gives a coarse human string ("Next race in 2 days, 14 hours") updated at most once/minute; visual digits `aria-hidden`.
- **StandingsTable:** real `<table>` with `<caption>`, `<th scope>`; mobile card variant uses a definition-list/row structure with labels; sortable headers are `<button>` with `aria-sort`.
- **PitWallPanel:** `Sheet` = focus-trapped `role="dialog"` with labelled title, Esc to close, focus returns to the StatusBadge; live numbers in a `polite` region but throttled.
- **Composer:** labelled `<textarea>`; Enter sends, Shift+Enter newline (documented in helper text); error states announced via toast + `aria-describedby`; focus stays in composer after send, moves to the streaming message only when it begins (announced).
- **Footer disclaimer:** plain persistent text (not a tooltip), AA contrast, in a `<footer>` landmark.
- **Color-blind:** verified shapes differ across all status glyphs; never rely on azure-vs-lime or amber-vs-green alone.

---

## 7. What NOT To Do (anti-slop rules)

1. **No generic AI gradients.** No purple→blue or teal→indigo background gradients on cards or the hero. No "magic gradient" buttons. Surfaces are flat carbon + hairline + the one optional carbon-twill texture. `[NLM]`
2. **No purple-blue SaaS default palette.** The identity is asphalt/carbon + telemetry azure + electric lime + thermal amber + finish green. Azure is functional only; never a decorative purple-blue glow soup.
3. **No emoji as icons.** Every glyph is from the original inline-SVG set (§4.3). No 🏎️ 🏁 🤖 ⚙️ anywhere — not in chips, badges, the loader, or the disclaimer. The caution mark is a drawn triangle, not ⚠️.
4. **No typewriter character-tick** for streaming. Vertical word-group materialization only; no horizontal per-char ticking, no shimmer. `[NLM]`
5. **No "Inter for everything."** Serif (Spectral) for editorial headlines, mono (JetBrains) for ALL telemetry/numbers/labels, Inter for the reading voice only. `[NLM]`
6. **No dead spinner anywhere.** The cold start is the LightsOutLoader; smaller waits use skeletons that pre-allocate height. No infinite generic ring spinner, ever.
7. **No linear easing, no SaaS bounce.** Organic motion uses the signal spring `{150,15,0.1}`; mature transitions use `cubic-bezier(0.16,1,0.3,1)` ≥500ms. `[NLM]`
8. **No layout shift on stream.** Pre-allocate, `contain: layout`, tabular-nums on every counter. CLS target 0.
9. **No fake telemetry.** Numbers come only from `systemStats` (ARCHITECTURE §8 — "only telemetry-fed numbers, no theater"). The SHOWCASE replay is labeled honestly ("replayed from cache"); never disguise it as live.
10. **No F1 trademark surfaces.** No official wordmark, no F1 proprietary typeface, no team logos/liveries/driver-helmet art, no brand red as identity, no copied broadcast-graphics package, no track-map logos. Country/circuit names are plain text. The logo is the original apex glyph.
11. **No color-only status.** Every state pairs color with a distinct-shape glyph and (where space allows) a text label.
12. **No backdrop-filter soup.** Restrict `backdrop-filter` to at most the masthead and the ops sheet scrim; never stack blurs (GPU budget). `[NLM]`
13. **No hiding the disclaimer.** It is persistent, readable footer text on every route — legal requirement and an honesty signal.

---

## 8. Build-agent quick map (GraphQL → UI)

| GraphQL (ARCHITECTURE §3) | Renders as |
|---|---|
| `agentStream` → `NodeTransition` | `TelemetryStrip` node activation + Traveling Signal |
| `agentStream` → `TokenDelta` (batched) | `TokenStream` word-group materialization + caret |
| `agentStream` → `SourcesResolved` | `CitationChip`s above the answer (before complete) |
| `agentStream` → `MessageCompleted` (cached, usage) | latency/tok/s/cached badge row; remove caret |
| `agentStream` → `AgentError` (retryable) | amber toast + inline retry; non-retryable → critical |
| `AgentNode.WARMING_UP` | `LightsOutLoader` (§5.1) |
| `AgentNode.REPLAYING_CACHE` | strip REPLAY state + SHOWCASE badge |
| `systemHealth.mode` / `systemHealthChanged` | `StatusBadge` (masthead + panel) |
| `systemStats` | `PitWallPanel` numerals + sparkline |
| `standings(season)` | `StandingsTable` |
| `nextRace` | `CountdownHero` |
| `races(season)` | Calendar round cards |
| `drivers(season)` / `driver(code)` | Driver card grid / detail |
| `demoQuestions` | empty-state + suggested chips (Hick: cap at 4–5 visible) |
| `rateLimitStatus` | subtle remaining-requests hint near composer |

---

*End of spec. Mood: Telemetry Noir. Every motion has a reduced-motion branch; every status has a glyph; every number is tabular mono; the cold start is the show; the disclaimer never hides; and not one pixel imitates the F1 brand.*
