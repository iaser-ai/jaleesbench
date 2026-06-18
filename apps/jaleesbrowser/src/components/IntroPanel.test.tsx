import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { IntroPanel } from "./IntroPanel";

afterEach(() => window.localStorage.clear());

const PAPER = { url: "https://example.com/paper.pdf", label: "The paper", draft: true };

describe("IntroPanel", () => {
  it("is open on first visit and links the (draft) paper", () => {
    render(<IntroPanel paper={PAPER} />);
    expect(screen.getByText(/righteous companion/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "The paper" });
    expect(link).toHaveAttribute("href", PAPER.url);
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText(/draft — under review/)).toBeInTheDocument();
  });

  it("starts collapsed once the visitor has seen it", () => {
  window.localStorage.setItem("orient-seen", "1");
    render(<IntroPanel paper={PAPER} />);
    expect(screen.queryByText(/righteous companion/)).toBeNull();
    // still toggleable
    fireEvent.click(screen.getByRole("button", { name: /About this dataset/ }));
    expect(screen.getByText(/righteous companion/)).toBeInTheDocument();
  });
});
