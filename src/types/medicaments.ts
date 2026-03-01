/**
 * Types alignés sur la table Supabase medicaments (prix des médicaments).
 */

export interface Medicament {
  id: string;
  code: string;
  nom_commercial: string;
  groupe_therapeutique: string | null;
  prix_fcfa: number;
  source: string | null;
  created_at: string;
  updated_at: string;
}

/** Options pour la liste paginée et filtrée. */
export interface MedicamentsListOptions {
  groupe_therapeutique?: string | null;
  prix_min?: number | null;
  prix_max?: number | null;
  sortBy?: "nom" | "groupe" | "prix";
  sortOrder?: "asc" | "desc";
  limit?: number;
  offset?: number;
}

/** Options pour la recherche texte (searchMedicaments). */
export interface MedicamentsSearchOptions extends MedicamentsListOptions {
  searchInGroupe?: boolean;
}
