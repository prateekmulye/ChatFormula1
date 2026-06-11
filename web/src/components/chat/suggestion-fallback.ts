/**
 * Static fallback for the suggestion chips. The gateway's `demoQuestions`
 * query (chips wired to pre-warmed SHOWCASE answers) is the primary source;
 * these cover the load window and any query error so the chip row is never
 * empty (DESIGN.md §3.1 — the empty state leads with chips).
 *
 * Separate module (not in suggestion-chips.tsx) so the component file only
 * exports components — keeps Fast Refresh intact.
 */
export const FALLBACK_QUESTIONS: readonly string[] = [
  "Who leads the drivers' championship?",
  "When is the next race?",
  "How do the 2026 regulations change the cars?",
  "Compare Verstappen and Norris this season",
];
