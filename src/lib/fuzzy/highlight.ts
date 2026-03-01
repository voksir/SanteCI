import type { FuseResultMatch } from "./types";

export interface HighlightSegment {
  text: string;
  highlighted: boolean;
}

/**
 * Transforme un texte et les indices de match Fuse en segments pour le surlignage.
 */
export function getHighlightSegments(
  text: string,
  matches: ReadonlyArray<FuseResultMatch> | undefined,
  key: string
): HighlightSegment[] {
  if (!matches?.length || !text) {
    return [{ text, highlighted: false }];
  }
  const fieldMatch = matches.find((m) => m.key === key);
  if (!fieldMatch?.indices?.length) {
    return [{ text, highlighted: false }];
  }
  const segments: HighlightSegment[] = [];
  let lastIndex = 0;
  const merged = mergeIndices(fieldMatch.indices);
  for (const [start, end] of merged) {
    if (start > lastIndex) {
      segments.push({ text: text.slice(lastIndex, start), highlighted: false });
    }
    segments.push({ text: text.slice(start, end + 1), highlighted: true });
    lastIndex = end + 1;
  }
  if (lastIndex < text.length) {
    segments.push({ text: text.slice(lastIndex), highlighted: false });
  }
  return segments;
}

function mergeIndices(
  indices: ReadonlyArray<[number, number]>
): Array<[number, number]> {
  const sorted = [...indices].sort((a, b) => a[0] - b[0]);
  const merged: Array<[number, number]> = [];
  for (const [start, end] of sorted) {
    const last = merged[merged.length - 1];
    if (last && start <= last[1] + 1) {
      last[1] = Math.max(last[1], end);
    } else {
      merged.push([start, end]);
    }
  }
  return merged;
}
