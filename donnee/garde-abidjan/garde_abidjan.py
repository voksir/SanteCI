#!/usr/bin/env python3
"""
garde_abidjan.py
================
Parseur / ETL réutilisable pour les PDFs mensuels de tour de garde des pharmacies
de la zone Abidjan publiés par l'UNPPCI.

Fichiers de sortie produits
---------------------------
  - unppci_pharmacies_<mois>_<année>.csv
  - unppci_duty_periods_<mois>_<année>.csv
  - unppci_seed_<mois>_<année>.json

Usage
-----
  python garde_abidjan.py --pdf garde-fevrier-2026.pdf --output-dir ./output

  # Avec un référentiel mensuel précédent pour réutiliser les pharmacy_key :
  python garde_abidjan.py \
      --pdf garde-mars-2026.pdf \
      --output-dir ./output \
      --reference unppci_pharmacies_fevrier_2026.csv

Dépendances
-----------
  pip install pdfplumber pandas
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

import pdfplumber
import pandas as pd


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

MONTHS_FR = {
    "JANVIER":  (1,  "janvier"),
    "FEVRIER":  (2,  "fevrier"),
    "FÉVRIER":  (2,  "fevrier"),
    "MARS":     (3,  "mars"),
    "AVRIL":    (4,  "avril"),
    "MAI":      (5,  "mai"),
    "JUIN":     (6,  "juin"),
    "JUILLET":  (7,  "juillet"),
    "AOUT":     (8,  "aout"),
    "AOÛT":     (8,  "aout"),
    "SEPTEMBRE":(9,  "septembre"),
    "OCTOBRE":  (10, "octobre"),
    "NOVEMBRE": (11, "novembre"),
    "DECEMBRE": (12, "decembre"),
    "DÉCEMBRE": (12, "decembre"),
}

# Zones/quartiers reconnus explicitement dans le PDF Abidjan
# (apparaissent en en-tête de sous-section, sur une ligne seule)
KNOWN_AREAS = {
    # Section d'Abobo
    "ABOBO", "ABOBO PK 18", "ANYAMA", "ALEPE / MONTEZO / BROFODOUME",
    "ALEPE", "MONTEZO", "BROFODOUME",
    # Section d'Adjamé
    "ADJAME CENTRE", "ATTECOUBE", "WILLIAMSVILLE",
    # Section de Cocody
    "BINGERVILLE",
    "ZONE AKOUEDO - PALMERAIE EXTENSION - ABATTA",
    "ZONE AKOUEDO - PALMERAIE EXTENSION - ABATTA",
    "RIVIERA", "COCODY", "II PLATEAUX",
    # Section de Marcory
    "MARCORY NORD", "MARCORY SUD", "ANOUMABO",
    # Section de Port-Bouet
    "CENTRE", "VRIDI", "ADJOUFFOU /GONZAQ/ ANANI",
    "ADJOUFFOU", "GONZAQ", "ANANI",
    # Section de Yopougon
    "ABOBODOUME/ LOCODJORO", "ABOBODOUME/LOCODJORO", "ALLOKOI PK 23",
    "ABOBODOUME", "LOCODJORO", "YOPOUGON",
}


# Mapping zone → section implicite (pour les pages sans en-tête "SECTION DE...")
AREA_TO_SECTION = {
    "ABOBO":                         "SECTION D'ABOBO",
    "ABOBO PK 18":                   "SECTION D'ABOBO",
    "ANYAMA":                        "SECTION D'ABOBO",
    "ALEPE / MONTEZO / BROFODOUME":  "SECTION D'ABOBO",
    "ALEPE":                         "SECTION D'ABOBO",
    "MONTEZO":                       "SECTION D'ABOBO",
    "BROFODOUME":                    "SECTION D'ABOBO",
    "ADJAME CENTRE":                 "SECTION D'ADJAME",
    "ATTECOUBE":                     "SECTION D'ADJAME",
    "WILLIAMSVILLE":                 "SECTION D'ADJAME",
    "BINGERVILLE":                   "SECTION DE COCODY",
    "RIVIERA":                       "SECTION DE COCODY",
    "COCODY":                        "SECTION DE COCODY",
    "II PLATEAUX":                   "SECTION DE COCODY",
    "MARCORY NORD":                  "SECTION DE MARCORY",
    "MARCORY SUD":                   "SECTION DE MARCORY",
    "ANOUMABO":                      "SECTION DE MARCORY",
    "CENTRE":                        "SECTION DE PORT BOUET",
    "VRIDI":                         "SECTION DE PORT BOUET",
    "ADJOUFFOU /GONZAQ/ ANANI":      "SECTION DE PORT BOUET",
    "ADJOUFFOU":                     "SECTION DE PORT BOUET",
    "ABOBODOUME/ LOCODJORO":         "SECTION DE YOPOUGON",
    "ABOBODOUME/LOCODJORO":          "SECTION DE YOPOUGON",
    "ABOBODOUME":                    "SECTION DE YOPOUGON",
    "LOCODJORO":                     "SECTION DE YOPOUGON",
    "ALLOKOI PK 23":                 "SECTION DE YOPOUGON",
    "YOPOUGON":                      "SECTION DE YOPOUGON",
}


# ---------------------------------------------------------------------------
# Structures de données
# ---------------------------------------------------------------------------

@dataclass
class RawEntry:
    """Entrée brute extraite du PDF avant normalisation."""
    section: str
    area: str
    start_date: str
    end_date: str
    raw_lines: List[str] = field(default_factory=list)

    def full_text(self) -> str:
        return clean_space(" ".join(self.raw_lines))


# ---------------------------------------------------------------------------
# Utilitaires texte
# ---------------------------------------------------------------------------

def ascii_upper(value: object) -> str:
    """Convertit en majuscules ASCII sans accents."""
    text = str(value or "")
    text = (
        text.replace("'", "'").replace("'", "'")
        .replace("–", "-").replace("—", "-")
        .replace("œ", "oe").replace("Œ", "OE")
        .replace("ß", "ss")
    )
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text.upper()


def clean_space(value: object) -> str:
    """Normalise les espaces et caractères spéciaux courants."""
    text = str(value or "")
    text = (
        text.replace("\xa0", " ").replace("\u2019", "'").replace("'", "'")
        .replace("–", "-").replace("—", "-")
        .replace("\u201c", '"').replace("\u201d", '"')
        .replace("Ï", "I").replace("Â", "A").replace("Ê", "E")
    )
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*/\s*", " / ", text)
    text = re.sub(r"\s*-\s*", " - ", text)
    text = re.sub(r"\s+", " ", text).strip(" /-.,")
    return text


def normalize_for_match(value: object) -> str:
    """Version agressive pour comparaisons/matching : pas d'accents, que lettres+chiffres."""
    text = ascii_upper(value)
    text = re.sub(r"\b(PHCIE|PHARMACIE|PHC)\b", " ", text)
    text = re.sub(r"\b(NOUVELLE|NVLLE|NLLE)\b", "NOUVELLE", text)
    text = re.sub(r"\bSAINTE\b", "STE", text)
    text = re.sub(r"\bSAINT\b", "ST", text)
    text = re.sub(r"\bD[' ]", "D ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_name_display(name: str) -> str:
    """Nettoie et met en majuscules le nom d'affichage d'une pharmacie."""
    text = clean_space(name)
    text = re.sub(r"^\s*(PHCIE|PHARMACIE)\s+", "", text, flags=re.I)
    text = text.strip(" /-.,")
    return re.sub(r"\s+", " ", text).upper()


# ---------------------------------------------------------------------------
# Extraction téléphones & adresse
# ---------------------------------------------------------------------------

def extract_phones(text: str) -> List[str]:
    """Extrait tous les numéros de téléphone ivoiriens (format 2+2+2+2 ou 2+2+2+2+2)."""
    clean = clean_space(text)
    phones: List[str] = []
    for m in re.finditer(r"(?<!\d)(\d{2}(?:[\s.]\d{2}){3,4})(?!\d)", clean):
        phone = re.sub(r"[\s.]+", " ", m.group(1)).strip()
        if phone not in phones:
            phones.append(phone)
    return phones


def strip_phones_from_text(text: str) -> str:
    """Supprime les numéros de téléphone et le mot TEL. d'un texte."""
    out = clean_space(text)
    out = re.sub(r"\bTEL\.?\s*:?\s*", " ", out, flags=re.I)
    out = re.sub(r"(?<!\d)\d{2}(?:[\s.]\d{2}){3,4}(?!\d)", " ", out)
    out = re.sub(r"[;]+", " / ", out)
    out = re.sub(r"\s+/\s+", " / ", out)
    out = re.sub(r"\s+", " ", out)
    out = clean_space(out)
    out = re.sub(r"^(?:[/\-.,:]|\s)+", "", out)
    out = re.sub(r"(?:[/\-.,:]|\s)+$", "", out)
    return clean_space(out)


# ---------------------------------------------------------------------------
# Parsing des dates de semaine
# ---------------------------------------------------------------------------

def parse_week_header(line: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrait (start_date ISO, end_date ISO) d'une ligne de type :
      'SEMAINE DU SAMEDI 07 AU VENDREDI 13 FEVRIER 2026'
      'SEMAINE DU SAMEDI 28 FEVRIER AU VENDREDI 06 MARS 2026'
    Retourne (None, None) si non trouvé.
    """
    upper = ascii_upper(line)

    # Cas 1 : même mois — SAMEDI DD AU VENDREDI DD MOIS YYYY
    m = re.search(
        r"SEMAINE DU SAMEDI\s+(\d{1,2})\s+AU\s+VENDREDI\s+(\d{1,2})\s+"
        r"([A-ZÉÈÊÛÎÔÄËÏÖÜÀÙÇ]+)\s+(\d{4})",
        upper,
    )
    if m:
        s_day, e_day = int(m.group(1)), int(m.group(2))
        e_month_key = ascii_upper(m.group(3))
        year = int(m.group(4))
        if e_month_key in MONTHS_FR:
            e_month = MONTHS_FR[e_month_key][0]
            s_month = e_month if s_day <= e_day else (12 if e_month == 1 else e_month - 1)
            s_year = year if s_month <= e_month else year - 1
            try:
                return (
                    dt.date(s_year, s_month, s_day).isoformat(),
                    dt.date(year, e_month, e_day).isoformat(),
                )
            except ValueError:
                pass

    # Cas 2 : mois différents — SAMEDI DD MOIS AU VENDREDI DD MOIS YYYY
    m = re.search(
        r"SEMAINE DU SAMEDI\s+(\d{1,2})\s+([A-ZÉÈÊÛÎÔÄËÏÖÜÀÙÇ]+)\s+AU\s+VENDREDI\s+"
        r"(\d{1,2})\s+([A-ZÉÈÊÛÎÔÄËÏÖÜÀÙÇ]+)\s+(\d{4})",
        upper,
    )
    if m:
        s_day = int(m.group(1))
        s_month_key = ascii_upper(m.group(2))
        e_day = int(m.group(3))
        e_month_key = ascii_upper(m.group(4))
        year = int(m.group(5))
        if s_month_key in MONTHS_FR and e_month_key in MONTHS_FR:
            s_month = MONTHS_FR[s_month_key][0]
            e_month = MONTHS_FR[e_month_key][0]
            s_year = year if s_month <= e_month else year - 1
            try:
                return (
                    dt.date(s_year, s_month, s_day).isoformat(),
                    dt.date(year, e_month, e_day).isoformat(),
                )
            except ValueError:
                pass

    return None, None


def infer_month_year_from_header(text: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Extrait le mois et l'année du titre 'TOUR DE GARDE DU MOIS DE FEVRIER 2026'.
    Retourne (slug_mois, année) ou (None, None).
    """
    upper = ascii_upper(text)
    m = re.search(
        r"TOUR DE GARDE DU MOIS DE\s+([A-ZÉÈÊÛÎÔÄËÏÖÜÀÙÇ]+)\s+(\d{4})",
        upper,
    )
    if m:
        month_key = ascii_upper(m.group(1))
        year = int(m.group(2))
        if month_key in MONTHS_FR:
            return MONTHS_FR[month_key][1], year
    return None, None


# ---------------------------------------------------------------------------
# Détection de structure dans le PDF
# ---------------------------------------------------------------------------

def is_section_header(line: str) -> bool:
    """
    Vrai si la ligne est un en-tête de section (SECTION DE ..., SECTION D'...).
    Gère les apostrophes courbes (U+2019) et droites.
    """
    # Normalise les apostrophes avant upper conversion
    cleaned = line.replace("’", "'").replace("‘", "'").strip()
    upper = ascii_upper(cleaned).strip()
    return bool(re.match(r"^SECTION\s+(DE\b|D[' ]|DU\b)", upper))


def is_area_header(line: str) -> bool:
    """
    Vrai si la ligne est un sous-en-tête de zone/quartier.
    Priorité : correspondance avec KNOWN_AREAS, sinon heuristique stricte (courte, sans tel ni virgule).
    """
    stripped = line.strip()
    upper = ascii_upper(stripped)
    if not stripped:
        return False
    if "PHCIE" in upper or re.search(r"\bTEL\b", upper):
        return False
    if extract_phones(stripped):
        return False

    # Correspondance directe avec zones connues (normalisation)
    upper_clean = re.sub(r"\s+", " ", upper).strip()
    # Normalise les tirets pour comparaison
    upper_norm = re.sub(r"[-–—]", "-", upper_clean)
    for known in KNOWN_AREAS:
        known_norm = re.sub(r"[-–—]", "-", ascii_upper(known))
        if known_norm == upper_norm:
            return True

    # Heuristique pour zones non listées :
    # ligne courte, sans chiffres groupés (phone), sans virgule/point/parenthèse
    if len(stripped) <= 45 and not re.search(r"\d{2}[\s.]\d{2}", stripped):
        if not re.search(r"[.,;()]", stripped):
            if re.fullmatch(r"[A-ZÀ-Ÿa-zà-ÿ0-9 '\-/éèêëàâùûîïôœæÉÈÊËÀÂÙÛÎÏÔŒÆ]+", stripped):
                return True

    return False


def is_pharmacy_line(line: str) -> bool:
    """Vrai si la ligne débute une entrée pharmacie (contient PHCIE)."""
    upper = ascii_upper(line)
    return "PHCIE" in upper and (
        upper.strip().startswith("PHCIE")
        or re.match(r"^SECTEUR\s+\d+\s+PHCIE", upper.strip())
    )


# ---------------------------------------------------------------------------
# Parsing principal du PDF
# ---------------------------------------------------------------------------

def extract_all_lines(pdf_path: str) -> List[str]:
    """Extrait toutes les lignes texte brutes du PDF (pdfplumber)."""
    lines: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=3, y_tolerance=3)
            if text:
                for raw_line in text.splitlines():
                    stripped = raw_line.strip()
                    if stripped:
                        lines.append(stripped)
    return lines


def parse_pdf(pdf_path: str) -> Tuple[List[RawEntry], Optional[str], Optional[int]]:
    """
    Lit le PDF et retourne :
      - la liste des RawEntry
      - le slug du mois ('fevrier', 'mars', …)
      - l'année (2026, …)
    """
    all_lines = extract_all_lines(pdf_path)
    entries: List[RawEntry] = []

    month_slug: Optional[str] = None
    year: Optional[int] = None
    current_section = ""
    current_area = ""
    current_week: Tuple[Optional[str], Optional[str]] = (None, None)
    current_entry: Optional[RawEntry] = None

    def flush():
        nonlocal current_entry
        if current_entry is not None and current_entry.raw_lines:
            entries.append(current_entry)
            current_entry = None

    for line in all_lines:
        upper = ascii_upper(line)

        # ── Titre principal du document ──────────────────────────────────
        if "TOUR DE GARDE DU MOIS DE" in upper:
            if month_slug is None:
                m_slug, yr = infer_month_year_from_header(line)
                if m_slug:
                    month_slug, year = m_slug, yr
            continue

        # ── En-tête de permanence / instructions générales ───────────────
        if re.search(r"\bPERMANENCE\b|\bh/24\b|\bh /24\b", upper):
            continue

        # ── Semaine de garde ─────────────────────────────────────────────
        s, e = parse_week_header(line)
        if s and e:
            flush()
            current_week = (s, e)
            continue

        # ── En-tête de section ───────────────────────────────────────────
        if is_section_header(line):
            flush()
            current_section = clean_space(line).upper()
            continue

        # ── Secteur Yopougon (Secteur 1, Secteur 2 …) ───────────────────
        secteur_match = re.match(r"^Secteur\s+(\d+)\s+", line, flags=re.I)
        if secteur_match:
            # La ligne commence par "Secteur N PHCIE ..." → pharmacie
            rest = line[secteur_match.end():].strip()
            if is_pharmacy_line(rest) or is_pharmacy_line(line):
                flush()
                current_entry = RawEntry(
                    section=current_section,
                    area=current_area,
                    start_date=current_week[0] or "",
                    end_date=current_week[1] or "",
                    raw_lines=[rest if is_pharmacy_line(rest) else line],
                )
            # Sinon c'est juste un numéro de secteur sans pharmacie, on ignore
            continue

        # ── Sous-zone / quartier ─────────────────────────────────────────
        if is_area_header(line) and not is_pharmacy_line(line):
            flush()
            current_area = clean_space(line).upper()
            # Inférence de section si non encore définie (ex: page 1 sans "SECTION DE...")
            if not current_section:
                # Cherche une correspondance dans le mapping zone → section
                upper_area = ascii_upper(current_area).strip()
                for known_area, implied_section in AREA_TO_SECTION.items():
                    if ascii_upper(known_area) == upper_area:
                        current_section = implied_section
                        break
            continue

        # ── Ligne de pharmacie ───────────────────────────────────────────
        if is_pharmacy_line(line):
            flush()
            # Inférence de section via AREA_TO_SECTION si section non encore définie
            effective_section = current_section
            if not effective_section and current_area:
                upper_area = ascii_upper(current_area).strip()
                for known_area, implied_section in AREA_TO_SECTION.items():
                    if ascii_upper(known_area) == upper_area:
                        effective_section = implied_section
                        break
            current_entry = RawEntry(
                section=effective_section,
                area=current_area,
                start_date=current_week[0] or "",
                end_date=current_week[1] or "",
                raw_lines=[line],
            )
            continue

        # ── Continuation de la pharmacie en cours ────────────────────────
        if current_entry is not None:
            current_entry.raw_lines.append(line)

    flush()
    return entries, month_slug, year


# ---------------------------------------------------------------------------
# Normalisation d'une entrée brute → dict structuré
# ---------------------------------------------------------------------------

def parse_entry(entry: RawEntry) -> Dict[str, object]:
    """Extrait nom, adresse, téléphones d'un RawEntry."""
    whole = entry.full_text()

    # ── Nom de la pharmacie ──────────────────────────────────────────────
    # On s'arrête avant le slash proprietaire, le tiret-TEL ou un titre civil
    first_line = clean_space(entry.raw_lines[0]) if entry.raw_lines else ""
    # Supprime "Secteur N " en début
    first_line = re.sub(r"^Secteur\s+\d+\s+", "", first_line, flags=re.I)

    name_match = re.search(
        r"\bPHCIE\s+(.*?)(?=\s*/|\s+[-–]\s*TEL\b|\s+TEL\b|\s+(?:MME|M\.|M |MLLE|DR|PR)\b)",
        first_line, flags=re.I,
    )
    if not name_match:
        name_match = re.search(r"\bPHCIE\s+(.+?)(?:\s*/\s*|\s+-\s*TEL|\s+TEL)", first_line, flags=re.I)
    if not name_match:
        name_match = re.search(r"\bPHCIE\s+(.+)$", first_line, flags=re.I)

    pharmacy_name = normalize_name_display(name_match.group(1) if name_match else first_line)

    # ── Téléphones ───────────────────────────────────────────────────────
    phones = extract_phones(whole)

    # ── Adresse ──────────────────────────────────────────────────────────
    address = ""
    # Texte après TEL.
    tel_split = re.split(r"\bTEL\.?\s*:?\s*", whole, maxsplit=1, flags=re.I)
    if len(tel_split) > 1:
        tail = tel_split[1]
        # On saute les numéros de téléphone en début de tail
        tail_no_phones = strip_phones_from_text(tail)
        address = tail_no_phones
    # Fallback : lignes de continuation
    if not address and len(entry.raw_lines) > 1:
        address = strip_phones_from_text(" ".join(entry.raw_lines[1:]))

    return {
        "pharmacy_name": pharmacy_name,
        "section":       clean_space(entry.section),
        "area":          clean_space(entry.area),
        "address":       clean_space(address),
        "phones":        phones,
        "start_date":    entry.start_date,
        "end_date":      entry.end_date,
        "raw_text":      whole,
    }


# ---------------------------------------------------------------------------
# Clé déterministe & déduplication
# ---------------------------------------------------------------------------

def deterministic_key(name: str, area: str, address: str) -> str:
    """Génère une pharmacy_key stable via SHA-1 sur les champs normalisés."""
    base = f"{normalize_for_match(name)}|{normalize_for_match(area)}|{normalize_for_match(address)}"
    return "ph_" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]


