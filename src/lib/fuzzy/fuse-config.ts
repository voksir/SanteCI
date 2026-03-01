import type { FuseOptionKey } from "fuse.js";
import type { PharmacieDeGarde } from "@/types/garde";
import type { Medicament } from "@/types/medicaments";

/** Clés de recherche pour les pharmacies de garde (liste GardeList). */
export const pharmacySearchKeys: Array<FuseOptionKey<PharmacieDeGarde>> = [
  { name: "name", weight: 0.4 },
  { name: "section", weight: 0.2 },
  { name: "area", weight: 0.15 },
  { name: "city", weight: 0.15 },
  { name: "address", weight: 0.1 },
];

/** Clés de recherche pour les médicaments (réutilisable pour PrixList plus tard). */
export const medicamentSearchKeys: Array<FuseOptionKey<Medicament>> = [
  { name: "nom_commercial", weight: 0.5 },
  { name: "groupe_therapeutique", weight: 0.35 },
  { name: "code", weight: 0.15 },
];

export const BASE_FUSE_OPTIONS = {
  includeScore: true,
  includeMatches: true,
  ignoreDiacritics: true,
  ignoreLocation: true,
  minMatchCharLength: 2,
  shouldSort: true,
} as const;

/** Seuils par domaine : plus bas = plus strict. */
export const THRESHOLDS = {
  pharmacy: 0.35,
  medication: 0.3,
} as const;
