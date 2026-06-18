/**
 * TypeScript types for the exported viewer data (see the app README "Data format").
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

/** A subject's overall mean band (display scale), turn-1 (initial) / full (post). */
export interface SubjectScore {
  initial: number | null;
  post: number | null;
}

export interface SubjectRef {
  id: string;
  label: string;
  overall?: SubjectScore | null;
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

/**
 * A compact numbers-only score blob: subject × item × (each condition axis) ×
 * scope → mean band (display scale), flat row-major; `null` if the cell is absent.
 * Dimension order/lengths come from the index's ordered lists (see `order`/`shape`).
 */
export interface ScoreMatrix {
  order: string[]; // ["subject","item",<axisKey>…,"scope"]
  shape: number[];
  data: (number | null)[];
}

export interface PresetEntry {
  label: string;
  /** A flat URL-param map fed through the same decoder (axis keys stay generic). */
  params: Record<string, string>;
}

export interface Preset {
  key: string;
  label: string;
  description?: string;
  entries: PresetEntry[];
}

export interface Paper {
  url: string;
  label: string;
  draft?: boolean;
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
  /** Optional: powers the instant compare ranking + presets without shard loads. */
  scores?: ScoreMatrix;
  presets?: Preset[];
  paper?: Paper;
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
