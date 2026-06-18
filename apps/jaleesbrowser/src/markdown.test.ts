import { describe, expect, it } from "vitest";
import { renderMarkdown } from "./markdown";

describe("renderMarkdown", () => {
  it("renders markdown formatting", () => {
    const html = renderMarkdown("**bold** and *italic*");
    expect(html).toContain("<strong>bold</strong>");
    expect(html).toContain("<em>italic</em>");
  });

  it("does not execute raw HTML — a literal <script> is inert text", () => {
    const html = renderMarkdown("hi <script>alert(1)</script> there");
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
  });

  it("allows http/https/mailto links and marks them external", () => {
    const html = renderMarkdown("[site](https://example.com) [mail](mailto:a@b.com)");
    expect(html).toContain('href="https://example.com"');
    expect(html).toContain('href="mailto:a@b.com"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain('target="_blank"');
  });

  it("never produces a javascript: href (markdown-it refuses it; no executable link)", () => {
    const html = renderMarkdown("[x](javascript:alert(1))");
    expect(html).not.toMatch(/href\s*=\s*["']?\s*javascript:/i);
    expect(html).toContain("x"); // text preserved, inert
  });

  it("DOMPurify strips a non-allowlisted scheme that markdown-it permits (tel:)", () => {
    const html = renderMarkdown("[call](tel:123)");
    expect(html).not.toContain("tel:123"); // href removed by the scheme allowlist
    expect(html).toContain("call"); // link text preserved
  });
});
