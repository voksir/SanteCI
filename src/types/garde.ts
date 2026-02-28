/**
 * Types alignés sur les tables Supabase pharmacies et duty_periods.
 */

export type ZoneType = "abidjan" | "interieur";

export interface Pharmacie {
  id: string;
  pharmacy_key: string;
  name: string;
  zone_type: ZoneType;
  section: string | null;
  area: string | null;
  city: string | null;
  address: string | null;
  phones: string[] | null;
  source: string | null;
  created_at?: string;
}

export interface DutyPeriod {
  id: string;
  pharmacy_id: string | null;
  pharmacy_key: string;
  zone_type: ZoneType;
  section: string | null;
  area: string | null;
  city: string | null;
  start_date: string;
  end_date: string;
  duty_type: string | null;
  source: string | null;
  timezone: string | null;
  created_at?: string;
}

/** Une période de garde avec les infos pharmacie jointes (pour liste et fiche). */
export interface PharmacieDeGarde {
  id: string;
  pharmacy_key: string;
  pharmacy_id: string | null;
  name: string;
  zone_type: ZoneType;
  section: string | null;
  area: string | null;
  city: string | null;
  address: string | null;
  phones: string[] | null;
  start_date: string;
  end_date: string;
  duty_type: string | null;
  source: string | null;
}

export interface GardeAbidjanOptions {
  startDate?: string;
  endDate?: string;
  section?: string | null;
}

export interface GardeInterieurOptions {
  startDate?: string;
  endDate?: string;
  city?: string | null;
}
