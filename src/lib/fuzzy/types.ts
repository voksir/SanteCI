/**
 * Types partagés pour le fuzzy search.
 * Réutilise les types du projet (PharmacieDeGarde, Medicament) et ajoute les métadonnées Fuse.
 */

/** Résultat enrichi avec score et matches pour le highlight. */
export interface FuzzyResult<T> {
  item: T;
  score: number;
  matches?: FuseResultMatch[];
  isFuzzy: boolean;
}

export interface FuseResultMatch {
  key?: string;
  indices: ReadonlyArray<[number, number]>;
  value?: string;
}

export interface UseFuzzySearchOptions {
  threshold?: number;
  debounceMs?: number;
  minChars?: number;
  returnFuzzyMeta?: boolean;
}
