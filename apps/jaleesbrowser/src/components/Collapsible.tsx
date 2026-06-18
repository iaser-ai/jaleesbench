import { type ReactNode, useLayoutEffect, useRef, useState } from "react";

/** Collapsed height ≈ 10–11 lines; content taller than this gets a toggle. */
const COLLAPSED_MAX_PX = 220;

/**
 * Clamps long content to ~10 lines with a "Show more / Show less" toggle. Only
 * shows the toggle when the content actually overflows the collapsed height.
 */
export function Collapsible({ children }: { children: ReactNode }) {
  const bodyRef = useRef<HTMLDivElement>(null);
  const [overflowing, setOverflowing] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useLayoutEffect(() => {
    const el = bodyRef.current;
    if (el) setOverflowing(el.scrollHeight > COLLAPSED_MAX_PX + 4);
  }, [children]);

  const collapsed = overflowing && !expanded;
  return (
    <div className="collapsible">
      <div
        ref={bodyRef}
        className={collapsed ? "collapsible-body collapsed" : "collapsible-body"}
        style={collapsed ? { maxHeight: COLLAPSED_MAX_PX } : undefined}
      >
        {children}
      </div>
      {overflowing && (
        <button
          type="button"
          className="collapsible-toggle"
          aria-expanded={expanded}
          onClick={() => setExpanded((x) => !x)}
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}
