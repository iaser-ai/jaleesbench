/**
 * TypeScript types for the results-viewer data contract (see CONTRACT.md).
 *
 * These types are GENERIC — subjects, items, condition axes, a band ladder,
 * judges, transcripts, verdicts. They contain NO JaleesBench-specific strings
 * (no "pressure"/"framing"/"Burns"/probe field names); every such value arrives
 * in the data. This file is the ONLY place the index/shard shapes are named.
 */

export const CONTRACT_MAJOR = 1;

/** A rung on the band ladder, on the display scale (e.g. -1…+1). */
export interface Band {
  value: number;
  label: string;
  color?: string;
  description?: string;
}

export interface SubjectRef {
  id: string;
  label: string;
}

export interface AxisValue {
  id: string;
  label: string;
  description?: string;
}

/** One selectable dimension (JaleesBench emits `pressure` and `framing`). */
export interface ConditionAxis {
  key: string;
  label: string;
  values: AxisValue[];
}

export interface JudgeRef {
  id: string;
  label: string;
}

export interface ScopeRef {
  id: string;
  label: string;
  default?: boolean;
}

/** Opaque, display-only metadata; the viewer assigns no meaning to keys. */
export type Tags = Record<string, unknown>;

export interface ItemRef {
  id: string;
  title: string;
  tags?: Tags;
}

/** The catalog/manifest (`index.json`), loaded once on startup. */
export interface ContractIndex {
  contractVersion: string;
  producer: { name: string; version: string };
  dataset: { title: string; description?: string; language?: string };
  bands: Band[];
  subjects: SubjectRef[];
  conditionAxes: ConditionAxis[];
  judges: JudgeRef[];
  scopes?: ScopeRef[];
  items: ItemRef[];
  /** itemId -> shard path, relative to index.json (gzip-compressed `.json.gz`). */
  shards: Record<string, string>;
}

export interface Turn {
  role: "user" | "assistant";
  content: string;
}

export interface Verdict {
  judge: string;
  scope?: string;
  band: number;
  bandLabel: string;
  summary?: string;
  rationale?: string;
  tags?: Tags;
}

/** One comparable unit: a subject under a condition-tuple. */
export interface Cell {
  subject: string;
  conditions: Record<string, string>;
  transcript: Turn[];
  verdicts: Verdict[];
}

/** A per-item detail shard (gzip-compressed on the wire), loaded on demand. */
export interface ItemShard {
  item: ItemRef & { context?: string };
  cells: Cell[];
}