def dedup_preserve(values: Iterable[str]) -> List[str]:
    """Déduplique en préservant l'ordre d'apparition."""
    seen, out = set(), []
    for v in values:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def choose_value(values: Iterable[str], prefer_longest: bool = False) -> str:
    """Choisit la valeur la plus fréquente (à égalité, la plus longue si prefer_longest)."""
    clean = [clean_space(v) for v in values if clean_space(v)]
    if not clean:
        return ""
    counts = Counter(clean)
    top = max(counts.values())
    candidates = [v for v, c in counts.items() if c == top]
    return max(candidates, key=len) if prefer_longest else max(candidates, key=len)


# ---------------------------------------------------------------------------
# Réconciliation avec le référentiel mensuel précédent
# ---------------------------------------------------------------------------

def build_reference(csv_path: Optional[str]) -> Optional[pd.DataFrame]:
    """Charge le CSV référentiel et calcule les colonnes normalisées."""
    if not csv_path or not os.path.isfile(csv_path):
        return None
    ref = pd.read_csv(csv_path).fillna("")
    ref["norm_name"]    = ref["pharmacy_name"].map(normalize_for_match)
    ref["norm_area"]    = ref["area"].map(normalize_for_match)
    ref["norm_address"] = ref["address"].map(normalize_for_match)
    return ref


