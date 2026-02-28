#!/usr/bin/env python3
"""
Import des CSV UNPPCI (Pharmacies de garde) vers Supabase.

Lit les fichiers dans donnee/garde-abidjan/ et donnee/garde-interieur/
et remplit les tables public.pharmacies et public.duty_periods.

Usage:
  export SUPABASE_URL="https://xxx.supabase.co"
  export SUPABASE_SERVICE_ROLE_KEY="eyJ..."
  python scripts/import_garde_to_supabase.py

  # Avec chemins personnalisés (ex. autre mois)
  python scripts/import_garde_to_supabase.py \
    --abidjan-pharmacies donnee/garde-abidjan/unppci_pharmacies_mars_2026.csv \
    --abidjan-periods   donnee/garde-abidjan/unppci_duty_periods_mars_2026.csv \
    --interieur-pharmacies donnee/garde-interieur/unppci_interieur_pharmacies_mars_2026.csv \
    --interieur-periods    donnee/garde-interieur/unppci_interieur_duty_periods_mars_2026.csv

Dépendances: pip install -r scripts/requirements-import.txt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Charge .env.local (ou .env) à la racine du projet
load_dotenv(PROJECT_ROOT / ".env.local")
load_dotenv(PROJECT_ROOT / ".env")
DONNEE = PROJECT_ROOT / "donnee"
ABIDJAN_PHARMACIES = DONNEE / "garde-abidjan" / "unppci_pharmacies_fevrier_2026.csv"
ABIDJAN_PERIODS = DONNEE / "garde-abidjan" / "unppci_duty_periods_fevrier_2026.csv"
INTERIEUR_PHARMACIES = DONNEE / "garde-interieur" / "unppci_interieur_pharmacies_fevrier_2026.csv"
INTERIEUR_PERIODS = DONNEE / "garde-interieur" / "unppci_interieur_duty_periods_fevrier_2026.csv"


def parse_phones_json(raw: str) -> list[str] | None:
    """Parse la colonne phones_json (ex: '[""07 78 68 11 74""]') en liste Python."""
    if not raw or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(s.replace('""', '"'))
    except json.JSONDecodeError:
        return None


def load_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        print("Erreur: définir SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY (ou SUPABASE_ANON_KEY)", file=sys.stderr)
        sys.exit(1)
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Abidjan
# ---------------------------------------------------------------------------

def import_abidjan_pharmacies(supabase: Client, path: Path) -> dict[str, str]:
    """Importe les pharmacies Abidjan. Retourne un map pharmacy_key -> id (uuid)."""
    df = pd.read_csv(path)
    key_to_id: dict[str, str] = {}
    rows = []
    for _, r in df.iterrows():
        phones = parse_phones_json(r.get("phones_json"))
        rows.append({
            "pharmacy_key": str(r["pharmacy_key"]).strip(),
            "name": str(r["pharmacy_name"]).strip() if pd.notna(r.get("pharmacy_name")) else "",
            "zone_type": "abidjan",
            "section": str(r["section"]).strip() if pd.notna(r.get("section")) else None,
            "area": str(r["area"]).strip() if pd.notna(r.get("area")) else None,
            "city": None,
            "address": str(r["address"]).strip() if pd.notna(r.get("address")) else None,
            "phones": phones,
            "source": "UNPPCI",
        })
    # Upsert par pharmacy_key
    supabase.table("pharmacies").upsert(rows, on_conflict="pharmacy_key").execute()
    # Récupérer les id pour lier duty_periods
    all_ph = supabase.table("pharmacies").select("id, pharmacy_key").eq("zone_type", "abidjan").execute()
    for row in (all_ph.data or []):
        key_to_id[row["pharmacy_key"]] = row["id"]
    return key_to_id


def import_abidjan_duty_periods(supabase: Client, path: Path, pharmacy_key_to_id: dict[str, str]) -> int:
    """Importe les périodes de garde Abidjan. Retourne le nombre d'insertions."""
    df = pd.read_csv(path)
    rows = []
    for _, r in df.iterrows():
        pk = str(r["pharmacy_key"]).strip()
        rows.append({
            "pharmacy_id": pharmacy_key_to_id.get(pk),
            "pharmacy_key": pk,
            "zone_type": "abidjan",
            "section": str(r["section"]).strip() if pd.notna(r.get("section")) else None,
            "area": str(r["area"]).strip() if pd.notna(r.get("area")) else None,
            "city": None,
            "start_date": str(r["start_date"]),
            "end_date": str(r["end_date"]),
            "duty_type": str(r["duty_type"]).strip() if pd.notna(r.get("duty_type")) else None,
            "source": str(r["source"]).strip() if pd.notna(r.get("source")) else None,
            "timezone": str(r["timezone"]).strip() if pd.notna(r.get("timezone")) else None,
        })
    if not rows:
        return 0
    supabase.table("duty_periods").insert(rows).execute()
    return len(rows)


