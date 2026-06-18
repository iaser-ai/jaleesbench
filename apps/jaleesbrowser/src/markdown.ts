import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";

/**
 * Markdown rendering for model-authored text (transcript responses, judge
 * rationales). Safety (spec §5.6):
 * - `markdown-it` with `html: false` — raw HTML in the source is escaped, not
 *   interpreted (a literal `<script>` renders as text).
 * - DOMPurify sanitizes the generated HTML (defense in depth).
 * - Link schemes are allowlisted to `http`/`https`/`mailto`; anything else
 *   (`javascript:`, …) has its `href` stripped. External links get
 *   `rel="noopener noreferrer"` + `target="_blank"`.
 */

const md = new MarkdownIt({ html: false, linkify: true, breaks: true });

// Only these URI schemes survive sanitization (relative/anchor hrefs are dropped).
const ALLOWED_URI = /^(?:https?:|mailto:)/i;

let hooked = false;
function ensureHook() {
  if (hooked) return;
  DOMPurify.addHook("afterSanitizeAttributes", (node) => {
    if (node.tagName === "A" && node.hasAttribute("href")) {
      node.setAttribute("target", "_blank");
      node.setAttribute("rel", "noopener noreferrer");
    }
  });
  hooked = true;
}

export function renderMarkdown(text: string): string {
  ensureHook();
  const rendered = md.render(text ?? "");
  return DOMPurify.sanitize(rendered, {
    ALLOWED_URI_REGEXP: ALLOWED_URI,
    ADD_ATTR: ["target", "rel"],
  });
}
