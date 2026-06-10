import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "@/components/telemetry/status-badge";

describe("StatusBadge mode mapping", () => {
  it("LIVE renders the green signal dot with a mono label", () => {
    render(<StatusBadge mode="LIVE" />);
    const badge = screen.getByRole("button", { name: /system status: live/i });
    expect(badge).toHaveTextContent("LIVE");
    expect(badge.className).toContain("text-green");
    expect(badge).toHaveAttribute("aria-haspopup", "dialog");
  });

  it("DEGRADED renders amber with the half-disc glyph semantics", () => {
    render(<StatusBadge mode="DEGRADED" />);
    const badge = screen.getByRole("button", { name: /system status: degraded/i });
    expect(badge).toHaveTextContent("DEGRADED");
    expect(badge.className).toContain("text-amber");
  });

  it("SHOWCASE renders amber and tells the truth about cache replay", () => {
    render(<StatusBadge mode="SHOWCASE" />);
    const badge = screen.getByRole("button", { name: /replayed from cache/i });
    expect(badge).toHaveTextContent("SHOWCASE");
    expect(badge.className).toContain("text-amber");
  });

  it("an unreachable gateway is an honest OFFLINE state, not a fake mode", () => {
    render(<StatusBadge mode={null} unreachable />);
    const badge = screen.getByRole("button", { name: /gateway unreachable/i });
    expect(badge).toHaveTextContent("OFFLINE");
    expect(badge.className).toContain("text-text-faint");
  });

  it("unknown-yet state shows a quiet placeholder", () => {
    render(<StatusBadge mode={null} />);
    expect(screen.getByRole("button", { name: /checking system status/i })).toBeInTheDocument();
  });
});