def match_reference(row: Dict, reference: Optional[pd.DataFrame]) -> Optional[pd.Series]:
    """
    Cherche la meilleure correspondance dans le référentiel.
    Système de score :
      +50  zone identique
      +30  zone partielle
      +60  similarité adresse (ratio × 60)
      +20  adresse identique
      +10  candidat unique
    Seuil d'acceptation : score ≥ 45.
    """
    if reference is None or reference.empty:
        return None

    norm_name    = normalize_for_match(row["pharmacy_name"])
    norm_area    = normalize_for_match(row["area"])
    norm_address = normalize_for_match(row["address"])

    candidates = reference[reference["norm_name"] == norm_name]
    if candidates.empty:
        return None

    best, best_score = None, -1
    for _, cand in candidates.iterrows():
        score = 0
        if cand["norm_area"] == norm_area and norm_area:
            score += 50
        elif cand["norm_area"] and (cand["norm_area"] in norm_area or norm_area in cand["norm_area"]):
            score += 30
        if cand["norm_address"] and norm_address:
            ratio = difflib.SequenceMatcher(None, cand["norm_address"], norm_address).ratio()
            score += int(ratio * 60)
            if cand["norm_address"] == norm_address:
                score += 20
        if len(candidates) == 1:
            score += 10
        if score > best_score:
            best_score, best = score, cand

    threshold = 45 if len(candidates) > 1 else 10
    return best if (best is not None and best_score >= threshold) else None


