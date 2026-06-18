import type { Cell, ContractIndex } from "../contract";
import { BandChip } from "./BandLegend";
import { Collapsible } from "./Collapsible";
import { Markdown } from "./Markdown";

/**
 * The judge verdicts for one cell, filtered to the selected scope. All text is
 * rendered as escaped plain text (React default) — never raw HTML. A missing
 * `rationale` (e.g. a re-judged override) is simply omitted.
 */
export function Verdicts({
  index,
  cell,
  scope,
}: {
  index: ContractIndex;
  cell: Cell;
  scope?: string;
}) {
  const verdicts = cell.verdicts.filter((v) => scope === undefined || v.scope === scope);
  if (verdicts.length === 0) {
    return <p className="no-data">No verdicts for this scope.</p>;
  }
  return (
    <div className="verdicts">
      {verdicts.map((v, i) => (
        <div className="verdict" key={`${v.judge}-${v.scope ?? ""}-${i}`}>
          <div className="verdict-head">
            <BandChip index={index} value={v.band} label={v.bandLabel} />
            <span className="verdict-judge">{judgeLabel(index, v.judge)}</span>
          </div>
          {v.summary && (
            <Markdown text={v.summary} className="verdict-summary" />
          )}
          {v.rationale && (
            <Collapsible>
              <Markdown text={v.rationale} className="verdict-rationale" />
            </Collapsible>
          )}
        </div>
      ))}
    </div>
  );
}

function judgeLabel(index: ContractIndex, id: string): string {
  return index.judges.find((j) => j.id === id)?.label ?? id;
}
