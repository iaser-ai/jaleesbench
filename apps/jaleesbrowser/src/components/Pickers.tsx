import { useMemo, useState } from "react";
import type { ContractIndex } from "../contract";
import type { Selection } from "../urlstate";

/**
 * The selection UI, built ENTIRELY from the index — one searchable question
 * picker, two subject pickers, one selector per condition axis, and a scope
 * selector. No JaleesBench-specific strings: axis keys/labels and option labels
 * all come from `index`.
 */
export function Pickers({
  index,
  selection,
  onChange,
}: {
  index: ContractIndex;
  selection: Selection;
  onChange: (next: Selection) => void;
}) {
  const [filter, setFilter] = useState("");

  const filteredItems = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return index.items;
    return index.items.filter(
      (it) =>
        it.id.toLowerCase().includes(q) || it.title.toLowerCase().includes(q),
    );
  }, [filter, index.items]);

  const set = (patch: Partial<Selection>) => onChange({ ...selection, ...patch });
  const setCondition = (key: string, value: string) =>
    onChange({ ...selection, conditions: { ...selection.conditions, [key]: value } });

  const currentItemShown = filteredItems.some((it) => it.id === selection.item);

  return (
    <section className="pickers">
      {/* A div (not a <label>): the two controls below carry their own
          aria-labels, so wrapping both in one label would name both ambiguously. */}
      <div className="picker picker-question">
        <span className="picker-caption">Question</span>
        <input
          type="search"
          placeholder="filter by id or title…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          aria-label="Filter questions"
        />
        <select
          value={selection.item}
          onChange={(e) => set({ item: e.target.value })}
          aria-label="Question"
        >
          {/* Keep the current item selectable even when filtered out. */}
          {!currentItemShown && (
            <option value={selection.item}>{itemLabel(index, selection.item)}</option>
          )}
          {filteredItems.map((it) => (
            <option key={it.id} value={it.id}>
              {it.id} — {it.title}
            </option>
          ))}
        </select>
      </div>

      <label className="picker">
        <span>Model A</span>
        <select
          value={selection.a}
          onChange={(e) => set({ a: e.target.value })}
          aria-label="Model A"
        >
          {index.subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
      </label>

      <label className="picker">
        <span>Model B</span>
        <select
          value={selection.b}
          onChange={(e) => set({ b: e.target.value })}
          aria-label="Model B"
        >
          {/* "" = none → the comparison collapses to a single-model view. */}
          <option value="">None (single view)</option>
          {index.subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
      </label>

      {index.conditionAxes.map((axis) => (
        <label key={axis.key} className="picker">
          <span>{axis.label}</span>
          <select
            value={selection.conditions[axis.key] ?? ""}
            onChange={(e) => setCondition(axis.key, e.target.value)}
            aria-label={axis.label}
          >
            {axis.values.map((v) => (
              <option key={v.id} value={v.id}>
                {v.label}
              </option>
            ))}
          </select>
        </label>
      ))}
    </section>
  );
}

function itemLabel(index: ContractIndex, itemId: string): string {
  const it = index.items.find((i) => i.id === itemId);
  return it ? `${it.id} — ${it.title}` : itemId;
}
