import { FALLBACK_QUESTIONS } from "@/components/chat/suggestion-fallback";
import { useDemoQuestionsQuery } from "@/graphql/generated";

/** Hick's law: at most 5 visible (DESIGN.md §3.1). */
const MAX_VISIBLE = 5;

export function SuggestionChips({
  onPick,
  disabled,
}: {
  onPick: (question: string) => void;
  disabled: boolean;
}) {
  const { data } = useDemoQuestionsQuery();
  const fromGateway = data?.demoQuestions ?? [];
  const questions = (fromGateway.length > 0 ? fromGateway : FALLBACK_QUESTIONS).slice(
    0,
    MAX_VISIBLE,
  );

  return (
    <ul aria-label="Suggested questions" className="flex flex-wrap gap-2">
      {questions.map((question) => (
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
