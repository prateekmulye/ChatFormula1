import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ShowcaseNotice } from "@/components/chat/showcase-notice";

describe("ShowcaseNotice mode mapping", () => {
  it("SHOWCASE shows the honest one-line demo-mode notice", () => {
    render(<ShowcaseNotice mode="SHOWCASE" />);
    const notice = screen.getByRole("status");
    expect(notice).toHaveTextContent(/demo mode/i);
    expect(notice).toHaveTextContent(/replay from cache/i);
    expect(notice).toHaveTextContent(/midnight utc/i);
  });

  it("LIVE renders nothing — no notice noise during normal operation", () => {
    render(<ShowcaseNotice mode="LIVE" />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("DEGRADED renders nothing — degraded has its own badge, not this notice", () => {
    render(<ShowcaseNotice mode="DEGRADED" />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("unknown mode renders nothing", () => {
    render(<ShowcaseNotice mode={null} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
