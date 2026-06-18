import type { ItemShard } from "../contract";

/**
 * The selected item's metadata: title, the opaque `tags` (rendered generically —
 * the viewer assigns no meaning to specific keys), and the optional `context`
 * (e.g. proof texts) in a collapsible panel. All text is escaped plain text.
 */
export function ItemHeader({ shard }: { shard: ItemShard }) {
  const { item } = shard;
  const tags = item.tags ?? {};
  const tagEntries = Object.entries(tags).filter(([, v]) => !isEmpty(v));
  return (
    <section className="item-header">
      <h2 className="item-title">
        {item.id} — {item.title}
      </h2>
      {tagEntries.length > 0 && (
        <dl className="item-tags">
          {tagEntries.map(([key, value]) => (
            <div className="item-tag" key={key}>
              <dt>{key}</dt>
              <dd>{formatTagValue(value)}</dd>
            </div>
          ))}
        </dl>
      )}
      {item.context && (
        <details className="item-context">
          <summary>Context</summary>
          <div className="item-context-body">{item.context}</div>
        </details>
      )}
    </section>
  );
}

function isEmpty(v: unknown): boolean {
  return v == null || (Array.isArray(v) && v.length === 0) || v === "";
}

function formatTagValue(v: unknown): string {
  if (Array.isArray(v)) return v.map((x) => String(x)).join(", ");
  return String(v);
}
