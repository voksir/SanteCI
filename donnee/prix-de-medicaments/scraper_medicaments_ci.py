"""
╔══════════════════════════════════════════════════════════════════════════════╗
║       SCRAPER - Prix des médicaments en Côte d'Ivoire                       ║
║       Source : pharmacies-de-garde.ci                                        ║
║       Auteur : Généré pour PharmaciesCI App                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

Structure scrapée :
  - N° | CODE | NOM COMMERCIAL | GROUPE THÉRAPEUTIQUE | PRIX (FCFA)

Dépendances :
  pip install requests beautifulsoup4 pandas lxml tqdm
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
import json
import re
import os
from datetime import datetime
from tqdm import tqdm

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
BASE_URL = "https://www.pharmacies-de-garde.ci/prix-des-medicaments-en-pharmacie-en-cote-divoire/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.google.com/",
    "DNT": "1",
}

# Délai entre requêtes (secondes) pour être respectueux du serveur
DELAY_BETWEEN_REQUESTS = 2

# Dossier de sortie
OUTPUT_DIR = "output_medicaments"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────
#  LOGGER
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"{OUTPUT_DIR}/scraper.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  SESSION HTTP ROBUSTE
# ─────────────────────────────────────────────
def create_session() -> requests.Session:
    """Crée une session HTTP avec retry automatique."""
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=2,                         # 2s, 4s, 8s, 16s, 32s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session


# ─────────────────────────────────────────────
#  NETTOYAGE DES DONNÉES
# ─────────────────────────────────────────────
def clean_price(raw: str) -> int | None:
    """Convertit '13 780' ou '1.065' en entier 13780."""
    if not raw:
        return None
    cleaned = re.sub(r"[^\d]", "", raw.strip())
    return int(cleaned) if cleaned else None


def clean_text(raw: str) -> str:
    """Supprime les espaces et caractères inutiles."""
    return " ".join(raw.strip().split()) if raw else ""


# ─────────────────────────────────────────────
#  PARSING D'UNE PAGE
# ─────────────────────────────────────────────
def parse_table(html: str) -> list[dict]:
    """
    Extrait les lignes du tableau de médicaments.
    Structure du tableau :
      N* | CODE | NOM COMMERCIAL | GROUPE THÉRAPEUTIQUE | PRIX
    """
    soup = BeautifulSoup(html, "lxml")
    records = []

    # Chercher le tableau principal
    table = soup.find("table")
    if not table:
        log.warning("Aucun tableau trouvé sur cette page.")
        return records

    rows = table.find_all("tr")
    log.info(f"  → {len(rows)} lignes trouvées dans le tableau.")

    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 5:
            continue

        # Ignorer l'en-tête
        if cells[0].get_text(strip=True).upper() in ("N*", "N°", "N", "#"):
            continue

        try:
            record = {
                "numero":             clean_text(cells[0].get_text()),
                "code":               clean_text(cells[1].get_text()),
                "nom_commercial":     clean_text(cells[2].get_text()),
                "groupe_therapeutique": clean_text(cells[3].get_text()),
                "prix_fcfa":          clean_price(cells[4].get_text()),
            }
            # Ignorer les lignes vides
            if record["nom_commercial"]:
                records.append(record)
        except Exception as e:
            log.debug(f"Ligne ignorée (erreur parsing): {e}")

    return records


# ─────────────────────────────────────────────
#  DÉTECTION DE LA PAGINATION
# ─────────────────────────────────────────────
def get_all_page_urls(session: requests.Session, base_url: str) -> list[str]:
    """
    Détecte s'il y a plusieurs pages et retourne toutes les URLs.
    Gère les paginations WordPress classiques (?page=2, /page/2/).
    """
    log.info("Détection de la pagination...")
    try:
        resp = session.get(base_url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Erreur lors de la requête initiale: {e}")
        return [base_url]

    soup = BeautifulSoup(resp.text, "lxml")

    # Recherche de liens de pagination
    page_urls = [base_url]
    pagination = soup.find("div", class_=re.compile(r"paginat|page-numbers|wp-pagenavi", re.I))
    if pagination:
        links = pagination.find_all("a", href=True)
        for link in links:
            href = link["href"]
            if href not in page_urls and base_url.split("/")[2] in href:
                page_urls.append(href)
        log.info(f"Pagination détectée : {len(page_urls)} page(s).")
    else:
        log.info("Pas de pagination détectée — page unique.")

    return page_urls


# ─────────────────────────────────────────────
#  SCRAPING PRINCIPAL
# ─────────────────────────────────────────────
def scrape(url: str = BASE_URL) -> list[dict]:
    """Lance le scraping complet et retourne tous les médicaments."""
    session = create_session()
    all_records = []

    pages = get_all_page_urls(session, url)

    for i, page_url in enumerate(tqdm(pages, desc="Pages scrapées"), start=1):
        log.info(f"[Page {i}/{len(pages)}] Chargement de : {page_url}")
        try:
            resp = session.get(page_url, timeout=30)
            resp.raise_for_status()
            records = parse_table(resp.text)
            all_records.extend(records)
            log.info(f"  → {len(records)} médicaments extraits (total: {len(all_records)})")
        except requests.HTTPError as e:
            log.error(f"  ✗ Erreur HTTP {resp.status_code}: {e}")
        except requests.RequestException as e:
            log.error(f"  ✗ Erreur réseau: {e}")

        if i < len(pages):
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # Dédoublonnage sur le code médicament
    before = len(all_records)
    seen_codes = set()
    deduped = []
    for rec in all_records:
        key = rec["code"] or rec["nom_commercial"]
        if key not in seen_codes:
            seen_codes.add(key)
            deduped.append(rec)
    log.info(f"Dédoublonnage : {before} → {len(deduped)} médicaments uniques.")

    return deduped


# ─────────────────────────────────────────────
#  EXPORT DES RÉSULTATS
# ─────────────────────────────────────────────
def save_results(records: list[dict]):
    """Sauvegarde les données en CSV, JSON et Excel."""
    if not records:
        log.warning("Aucune donnée à sauvegarder.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    df = pd.DataFrame(records)

    # ── CSV ──────────────────────────────────
    csv_path = f"{OUTPUT_DIR}/medicaments_{timestamp}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    log.info(f"✅ CSV sauvegardé : {csv_path}")

    # ── JSON ─────────────────────────────────
    json_path = f"{OUTPUT_DIR}/medicaments_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    log.info(f"✅ JSON sauvegardé : {json_path}")

    # ── Excel ────────────────────────────────
    try:
        xlsx_path = f"{OUTPUT_DIR}/medicaments_{timestamp}.xlsx"
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Médicaments", index=False)

            # Mise en forme basique
            ws = writer.sheets["Médicaments"]
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)

        log.info(f"✅ Excel sauvegardé : {xlsx_path}")
    except ImportError:
        log.warning("openpyxl non installé — export Excel ignoré.")

    # ── Résumé ────────────────────────────────
    log.info("─" * 50)
    log.info(f"📊 RÉSUMÉ")
    log.info(f"   Total médicaments  : {len(df)}")
    log.info(f"   Prix min (FCFA)    : {df['prix_fcfa'].min():,}")
    log.info(f"   Prix max (FCFA)    : {df['prix_fcfa'].max():,}")
    log.info(f"   Prix moyen (FCFA)  : {df['prix_fcfa'].mean():,.0f}")
    log.info(f"   Groupes uniques    : {df['groupe_therapeutique'].nunique()}")
    log.info("─" * 50)

    # Top 5 groupes thérapeutiques
    top_groupes = df["groupe_therapeutique"].value_counts().head(5)
    log.info("🏷️  Top 5 groupes thérapeutiques :")
    for groupe, count in top_groupes.items():
        log.info(f"   - {groupe}: {count} médicaments")


# ─────────────────────────────────────────────
#  RECHERCHE RAPIDE (utilitaire)
# ─────────────────────────────────────────────
def search_medicament(records: list[dict], query: str) -> list[dict]:
    """Recherche un médicament par nom ou groupe (insensible à la casse)."""
    q = query.lower()
    return [
        r for r in records
        if q in r.get("nom_commercial", "").lower()
        or q in r.get("groupe_therapeutique", "").lower()
        or q in r.get("code", "").lower()
    ]


# ─────────────────────────────────────────────
#  POINT D'ENTRÉE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  💊 SCRAPER MÉDICAMENTS - CÔTE D'IVOIRE")
    print("  Source : pharmacies-de-garde.ci")
    print(f"  Démarrage : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    # Lancer le scraping
    medicaments = scrape(BASE_URL)

    if medicaments:
        # Sauvegarder les résultats
        save_results(medicaments)

        # Exemple de recherche
        print("\n🔍 Exemple — Recherche 'antipaludique' :")
        resultats = search_medicament(medicaments, "antipaludique")
        for r in resultats[:5]:
            print(f"   {r['code']} | {r['nom_commercial']:<50} | {r['prix_fcfa']:,} FCFA")

        print(f"\n✅ Scraping terminé. {len(medicaments)} médicaments collectés.")
        print(f"📁 Fichiers sauvegardés dans : ./{OUTPUT_DIR}/")
    else:
        print("\n⚠️  Aucune donnée collectée. Vérifiez la connexion ou l'URL.")
