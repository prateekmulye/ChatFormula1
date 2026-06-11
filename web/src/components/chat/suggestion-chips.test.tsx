import { MockedProvider, type MockedResponse } from "@apollo/client/testing";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SuggestionChips } from "@/components/chat/suggestion-chips";
import { FALLBACK_QUESTIONS } from "@/components/chat/suggestion-fallback";
import { DemoQuestionsDocument } from "@/graphql/generated";

function demoQuestionsMock(questions: string[]): MockedResponse {
  return {
    request: { query: DemoQuestionsDocument },
    result: { data: { demoQuestions: questions } },
  };
}

const SIX_QUESTIONS = ["Q one?", "Q two?", "Q three?", "Q four?", "Q five?", "Q six?"];

describe("SuggestionChips demoQuestions wiring", () => {
  it("renders gateway demo questions, capped at 5 (Hick's law)", async () => {
    render(
      <MockedProvider mocks={[demoQuestionsMock(SIX_QUESTIONS)]}>
        <SuggestionChips onPick={() => undefined} disabled={false} />
      </MockedProvider>,
    );

    expect(await screen.findByRole("button", { name: "Q one?" })).toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(5);
    expect(screen.queryByRole("button", { name: "Q six?" })).not.toBeInTheDocument();
  });

  it("shows the static fallback while the query is in flight — never an empty row", () => {
    render(
      <MockedProvider mocks={[demoQuestionsMock(SIX_QUESTIONS)]}>
        <SuggestionChips onPick={() => undefined} disabled={false} />
      </MockedProvider>,
    );

    // Before the mock resolves, the fallback chips are already on screen.
    expect(screen.getByRole("button", { name: FALLBACK_QUESTIONS[0] })).toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(FALLBACK_QUESTIONS.length);
  });

  it("falls back to the static list when the query errors", async () => {
    render(
      <MockedProvider
        mocks={[{ request: { query: DemoQuestionsDocument }, error: new Error("gateway down") }]}
      >
        <SuggestionChips onPick={() => undefined} disabled={false} />
      </MockedProvider>,
    );

    // Let the error settle, then confirm the fallback row survived it.
    expect(await screen.findByRole("button", { name: FALLBACK_QUESTIONS[0] })).toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(FALLBACK_QUESTIONS.length);
  });

  it("falls back when the gateway returns an empty list", async () => {
    render(
      <MockedProvider mocks={[demoQuestionsMock([])]}>
        <SuggestionChips onPick={() => undefined} disabled={false} />
      </MockedProvider>,
    );

    expect(await screen.findByRole("button", { name: FALLBACK_QUESTIONS[0] })).toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(FALLBACK_QUESTIONS.length);
  });

  it("clicking a chip forwards the question to onPick", async () => {
    const onPick = vi.fn();
    const user = userEvent.setup();
    render(
      <MockedProvider mocks={[demoQuestionsMock(["When is the next race?"])]}>
        <SuggestionChips onPick={onPick} disabled={false} />
      </MockedProvider>,
    );

    await user.click(await screen.findByRole("button", { name: "When is the next race?" }));
    expect(onPick).toHaveBeenCalledWith("When is the next race?");
  });
});
