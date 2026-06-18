import { renderMarkdown } from "../markdown";

/**
 * Renders sanitized markdown. This is the one sanctioned use of
 * `dangerouslySetInnerHTML` — the HTML comes from `renderMarkdown`, which runs
 * `markdown-it` (raw HTML disabled) through DOMPurify with a link-scheme
 * allowlist (spec §5.6).
 */
export function Markdown({ text, className }: { text: string; className?: string }) {
  return (
    <div
      className={className ? `md ${className}` : "md"}
      // eslint-disable-next-line react/no-danger -- sanitized by renderMarkdown (§5.6)
      dangerouslySetInnerHTML={{ __html: renderMarkdown(text) }}
    />
  );
}
