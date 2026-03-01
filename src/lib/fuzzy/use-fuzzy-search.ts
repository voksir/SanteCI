import { useMemo, useState, useEffect, useRef } from "react";
import Fuse, { type FuseOptionKey } from "fuse.js";
import { BASE_FUSE_OPTIONS } from "./fuse-config";
import type { FuzzyResult, UseFuzzySearchOptions } from "./types";

export function useFuzzySearch<T>(
  items: T[],
  query: string,
  keys: Array<FuseOptionKey<T>>,
  options: UseFuzzySearchOptions = {}
): {
  results: T[];
  fuzzyResults: FuzzyResult<T>[];
  isSearching: boolean;
  isFuzzyMode: boolean;
  debouncedQuery: string;
} {
  const {
    threshold = 0.35,
    debounceMs = 200,
    minChars = 2,
  } = options;

  const [debouncedQuery, setDebouncedQuery] = useState(query);
  const [isSearching, setIsSearching] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    const q = query.trim();
    if (q.length > 0 && q.length < minChars) {
      return;
    }
    setIsSearching(true);
    timerRef.current = setTimeout(() => {
      setDebouncedQuery(q);
      setIsSearching(false);
    }, debounceMs);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query, debounceMs, minChars]);

  const fuse = useMemo(() => {
    return new Fuse(items, {
      ...BASE_FUSE_OPTIONS,
      keys,
      threshold,
    });
  }, [items, keys, threshold]);

  const fuzzyResults = useMemo((): FuzzyResult<T>[] => {
    const q = debouncedQuery.trim();
    if (!q) {
      return items.map((item) => ({ item, score: 0, isFuzzy: false }));
    }
    if (q.length < minChars) {
      return items.map((item) => ({ item, score: 0, isFuzzy: false }));
    }
    const raw = fuse.search(q);
    return raw.map((r) => ({
      item: r.item,
      score: r.score ?? 1,
      matches: r.matches as FuzzyResult<T>["matches"],
      isFuzzy: (r.score ?? 1) > 0.05,
    }));
  }, [fuse, debouncedQuery, items, minChars]);

  const results = fuzzyResults.map((r) => r.item);
  const isFuzzyMode =
    debouncedQuery.trim().length >= minChars &&
    fuzzyResults.length > 0 &&
    fuzzyResults.some((r) => r.isFuzzy);

  return {
    results,
    fuzzyResults,
    isSearching,
    isFuzzyMode,
    debouncedQuery,
  };
}