# ---------------------------------------------------------------------------
# Construction des DataFrames de sortie
# ---------------------------------------------------------------------------

def build_outputs(
    pdf_path: str,
    reference_csv: Optional[str],
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict, str, int, float]:
    """
    Orchestre l'ensemble du pipeline ETL.
    Retourne : (pharmacies_df, duty_df, seed_dict, month_slug, year, match_ratio)
    """
    # 1. Parse
    raw_entries, month_slug, year = parse_pdf(pdf_path)
    if not raw_entries:
        raise ValueError("Aucune pharmacie n'a pu être extraite du PDF.")
    if not month_slug:
        month_slug = "inconnu"
    if not year:
        year = dt.date.today().year

    # 2. Normalise
    reference = build_reference(reference_csv)
    normalized_rows: List[Dict] = []
    matched = 0

    for raw in raw_entries:
        entry = parse_entry(raw)

        # Réconciliation référentiel
        cand = match_reference(entry, reference)
        if cand is not None:
            matched += 1
            entry["pharmacy_key"] = cand["pharmacy_key"]
            entry["pharmacy_name"] = choose_value([entry["pharmacy_name"], cand["pharmacy_name"]])
            entry["area"]    = choose_value([entry["area"],    cand["area"]])
            entry["section"] = choose_value([entry["section"], cand["section"]])
            entry["address"] = choose_value([entry["address"], cand["address"]], prefer_longest=True)
            # Fusion téléphones
            try:
                ref_phones = json.loads(cand["phones_json"]) if cand.get("phones_json") else []
            except Exception:
                ref_phones = [p.strip() for p in str(cand.get("phones_str", "")).split(";") if p.strip()]
            entry["phones"] = dedup_preserve(entry["phones"] + ref_phones)
        else:
            entry["pharmacy_key"] = deterministic_key(
                entry["pharmacy_name"], entry["section"] + " " + entry["area"], entry["address"]
            )

        normalized_rows.append(entry)

    # 3. DataFrame duty (périodes de garde)
    duty_df = pd.DataFrame(normalized_rows)
    duty_out = (
        duty_df[["pharmacy_key", "pharmacy_name", "section", "area", "start_date", "end_date"]]
        .copy()
        .drop_duplicates(subset=["pharmacy_key", "start_date", "end_date"])
        .sort_values(["start_date", "section", "area", "pharmacy_name"])
        .reset_index(drop=True)
    )
    duty_out["duty_type"] = "24H"
    duty_out["source"]    = "UNPPCI"
    duty_out["timezone"]  = "Africa/Abidjan"

    # 4. DataFrame pharmacies (une ligne par pharmacie unique)
    pharm_rows: List[Dict] = []
    for pharm_key, grp in duty_df.groupby("pharmacy_key", sort=False):
        all_phones = dedup_preserve(
            ph for phones_list in grp["phones"] for ph in phones_list
        )
        pharm_rows.append({
            "pharmacy_key":  pharm_key,
            "pharmacy_name": choose_value(grp["pharmacy_name"]),
            "section":       choose_value(grp["section"]),
            "area":          choose_value(grp["area"]),
            "address":       choose_value(grp["address"], prefer_longest=True),
            "phones_str":    " ; ".join(all_phones),
            "phones_json":   json.dumps(all_phones, ensure_ascii=False),
        })

    pharmacies_out = (
        pd.DataFrame(pharm_rows)
        .sort_values(["section", "area", "pharmacy_name"])
        .reset_index(drop=True)
    )

    # 5. Seed JSON
    weeks = (
        duty_out[["start_date", "end_date"]]
        .drop_duplicates()
        .values.tolist()
    )
    seed = {
        "source": {
            "name": "UNPPCI",
            "document": f"Tour de garde Abidjan — {month_slug} {year}",
            "pdf_file": os.path.basename(pdf_path),
            "generated_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        },
        "period": {
            "month": month_slug,
            "year": year,
        },
        "stats": {
            "unique_pharmacies": int(pharmacies_out["pharmacy_key"].nunique()),
            "duty_entries": int(len(duty_out)),
            "weeks_covered": len(weeks),
            "weeks": weeks,
            "reference_used": reference_csv is not None,
            "key_match_ratio": round(matched / max(len(normalized_rows), 1), 4),
        },
    }

    match_ratio = matched / max(len(normalized_rows), 1)
    return pharmacies_out, duty_out, seed, month_slug, year, match_ratio


# ---------------------------------------------------------------------------
# Écriture des fichiers de sortie
# ---------------------------------------------------------------------------

def write_outputs(
    pharmacies_out: pd.DataFrame,
    duty_out: pd.DataFrame,
    seed: Dict,
    output_dir: str,
    month_slug: str,
    year: int,
) -> Tuple[str, str, str]:
    """Écrit les 3 fichiers de sortie et retourne leurs chemins."""
    os.makedirs(output_dir, exist_ok=True)

    prefix = f"unppci"
    suffix = f"{month_slug}_{year}"

    pharm_path = os.path.join(output_dir, f"{prefix}_pharmacies_{suffix}.csv")
    duty_path  = os.path.join(output_dir, f"{prefix}_duty_periods_{suffix}.csv")
    seed_path  = os.path.join(output_dir, f"{prefix}_seed_{suffix}.json")

    pharmacies_out.to_csv(pharm_path, index=False, encoding="utf-8-sig")
    duty_out.to_csv(duty_path,  index=False, encoding="utf-8-sig")
    with open(seed_path, "w", encoding="utf-8") as fh:
        json.dump(seed, fh, ensure_ascii=False, indent=2)

    return pharm_path, duty_path, seed_path


# ---------------------------------------------------------------------------
# Point d'entrée CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Parseur ETL réutilisable pour les PDFs mensuels de tour de garde "
            "des pharmacies UNPPCI (zone Abidjan)."
        )
    )
    parser.add_argument(
        "--pdf", required=True,
        help="Chemin vers le PDF mensuel (ex: garde-fevrier-2026.pdf).",
    )
    parser.add_argument(
        "--output-dir", default=".",
        help="Répertoire de sortie pour les CSV et JSON (défaut: répertoire courant).",
    )
    parser.add_argument(
        "--reference", default=None,
        help=(
            "Optionnel : CSV de référence du mois précédent "
            "(unppci_pharmacies_janvier_2026.csv) pour réutiliser les pharmacy_key."
        ),
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  UNPPCI Guard Duty Parser — Abidjan")
    print(f"{'='*60}")
    print(f"  PDF      : {args.pdf}")
    print(f"  Sortie   : {args.output_dir}")
    if args.reference:
        print(f"  Référent : {args.reference}")
    print()

    pharmacies_out, duty_out, seed, month_slug, year, match_ratio = build_outputs(
        pdf_path=args.pdf,
        reference_csv=args.reference,
    )

    pharm_path, duty_path, seed_path = write_outputs(
        pharmacies_out=pharmacies_out,
        duty_out=duty_out,
        seed=seed,
        output_dir=args.output_dir,
        month_slug=month_slug,
        year=year,
    )

    print("✅ Traitement terminé.")
    print(f"\n  📄 Pharmacies    : {pharm_path}")
    print(f"  📅 Périodes garde: {duty_path}")
    print(f"  🗂  Seed JSON     : {seed_path}")
    print(f"\n  📊 Statistiques :")
    print(f"     Pharmacies uniques : {seed['stats']['unique_pharmacies']}")
    print(f"     Entrées de garde   : {seed['stats']['duty_entries']}")
    print(f"     Semaines couvertes : {seed['stats']['weeks_covered']}")
    for w in seed['stats']['weeks']:
        print(f"       • {w[0]}  →  {w[1]}")
    if args.reference:
        print(f"     Taux de matching   : {match_ratio:.1%}")
    print()


if __name__ == "__main__":
    main()
