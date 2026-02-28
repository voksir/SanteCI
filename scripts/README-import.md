# Import des données Pharmacies de garde vers Supabase

Ce script remplit les tables `pharmacies` et `duty_periods` à partir des CSV générés par les scripts ETL dans `donnee/garde-abidjan/` et `donnee/garde-interieur/`.

## Prérequis

- Python 3.10+
- Compte Supabase avec les tables déjà créées (migration `create_pharmacies_and_duty_periods`)

## Installation des dépendances

```bash
pip install -r scripts/requirements-import.txt
```

## Variables d'environnement

À mettre dans **`.env.local`** à la racine du projet (fichier ignoré par git via `*.local`) :

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | URL du projet (ex. `https://xxxxx.supabase.co`) |
| `SUPABASE_SERVICE_ROLE_KEY` | Clé **service_role** (recommandée pour l'import) ou `SUPABASE_ANON_KEY` |

Exemple de contenu pour `.env.local` :

```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

Le script charge automatiquement `.env.local` puis `.env` avant de lancer l'import. Tu peux aussi définir les variables en PowerShell/bash si tu préfères ne pas utiliser de fichier.

## Usage

- **Import par défaut** (fichiers février 2026 dans `donnee/`) :

  ```bash
  python scripts/import_garde_to_supabase.py
  ```

- **Vérifier les chemins sans importer** :

  ```bash
  python scripts/import_garde_to_supabase.py --dry-run
  ```

- **Autre mois** (ex. mars 2026) :

  ```bash
  python scripts/import_garde_to_supabase.py \
    --abidjan-pharmacies donnee/garde-abidjan/unppci_pharmacies_mars_2026.csv \
    --abidjan-periods donnee/garde-abidjan/unppci_duty_periods_mars_2026.csv \
    --interieur-pharmacies donnee/garde-interieur/unppci_interieur_pharmacies_mars_2026.csv \
    --interieur-periods donnee/garde-interieur/unppci_interieur_duty_periods_mars_2026.csv
  ```

## Comportement

1. **Pharmacies** : upsert sur `pharmacy_key` (pas de doublon, mise à jour si déjà présentes).
2. **Périodes de garde** : insert des lignes. En relançant le script avec les mêmes CSV, tu auras des doublons dans `duty_periods`. Pour repartir propre sur un mois, supprime en SQL les lignes concernées puis relance l'import.

## Où trouver les clés Supabase

Dans le tableau de bord Supabase : **Project Settings** → **API** → **Project URL** et **service_role** (secret).
