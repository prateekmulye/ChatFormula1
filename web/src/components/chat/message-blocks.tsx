import { Fragment, type ReactNode } from "react";

/**
 * Safe inline renderer for completed answers (DESIGN.md §4.2 TokenStream):
 * no dangerouslySetInnerHTML, no markdown library. Blank-line-separated
 * paragraphs, `- ` runs become lists, `**bold**` becomes <strong>.
 */
function renderInline(text: string): ReactNode {
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return parts.map((part, index) =>
    index % 2 === 1 ? <strong key={index}>{part}</strong> : <Fragment key={index}>{part}</Fragment>,
  );
}

export function MessageBlocks({ content }: { content: string }) {
  const blocks = content
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter((block) => block.length > 0);

  return (
    <>
      {blocks.map((block, blockIndex) => {
        const lines = block.split("\n");
        const isList = lines.every((line) => line.trimStart().startsWith("- "));
        if (isList) {
          return (
            <ul key={blockIndex} className="my-2 list-disc space-y-1 pl-5">
              {lines.map((line, lineIndex) => (
                <li key={lineIndex}>{renderInline(line.trimStart().slice(2))}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={blockIndex} className="my-2 first:mt-0 last:mb-0">
            {renderInline(block)}
          </p>
        );
      })}
    </>
  );
}
