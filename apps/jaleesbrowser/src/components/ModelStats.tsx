import type { ContractIndex } from "../contract";
import { signed } from "../format";
import { subjectStats } from "../scores";

const fmt = (v: number | null): string =>
  v === null ? "—" : signed(Math.round(v * 100) / 100);

/**
 * The paper's aggregate stats for the two compared models, computed client-side
 * from the score blob (no shard loads, no new data): a headline (overall mean,
 * recognition gain, steadfastness) side by side, plus a mean-by-value breakdown
 * for each condition axis (e.g. by pressure, by framing). All on the −1…+1 scale.
 */
export function ModelStats({
  index,
  a,
  b,
}: {
  index: ContractIndex;
  a: string;
  b: string;
}) {
  const sa = subjectStats(index, a);
  const sb = subjectStats(index, b);
  const la = subjectLabel(index, a);
  const lb = subjectLabel(index, b);
  const recAxis = sa.recognitionAxisLabel;

  return (
    <section className="model-stats" aria-label={`Stats: ${la} vs ${lb}`}>
      <table className="stats-table">
        <thead>
          <tr>
            <th>Headline</th>
            <th>{la}</th>
            <th>{lb}</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Overall (mean band)</td>
            <td>{fmt(sa.overall)}</td>
            <td>{fmt(sb.overall)}</td>
          </tr>
          <tr>
            <td>Recognition gain{recAxis ? ` (by ${recAxis})` : ""}</td>
            <td>{fmt(sa.recognition)}</td>
            <td>{fmt(sb.recognition)}</td>
          </tr>
          <tr>
            <td>Steadfastness (post − initial)</td>
            <td>{fmt(sa.steadfastness)}</td>
            <td>{fmt(sb.steadfastness)}</td>
          </tr>
        </tbody>
      </table>

      {sa.byAxis.map((axA, i) => {
        const axB = sb.byAxis[i];
        return (
          <table key={axA.key} className="stats-table">
            <thead>
              <tr>
                <th>By {axA.label}</th>
                <th>{la}</th>
                <th>{lb}</th>
              </tr>
            </thead>
            <tbody>
              {axA.values.map((va, j) => (
                <tr key={va.id}>
                  <td>{va.label}</td>
                  <td>{fmt(va.mean)}</td>
                  <td>{fmt(axB?.values[j]?.mean ?? null)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      })}
    </section>
  );
}

function subjectLabel(index: ContractIndex, id: string): string {
  return index.subjects.find((s) => s.id === id)?.label ?? id;
}
