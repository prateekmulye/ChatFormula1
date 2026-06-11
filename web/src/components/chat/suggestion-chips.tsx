/**
 * Suggested questions for the empty state and below the conversation.
 *
 * Static for Phase 4: the `demoQuestions` query (chips wired to pre-warmed
 * SHOWCASE answers) ships with Phase 5 — these constants are replaced by it.
 * Hick's law: at most 5 visible (DESIGN.md §3.1).
 */
const SUGGESTED_QUESTIONS: readonly string[] = [
  "Who leads the drivers' championship?",
  "When is the next race?",
  "How do the 2026 regulations change the cars?",
  "Compare Verstappen and Norris this season",
];

export function SuggestionChips({
  onPick,
  disabled,
}: {
  onPick: (question: string) => void;
  disabled: boolean;
}) {
  return (
    <ul aria-label="Suggested questions" className="flex flex-wrap gap-2">
      {SUGGESTED_QUESTIONS.slice(0, 5).map((question) => (
        <li key={question}>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onPick(question)}
            className="min-h-11 rounded-sm border border-hairline bg-surface-2 px-3 py-2 text-meta text-text-dim
              transition-all duration-120 hover:-translate-y-0.5 hover:border-azure/50 hover:text-text
              disabled:pointer-events-none disabled:opacity-50 motion-reduce:hover:translate-y-0"
          >
            {question}
          </button>
        </li>
      ))}
    </ul>
  );
}