# ---------------------------------------------------------------------------
# Intérieur
# ---------------------------------------------------------------------------

def import_interieur_pharmacies(supabase: Client, path: Path) -> dict[str, str]:
    """Importe les pharmacies Intérieur. Retourne un map pharmacy_key -> id."""
    df = pd.read_csv(path)
    rows = []
    for _, r in df.iterrows():
        phones = parse_phones_json(r.get("phones_json"))
        rows.append({
            "pharmacy_key": str(r["pharmacy_key"]).strip(),
            "name": str(r["pharmacy_name"]).strip() if pd.notna(r.get("pharmacy_name")) else "",
            "zone_type": "interieur",
            "section": None,
            "area": None,
            "city": str(r["city"]).strip() if pd.notna(r.get("city")) else None,
            "address": str(r["address"]).strip() if pd.notna(r.get("address")) else None,
            "phones": phones,
            "source": "UNPPCI",
        })
    supabase.table("pharmacies").upsert(rows, on_conflict="pharmacy_key").execute()
    key_to_id: dict[str, str] = {}
    all_ph = supabase.table("pharmacies").select("id, pharmacy_key").eq("zone_type", "interieur").execute()
    for row in (all_ph.data or []):
        key_to_id[row["pharmacy_key"]] = row["id"]
    return key_to_id


def import_interieur_duty_periods(supabase: Client, path: Path, pharmacy_key_to_id: dict[str, str]) -> int:
    """Importe les périodes de garde Intérieur. Retourne le nombre d'insertions."""
    df = pd.read_csv(path)
    rows = []
    for _, r in df.iterrows():
        pk = str(r["pharmacy_key"]).strip()
        rows.append({
            "pharmacy_id": pharmacy_key_to_id.get(pk),
            "pharmacy_key": pk,
            "zone_type": "interieur",
            "section": None,
            "area": None,
            "city": str(r["city"]).strip() if pd.notna(r.get("city")) else None,
            "start_date": str(r["start_date"]),
            "end_date": str(r["end_date"]),
            "duty_type": str(r["duty_type"]).strip() if pd.notna(r.get("duty_type")) else None,
            "source": str(r["source"]).strip() if pd.notna(r.get("source")) else None,
            "timezone": str(r["timezone"]).strip() if pd.notna(r.get("timezone")) else None,
        })
    if not rows:
        return 0
    supabase.table("duty_periods").insert(rows).execute()
    return len(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Import CSV UNPPCI → Supabase")
    parser.add_argument("--abidjan-pharmacies", type=Path, default=ABIDJAN_PHARMACIES)
    parser.add_argument("--abidjan-periods", type=Path, default=ABIDJAN_PERIODS)
    parser.add_argument("--interieur-pharmacies", type=Path, default=INTERIEUR_PHARMACIES)
    parser.add_argument("--interieur-periods", type=Path, default=INTERIEUR_PERIODS)
    parser.add_argument("--dry-run", action="store_true", help="Afficher les chemins sans appeler Supabase")
    args = parser.parse_args()

    for p in (args.abidjan_pharmacies, args.abidjan_periods, args.interieur_pharmacies, args.interieur_periods):
        if not p.exists():
            print(f"Fichier introuvable: {p}", file=sys.stderr)
            sys.exit(1)

    if args.dry_run:
        print("Dry-run. Fichiers qui seraient utilisés:")
        print("  Abidjan pharmacies:", args.abidjan_pharmacies)
        print("  Abidjan periods:   ", args.abidjan_periods)
        print("  Intérieur pharmacies:", args.interieur_pharmacies)
        print("  Intérieur periods:   ", args.interieur_periods)
        return

    supabase = load_supabase()

    print("Import Abidjan pharmacies...")
    abidjan_ids = import_abidjan_pharmacies(supabase, args.abidjan_pharmacies)
    print(f"  {len(abidjan_ids)} pharmacies (upsert)")

    print("Import Abidjan duty_periods...")
    n_ab = import_abidjan_duty_periods(supabase, args.abidjan_periods, abidjan_ids)
    print(f"  {n_ab} périodes insérées")

    print("Import Intérieur pharmacies...")
    interieur_ids = import_interieur_pharmacies(supabase, args.interieur_pharmacies)
    print(f"  {len(interieur_ids)} pharmacies (upsert)")

    print("Import Intérieur duty_periods...")
    n_int = import_interieur_duty_periods(supabase, args.interieur_periods, interieur_ids)
    print(f"  {n_int} périodes insérées")

    print("Terminé.")


if __name__ == "__main__":
    main()
