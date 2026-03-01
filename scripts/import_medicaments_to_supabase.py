#!/usr/bin/env python3
"""
Import des médicaments (CSV/JSON) vers Supabase.

Lit les fichiers dans donnee/prix-de-medicaments/output_medicaments/
(dernier fichier par défaut) et remplit la table public.medicaments.
Upsert sur la clé `code`.

Usage:
  export SUPABASE_URL="https://xxx.supabase.co"
  export SUPABASE_SERVICE_ROLE_KEY="eyJ..."
  python scripts/import_medicaments_to_supabase.py

  # Fichier spécifique
  python scripts/import_medicaments_to_supabase.py --input donnee/prix-de-medicaments/output_medicaments/medicaments_20260227_225618.json

  # Simulation sans écriture
  python scripts/import_medicaments_to_supabase.py --dry-run

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
load_dotenv(PROJECT_ROOT / ".env.local")
load_dotenv(PROJECT_ROOT / ".env")

DONNEE_PRIX = PROJECT_ROOT / "donnee" / "prix-de-medicaments" / "output_medicaments"
DEFAULT_SOURCE = "pharmacies-de-garde.ci"

# Taille des lots pour l'upsert (éviter les requêtes trop grosses)
BATCH_SIZE = 500


def load_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        print(
            "Erreur: définir SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY (ou SUPABASE_ANON_KEY)",
            file=sys.stderr,
        )
        sys.exit(1)
    return create_client(url, key)


def find_latest_data_file(directory: Path) -> Path | None:
    """Retourne le fichier medicaments_*.csv ou medicaments_*.json le plus récent."""
    candidates: list[Path] = []
    for ext in ("*.csv", "*.json"):
        candidates.extend(directory.glob(ext))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_records(path: Path) -> list[dict]:
    """Charge les enregistrements depuis un CSV ou un JSON."""
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")

    if path.suffix.lower() == ".json":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Le JSON doit être un tableau d'objets.")
        return data

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        return df.to_dict(orient="records")

    raise ValueError(f"Format non supporté: {path.suffix}. Utiliser .csv ou .json.")


def normalize_record(raw: dict) -> dict | None:
    """
    Normalise un enregistrement pour l'insertion.
    Retourne None si la ligne est invalide (code ou nom manquant, prix invalide).
    """
    code = raw.get("code")
    if code is None or (isinstance(code, float) and pd.isna(code)):
        return None
    code = str(code).strip()
    if not code:
        return None

    nom = raw.get("nom_commercial")
    if nom is None or (isinstance(nom, float) and pd.isna(nom)):
        return None
    nom = " ".join(str(nom).strip().split())

    groupe = raw.get("groupe_therapeutique")
    if groupe is None or (isinstance(groupe, float) and pd.isna(groupe)):
        groupe = None
    else:
        groupe = " ".join(str(groupe).strip().split()) or None

    prix = raw.get("prix_fcfa")
    if prix is None:
        return None
    try:
        prix = int(float(prix))
    except (TypeError, ValueError):
        return None
    if prix < 0:
        return None

    return {
        "code": code,
        "nom_commercial": nom,
        "groupe_therapeutique": groupe,
        "prix_fcfa": prix,
        "source": DEFAULT_SOURCE,
    }


def import_medicaments(
    supabase: Client | None, records: list[dict], dry_run: bool = False
) -> tuple[int, int]:
    """
    Upsert les enregistrements dans public.medicaments.
    Retourne (nombre traités, nombre ignorés/invalides).
    """
    rows: list[dict] = []
    skipped = 0
    for raw in records:
        row = normalize_record(raw)
        if row is None:
            skipped += 1
            continue
        rows.append(row)

    if dry_run:
        print(f"Dry-run: {len(rows)} lignes à upsert, {skipped} ignorées.")
        if rows:
            print("Exemple:", rows[0])
        return len(rows), skipped

    if not rows:
        return 0, skipped

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        supabase.table("medicaments").upsert(batch, on_conflict="code").execute()

    return len(rows), skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import médicaments (CSV/JSON) → Supabase table medicaments"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=None,
        help="Fichier CSV ou JSON à importer. Par défaut: dernier fichier dans donnee/prix-de-medicaments/output_medicaments/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Afficher le nombre de lignes sans écrire en base.",
    )
    args = parser.parse_args()

    if args.input is not None:
        data_path = (PROJECT_ROOT / args.input).resolve() if not args.input.is_absolute() else args.input
    else:
        if not DONNEE_PRIX.is_dir():
            print(f"Erreur: dossier introuvable: {DONNEE_PRIX}", file=sys.stderr)
            sys.exit(1)
        data_path = find_latest_data_file(DONNEE_PRIX)
        if data_path is None:
            print(
                f"Erreur: aucun fichier medicaments_*.csv ou *.json dans {DONNEE_PRIX}",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Fichier utilisé: {data_path}")

    try:
        records = load_records(data_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Erreur: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Enregistrements lus: {len(records)}")

    if args.dry_run:
        import_medicaments(None, records, dry_run=True)
        return

    supabase = load_supabase()
    inserted, skipped = import_medicaments(supabase, records, dry_run=False)
    print(f"Upsert: {inserted} médicaments, {skipped} lignes ignorées.")
    print("Terminé.")


if __name__ == "__main__":
    main()
