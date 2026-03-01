import { supabase } from "@/lib/supabase";
import type {
  Medicament,
  MedicamentsListOptions,
  MedicamentsSearchOptions,
} from "@/types/medicaments";

const TABLE = "medicaments";
const DEFAULT_LIMIT = 50;
const MAX_LIMIT = 200;

function mapRow(row: Record<string, unknown>): Medicament {
  return {
    id: row.id as string,
    code: row.code as string,
    nom_commercial: row.nom_commercial as string,
    groupe_therapeutique: (row.groupe_therapeutique as string) ?? null,
    prix_fcfa: Number(row.prix_fcfa),
    source: (row.source as string) ?? null,
    created_at: row.created_at as string,
    updated_at: row.updated_at as string,
  };
}

/**
 * Liste paginée des médicaments avec filtres et tri.
 */
export async function getMedicaments(
  options: MedicamentsListOptions = {}
): Promise<Medicament[]> {
  const {
    groupe_therapeutique,
    prix_min,
    prix_max,
    sortBy = "nom",
    sortOrder = "asc",
    limit = DEFAULT_LIMIT,
    offset = 0,
  } = options;

  const column =
    sortBy === "nom"
      ? "nom_commercial"
      : sortBy === "groupe"
        ? "groupe_therapeutique"
        : "prix_fcfa";

  let query = supabase
    .from(TABLE)
    .select(
      "id, code, nom_commercial, groupe_therapeutique, prix_fcfa, source, created_at, updated_at"
    );

  if (groupe_therapeutique) {
    query = query.eq("groupe_therapeutique", groupe_therapeutique);
  }
  if (prix_min != null && prix_min > 0) {
    query = query.gte("prix_fcfa", prix_min);
  }
  if (prix_max != null && prix_max > 0) {
    query = query.lte("prix_fcfa", prix_max);
  }

  const safeLimit = Math.min(Math.max(1, limit), MAX_LIMIT);
  const { data, error } = await query
    .order(column, { ascending: sortOrder === "asc", nullsFirst: false })
    .range(offset, offset + safeLimit - 1);

  if (error) throw error;
  return (data ?? []).map(mapRow);
}

/**
 * Recherche par texte sur nom_commercial (et optionnellement groupe_therapeutique).
 */
export async function searchMedicaments(
  searchQuery: string,
  options: MedicamentsSearchOptions = {}
): Promise<Medicament[]> {
  const q = searchQuery.trim();
  if (!q) {
    return getMedicaments(options);
  }

  const {
    groupe_therapeutique,
    prix_min,
    prix_max,
    sortBy = "nom",
    sortOrder = "asc",
    limit = DEFAULT_LIMIT,
    offset = 0,
    searchInGroupe = true,
  } = options;

  const column =
    sortBy === "nom"
      ? "nom_commercial"
      : sortBy === "groupe"
        ? "groupe_therapeutique"
        : "prix_fcfa";

  const pattern = `%${q}%`;

  let queryBuilder = supabase
    .from(TABLE)
    .select(
      "id, code, nom_commercial, groupe_therapeutique, prix_fcfa, source, created_at, updated_at"
    );

  if (searchInGroupe) {
    queryBuilder = queryBuilder.or(
      `nom_commercial.ilike.${pattern},groupe_therapeutique.ilike.${pattern}`
    );
  } else {
    queryBuilder = queryBuilder.ilike("nom_commercial", pattern);
  }

  if (groupe_therapeutique) {
    queryBuilder = queryBuilder.eq("groupe_therapeutique", groupe_therapeutique);
  }
  if (prix_min != null && prix_min > 0) {
    queryBuilder = queryBuilder.gte("prix_fcfa", prix_min);
  }
  if (prix_max != null && prix_max > 0) {
    queryBuilder = queryBuilder.lte("prix_fcfa", prix_max);
  }

  const safeLimit = Math.min(Math.max(1, limit), MAX_LIMIT);
  const { data, error } = await queryBuilder
    .order(column, { ascending: sortOrder === "asc", nullsFirst: false })
    .range(offset, offset + safeLimit - 1);

  if (error) throw error;
  return (data ?? []).map(mapRow);
}

/**
 * Détail d'un médicament par code.
 */
export async function getMedicamentByCode(code: string): Promise<Medicament | null> {
  const { data, error } = await supabase
    .from(TABLE)
    .select(
      "id, code, nom_commercial, groupe_therapeutique, prix_fcfa, source, created_at, updated_at"
    )
    .eq("code", code)
    .maybeSingle();

  if (error) throw error;
  return data ? mapRow(data) : null;
}

/**
 * Détail d'un médicament par id (uuid).
 */
export async function getMedicamentById(id: string): Promise<Medicament | null> {
  const { data, error } = await supabase
    .from(TABLE)
    .select(
      "id, code, nom_commercial, groupe_therapeutique, prix_fcfa, source, created_at, updated_at"
    )
    .eq("id", id)
    .maybeSingle();

  if (error) throw error;
  return data ? mapRow(data) : null;
}

/**
 * Liste des valeurs distinctes de groupe_therapeutique (pour les filtres / dropdown).
 */
export async function getGroupesTherapeutiques(): Promise<string[]> {
  const { data, error } = await supabase
    .from(TABLE)
    .select("groupe_therapeutique")
    .not("groupe_therapeutique", "is", null)
    .order("groupe_therapeutique", { ascending: true });

  if (error) throw error;

  const seen = new Set<string>();
  const out: string[] = [];
  for (const row of data ?? []) {
    const g = (row as { groupe_therapeutique: string }).groupe_therapeutique?.trim();
    if (g && !seen.has(g)) {
      seen.add(g);
      out.push(g);
    }
  }
  return out;
}
