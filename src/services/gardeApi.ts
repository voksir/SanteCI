import { supabase } from "@/lib/supabase";
import type {
  GardeAbidjanOptions,
  GardeInterieurOptions,
  Pharmacie,
  PharmacieDeGarde,
} from "@/types/garde";

type DutyPeriodRow = {
  id: string;
  pharmacy_id: string | null;
  pharmacy_key: string;
  zone_type: "abidjan" | "interieur";
  section: string | null;
  area: string | null;
  city: string | null;
  start_date: string;
  end_date: string;
  duty_type: string | null;
  source: string | null;
  timezone: string | null;
  pharmacies: Pharmacie | null;
};

function rowToPharmacieDeGarde(row: DutyPeriodRow): PharmacieDeGarde {
  const p = row.pharmacies;
  return {
    id: row.id,
    pharmacy_key: row.pharmacy_key,
    pharmacy_id: row.pharmacy_id,
    name: p?.name ?? row.pharmacy_key,
    zone_type: row.zone_type,
    section: row.section ?? p?.section ?? null,
    area: row.area ?? p?.area ?? null,
    city: row.city ?? p?.city ?? null,
    address: p?.address ?? null,
    phones: p?.phones ?? null,
    start_date: row.start_date,
    end_date: row.end_date,
    duty_type: row.duty_type,
    source: row.source,
  };
}

/**
 * Pharmacies de garde pour la zone Abidjan.
 * Filtre par période (chevauchement avec [startDate, endDate]) et optionnellement par section.
 */
export async function getGardeAbidjan(
  options: GardeAbidjanOptions = {}
): Promise<PharmacieDeGarde[]> {
  const { startDate, endDate, section } = options;

  let query = supabase
    .from("duty_periods")
    .select("*, pharmacies(*)")
    .eq("zone_type", "abidjan");

  if (startDate) {
    query = query.gte("end_date", startDate);
  }
  if (endDate) {
    query = query.lte("start_date", endDate);
  }
  if (section) {
    query = query.eq("section", section);
  }

  const { data, error } = await query.order("start_date", { ascending: true });

  if (error) throw error;
  return (data as DutyPeriodRow[]).map(rowToPharmacieDeGarde);
}

/**
 * Pharmacies de garde pour la zone Intérieur.
 * Filtre par période et optionnellement par ville.
 */
export async function getGardeInterieur(
  options: GardeInterieurOptions = {}
): Promise<PharmacieDeGarde[]> {
  const { startDate, endDate, city } = options;

  let query = supabase
    .from("duty_periods")
    .select("*, pharmacies(*)")
    .eq("zone_type", "interieur");

  if (startDate) {
    query = query.gte("end_date", startDate);
  }
  if (endDate) {
    query = query.lte("start_date", endDate);
  }
  if (city) {
    query = query.eq("city", city);
  }

  const { data, error } = await query.order("start_date", { ascending: true });

  if (error) throw error;
  return (data as DutyPeriodRow[]).map(rowToPharmacieDeGarde);
}

/**
 * Liste des sections (Abidjan) pour le filtre.
 */
export async function getSectionsAbidjan(): Promise<string[]> {
  const { data, error } = await supabase
    .from("duty_periods")
    .select("section")
    .eq("zone_type", "abidjan")
    .not("section", "is", null);

  if (error) throw error;

  const sections = [...new Set((data ?? []).map((r) => r.section as string))];
  return sections.sort((a, b) => a.localeCompare(b));
}

/**
 * Liste des villes (Intérieur) pour le filtre.
 */
export async function getVillesInterieur(): Promise<string[]> {
  const { data, error } = await supabase
    .from("duty_periods")
    .select("city")
    .eq("zone_type", "interieur")
    .not("city", "is", null);

  if (error) throw error;

  const cities = [...new Set((data ?? []).map((r) => r.city as string))];
  return cities.sort((a, b) => a.localeCompare(b));
}

/**
 * Fiche pharmacie par id (pour l'écran détail).
 */
export async function getPharmacieById(id: string): Promise<Pharmacie | null> {
  const { data, error } = await supabase
    .from("pharmacies")
    .select("*")
    .eq("id", id)
    .maybeSingle();

  if (error) throw error;
  return data as Pharmacie | null;
}

/**
 * Périodes de garde pour une pharmacie (optionnel, pour la fiche détail).
 */
export async function getDutyPeriodsByPharmacieId(
  pharmacyId: string
): Promise<PharmacieDeGarde[]> {
  const { data, error } = await supabase
    .from("duty_periods")
    .select("*, pharmacies(*)")
    .eq("pharmacy_id", pharmacyId)
    .gte("end_date", new Date().toISOString().slice(0, 10))
    .order("start_date", { ascending: true });

  if (error) throw error;
  return (data as DutyPeriodRow[]).map(rowToPharmacieDeGarde);
}
