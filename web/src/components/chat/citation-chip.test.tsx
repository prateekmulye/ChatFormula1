import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CitationChip } from "@/components/chat/citation-chip";

describe("CitationChip kinds", () => {
  it("WEB sources render as a safe external link", () => {
    render(
      <CitationChip
        source={{ kind: "WEB", title: "autosport.com", url: "https://autosport.com/a", snippet: null, score: 0.7 }}
        index={0}
      />,
    );
    const link = screen.getByRole("link", { name: /source, web: autosport\.com/i });
    expect(link).toHaveAttribute("href", "https://autosport.com/a");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    expect(link).toHaveAccessibleName(expect.stringMatching(/opens in a new tab/i));
  });

  it("VECTOR sources render as a snippet-popover button, not a link", () => {
    render(
      <CitationChip
        source={{ kind: "VECTOR", title: "2026 regulations", url: null, snippet: "Article 3.4…", score: 0.83 }}
        index={1}
      />,
    );
    const button = screen.getByRole("button", { name: /source, vector: 2026 regulations/i });
    expect(button).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("includes relevance for screen readers when a score exists", () => {
    render(
      <CitationChip
        source={{ kind: "VECTOR", title: "Tyre rules", url: null, snippet: null, score: 0.5 }}
        index={0}
      />,
    );
    expect(screen.getByRole("button", { name: /relevance 50 percent/i })).toBeInTheDocument();
  });

  it("marks the chip with its kind for styling hooks", () => {
    const { container } = render(
      <CitationChip
        source={{ kind: "WEB", title: "f1 news", url: "https://example.com", snippet: null, score: null }}
        index={0}
      />,
    );
    expect(container.querySelector('[data-kind="WEB"]')).not.toBeNull();
  });
});
