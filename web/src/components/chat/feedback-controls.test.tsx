import { MockedProvider, type MockedResponse } from "@apollo/client/testing";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { FeedbackControls } from "@/components/chat/feedback-controls";
import { SubmitFeedbackDocument } from "@/graphql/generated";

function feedbackMock(
  helpful: boolean,
  options: { delayMs?: number; onCall?: () => void } = {},
): MockedResponse {
  return {
    request: { query: SubmitFeedbackDocument, variables: { messageId: "m1", helpful } },
    delay: options.delayMs,
    maxUsageCount: Number.POSITIVE_INFINITY,
    result: () => {
      options.onCall?.();
      return { data: { submitFeedback: true } };
    },
  };
}

function renderControls(mocks: MockedResponse[]) {
  return render(
    <MockedProvider mocks={mocks}>
      <FeedbackControls messageId="m1" />
    </MockedProvider>,
  );
}

describe("FeedbackControls", () => {
  it("lights the thumb optimistically, before the mutation resolves", async () => {
    const user = userEvent.setup();
    renderControls([feedbackMock(true, { delayMs: 5_000 })]);

    await user.click(screen.getByRole("button", { name: "Helpful" }));

    // The mock is still 5s away — the pressed state is already on screen.
    expect(screen.getByRole("button", { name: "Helpful" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Not helpful" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("switching verdicts re-submits and moves the pressed state", async () => {
    let downCalls = 0;
    const user = userEvent.setup();
    renderControls([
      feedbackMock(true),
      feedbackMock(false, { onCall: () => (downCalls += 1) }),
    ]);

    await user.click(screen.getByRole("button", { name: "Helpful" }));
    await user.click(screen.getByRole("button", { name: "Not helpful" }));

    expect(screen.getByRole("button", { name: "Not helpful" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Helpful" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    await waitFor(() => expect(downCalls).toBe(1));
  });

  it("re-clicking the active verdict is idempotent — no duplicate mutation", async () => {
    let upCalls = 0;
    const user = userEvent.setup();
    renderControls([feedbackMock(true, { onCall: () => (upCalls += 1) })]);

    const helpful = screen.getByRole("button", { name: "Helpful" });
    await user.click(helpful);
    await user.click(helpful);

    expect(helpful).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => expect(upCalls).toBe(1));
  });

  it("reverts the optimistic state when the mutation fails", async () => {
    const user = userEvent.setup();
    renderControls([
      {
        request: { query: SubmitFeedbackDocument, variables: { messageId: "m1", helpful: true } },
        // Delay keeps the optimistic window observable before the failure lands.
        delay: 100,
        error: new Error("gateway down"),
      },
    ]);

    const helpful = screen.getByRole("button", { name: "Helpful" });
    await user.click(helpful);
    expect(helpful).toHaveAttribute("aria-pressed", "true");

    await waitFor(() => expect(helpful).toHaveAttribute("aria-pressed", "false"));
  });
});
