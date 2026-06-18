import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { Collapsible } from "./Collapsible";

// jsdom does no layout, so scrollHeight is always 0; stub it to simulate overflow.
function stubScrollHeight(px: number) {
  Object.defineProperty(HTMLElement.prototype, "scrollHeight", {
    configurable: true,
    get() {
      return px;
    },
  });
}

afterEach(() => {
  delete (HTMLElement.prototype as { scrollHeight?: number }).scrollHeight;
});

describe("Collapsible", () => {
  it("shows a toggle and expands/collapses when content overflows", () => {
    stubScrollHeight(1000);
    render(
      <Collapsible>
        <p>long content</p>
      </Collapsible>,
    );
    const toggle = screen.getByRole("button", { name: "Show more" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(screen.getByRole("button", { name: "Show less" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    fireEvent.click(screen.getByRole("button", { name: "Show less" }));
    expect(screen.getByRole("button", { name: "Show more" })).toBeInTheDocument();
  });

  it("shows no toggle when content fits", () => {
    stubScrollHeight(40);
    render(
      <Collapsible>
        <p>short</p>
      </Collapsible>,
    );
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.getByText("short")).toBeInTheDocument();
  });
});
