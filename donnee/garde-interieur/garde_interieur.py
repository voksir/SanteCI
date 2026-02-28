#!/usr/bin/env python3
"""
garde_interieur.py — Parseur ETL UNPPCI (Villes de l'Intérieur)
================================================================
Extrait, normalise et encode les données des PDFs mensuels de tour de garde
des pharmacies de l'intérieur de la Côte d'Ivoire publiés par l'UNPPCI.

Utilisation
-----------
  python garde_interieur.py --pdf garde-interieur-fevrier-2026.pdf --output-dir ./output

  # Avec référentiel mensuel précédent (pour réutiliser les pharmacy_key)
  python garde_interieur.py \
      --pdf garde-interieur-mars-2026.pdf \
      --output-dir ./output \
      --reference ./output/unppci_interieur_pharmacies_fevrier_2026.csv

Sorties
-------
  unppci_interieur_pharmacies_<mois>_<année>.csv
  unppci_interieur_duty_periods_<mois>_<année>.csv
  unppci_interieur_seed_<mois>_<année>.json

Dépendances
-----------
  pip install pdfplumber pandas
"""

import re
import sys
import json
import hashlib
import argparse
import unicodedata
from pathlib import Path
from datetime import datetime, date
from difflib import SequenceMatcher

import pdfplumber
import pandas as pd

# ─────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────

MONTHS_FR = {
    "JANVIER":   (1,  "janvier"),
    "FEVRIER":   (2,  "fevrier"),
    "MARS":      (3,  "mars"),
    "AVRIL":     (4,  "avril"),
    "MAI":       (5,  "mai"),
    "JUIN":      (6,  "juin"),
    "JUILLET":   (7,  "juillet"),
    "AOUT":      (8,  "aout"),
    "SEPTEMBRE": (9,  "septembre"),
    "OCTOBRE":   (10, "octobre"),
    "NOVEMBRE":  (11, "novembre"),
    "DECEMBRE":  (12, "decembre"),
}

# Villes/zones connues dans les PDFs intérieur
# Clé = forme normalisée (ASCII upper), valeur = nom canonique affiché
KNOWN_CITIES = {
    "ABENGOUROU":     "Abengourou",
    "ABOISSO":        "Aboisso",
    "ADIAKE":         "Adiake",
    "ADZOPE":         "Adzope",
    "AGBOVILLE":      "Agboville",
    "AGNIBILEKRO":    "Agnibilekro",
    "AZAGUIE":        "Azaguie",
    "BAYOTA":         "Bayota",
    "BONDOUKOU":      "Bondoukou",
    "BONOUA":         "Bonoua",
    "BOUAFLE":        "Bouafle",
    "BOUAKE":         "Bouake",
    "DABOU":          "Dabou",
    "DANANE":         "Danane",
    "DALOA":          "Daloa",
    "DIEGONEFLA":     "Diegonefla",
    "DIVO":           "Divo",
    "DUEKOUE":        "Duekoue",
    "GAGNOA":         "Gagnoa",
    "GRAND-BASSAM":   "Grand-Bassam",
    "GRAND BASSAM":   "Grand-Bassam",
    "GUIGLO":         "Guiglo",
    "ISSIA":          "Issia",
    "KORHOGO":        "Korhogo",
    "MAN":            "Man",
    "ODIENNE":        "Odienne",
    "OUME":           "Oume",
    "SAN PEDRO":      "San Pedro",
    "SINFRA":         "Sinfra",
    "SONGON":         "Songon / Km 17",
    "SONGON / KM 17": "Songon / Km 17",
    "KM 17 / SONGON": "Songon / Km 17",
    "KM 17":          "Songon / Km 17",
    "SOUBRE":         "Soubre",
    "TIASSALE":       "Tiassale",
    "YAMOUSSOUKRO":   "Yamoussoukro",
}

# Sous-sections spéciales (page 9+) avec leur format de dates particulier
SOUS_SECTIONS = {"AZAGUIE", "BONDOUKOU", "OUME"}

# Lignes à ignorer (headers, séparateurs)
IGNORE_PATTERNS = [
    r"^TOUR DE GARDE DU MOIS",
    r"^SEMAINE DU SAMEDI",
    r"^PERMANENCE 24H",
    r"^PERMANENCE DU SAMEDI",
    r"^SOUS SECTION",
]

# Regex principale pour détecter une ligne pharmacie
RE_PHCIE = re.compile(r"PHCIE\s+", re.IGNORECASE)

# Regex pour le téléphone ivoirien (formats: XX XX XX XX ou XXXXXXXXXX)
RE_TEL = re.compile(
    r"\b(\d{2}[\s.]\d{2}[\s.]\d{2}[\s.]\d{2}(?:[\s.]\d{2})?|\d{8,10})\b"
)

# Regex pour en-tête de semaine principale (pages 1-8)
RE_WEEK_MAIN = re.compile(
    r"SEMAINE DU SAMEDI\s+(\d{1,2})\s+(?:AU\s+)?(?:(\w+)\s+)?AU\s+VENDREDI\s+(\d{1,2})\s+(\w+)\s+(\d{4})",
    re.IGNORECASE,
)

# Regex pour en-tête de semaine (même mois ou deux mois différents)
# Groupe 1: jour début, Groupe 2: mois début (optionnel), Groupe 3: jour fin, Groupe 4: mois fin, Groupe 5: année
RE_WEEK_CROSS = re.compile(
    r"SEMAINE DU SAMEDI\s+(\d{1,2})(?:\s+([A-Z]+))?\s+AU\s+VENDREDI\s+(\d{1,2})\s+([A-Z]+)\s+(\d{4})",
    re.IGNORECASE,
)

# Regex pour sous-section période (AZAGUIE, BONDOUKOU)
RE_SUBSEC_PERIOD = re.compile(
    r"(?:SAMEDI|LUNDI)\s+(\d{1,2})\s*(?:(\w+))?\s*(?:AU|AU\s+SAMEDI|AU\s+DIMANCHE)\s+(?:SAMEDI|DIMANCHE)?\s*(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?",
    re.IGNORECASE,
)

# Regex titre du document pour détecter mois/année
RE_TITLE = re.compile(
    r"TOUR DE GARDE DU MOIS DE\s+(\w+)\s+(\d{4})",
    re.IGNORECASE,
)

# ─────────────────────────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────────────────────────

def normalize_apostrophes(text: str) -> str:
    """Remplace les apostrophes typographiques par des apostrophes droites."""
    for ch in ("\u2019", "\u2018", "\u2032", "\u0060", "\u00b4"):
        text = text.replace(ch, "'")
    return text


def ascii_upper(text: str) -> str:
    """Convertit en majuscules ASCII, supprime les accents."""
    text = normalize_apostrophes(text)
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_str.upper()


def clean_space(text: str) -> str:
    """Supprime les espaces multiples et normalise les espaces."""
    return re.sub(r"\s+", " ", text).strip()


def normalize_for_key(text: str) -> str:
    """Normalise un texte pour la génération de clé SHA-1."""
    return re.sub(r"[^A-Z0-9]", "", ascii_upper(text))


def make_pharmacy_key(name: str, city: str, address: str) -> str:
    """Génère une clé déterministe pour une pharmacie."""
    raw = f"{normalize_for_key(name)}|{normalize_for_key(city)}|{normalize_for_key(address)}"
    return "ph_" + hashlib.sha1(raw.encode()).hexdigest()[:12]


def extract_phones(text: str) -> list[str]:
    """Extrait les numéros de téléphone ivoiriens d'un texte."""
    phones = []
    # Chercher après TEL ou TEL.
    tel_match = re.search(r"TEL[.\s]*(.+)", text, re.IGNORECASE)
    search_zone = tel_match.group(1) if tel_match else text

    for m in RE_TEL.finditer(search_zone):
        raw = m.group(0)
        digits = re.sub(r"\D", "", raw)
        if len(digits) >= 8:
            # Formater en XX XX XX XX [XX]
            if len(digits) == 10:
                formatted = f"{digits[0:2]} {digits[2:4]} {digits[4:6]} {digits[6:8]} {digits[8:10]}"
            elif len(digits) == 8:
                formatted = f"{digits[0:2]} {digits[2:4]} {digits[4:6]} {digits[6:8]}"
            else:
                formatted = raw.strip()
            if formatted not in phones:
                phones.append(formatted)
    return phones


def extract_address(text: str) -> str:
    """Extrait l'adresse (texte après TEL et numéros de téléphone)."""
    # Supprimer la partie avant PHCIE
    # Supprimer les numéros de téléphone
    addr = re.sub(r"TEL[.\s]*[\d\s./]+", "", text, flags=re.IGNORECASE)
    # Supprimer les motifs de téléphone isolés
    addr = re.sub(r"\b\d{2}[\s.]\d{2}[\s.]\d{2}[\s.]\d{2}(?:[\s.]\d{2})?\b", "", addr)
    # Supprimer les slashs isolés en début
    addr = re.sub(r"^\s*/\s*", "", addr)
    addr = re.sub(r"\s*/\s*$", "", addr)
    return clean_space(addr)


def parse_date_fr(day: int, month_str: str, year: int) -> date | None:
    """Parse une date avec mois en français."""
    month_key = ascii_upper(month_str.strip())
    if month_key in MONTHS_FR:
        m = MONTHS_FR[month_key][0]
        try:
            return date(year, m, day)
        except ValueError:
            pass
    return None


def parse_week_header(line: str, default_year: int) -> tuple[date | None, date | None]:
    """
    Parse un en-tête de semaine et retourne (start_date, end_date).
    Gère les semaines à cheval sur deux mois.
    Formats reconnus:
      SEMAINE DU SAMEDI DD AU VENDREDI DD MOIS YYYY        (même mois)
      SEMAINE DU SAMEDI DD MOIS AU VENDREDI DD MOIS YYYY   (mois différents)
    """
    line_upper = ascii_upper(line)

    m = RE_WEEK_CROSS.search(line_upper)
    if m:
        d1, mo1, d2, mo2, yr = m.groups()
        year = int(yr)
        # Si mo1 est absent ou pas reconnu → même mois que la fin
        if mo1 and mo1 in MONTHS_FR:
            start = parse_date_fr(int(d1), mo1, year)
        else:
            # Même mois que mo2 — mais si start > end c'est le mois précédent
            end_tmp = parse_date_fr(int(d2), mo2, year)
            start_same = parse_date_fr(int(d1), mo2, year)
            if start_same and end_tmp and start_same > end_tmp:
                # Début dans le mois précédent
                m_num = MONTHS_FR.get(mo2, (0,))[0]
                if m_num > 1:
                    prev_names = [k for k, v in MONTHS_FR.items() if v[0] == m_num - 1]
                    if prev_names:
                        start = parse_date_fr(int(d1), prev_names[0], year)
                    else:
                        start = start_same
                else:
                    start = parse_date_fr(int(d1), "DECEMBRE", year - 1)
            else:
                start = start_same
        end = parse_date_fr(int(d2), mo2, year)
        return start, end

    return None, None


def parse_subsection_period(line: str, default_year: int) -> tuple[date | None, date | None]:
    """
    Parse une période de sous-section.
    Formats:
      SAMEDI DD [MON] AU SAMEDI DD MON [YYYY]: ...
      LUNDI DD AU DIMANCHE DD MON [YYYY]:
    """
    line_upper = ascii_upper(line)

    # Pattern générique : JOUR DD [MON] AU JOUR DD MON [YYYY]
    pattern = re.compile(
        r"(?:SAMEDI|LUNDI)\s+(\d{1,2})\s*(?:([A-Z]+)\s+)?AU\s+"
        r"(?:SAMEDI|DIMANCHE)\s+(\d{1,2})\s+([A-Z]+)(?:\s+(\d{4}))?",
        re.IGNORECASE,
    )
    m = pattern.search(line_upper)
    if m:
        d1, mo1, d2, mo2, yr_str = m.groups()
        year = int(yr_str) if yr_str else default_year

        if mo1 and mo1 in MONTHS_FR:
            start = parse_date_fr(int(d1), mo1, year)
        else:
            # même mois que la fin
            start = parse_date_fr(int(d1), mo2, year)
            # si start > end, c'est le mois précédent
            end_tmp = parse_date_fr(int(d2), mo2, year)
            if start and end_tmp and start > end_tmp:
                # Calculer le mois précédent
                if MONTHS_FR.get(mo2, (0,))[0] == 1:
                    start = parse_date_fr(int(d1), "DECEMBRE", year - 1)
                else:
                    prev_m = MONTHS_FR.get(mo2, (0,))[0] - 1
                    prev_name = [k for k, v in MONTHS_FR.items() if v[0] == prev_m]
                    if prev_name:
                        start = parse_date_fr(int(d1), prev_name[0], year)

        end = parse_date_fr(int(d2), mo2, year)
        return start, end

    return None, None


# ─────────────────────────────────────────────────────────────
# STRUCTURES DE DONNÉES
# ─────────────────────────────────────────────────────────────

class RawEntry:
    """Représente une entrée brute de pharmacie avant normalisation."""
    __slots__ = ("city", "raw_lines", "week_start", "week_end", "duty_type", "subsection")

    def __init__(self, city: str, raw_lines: list[str],
                 week_start: date | None, week_end: date | None,
                 duty_type: str = "24H", subsection: str = ""):
        self.city = city
        self.raw_lines = raw_lines
        self.week_start = week_start
        self.week_end = week_end
        self.duty_type = duty_type
        self.subsection = subsection  # pour Gagnoa (permanence réduite)


class ParsedPharmacy:
    """Pharmacie normalisée."""
    __slots__ = ("pharmacy_key", "pharmacy_name", "city", "address",
                 "phones", "duty_type", "week_start", "week_end", "subsection")

    def __init__(self, pharmacy_key: str, pharmacy_name: str, city: str,
                 address: str, phones: list[str],
                 duty_type: str, week_start: date | None, week_end: date | None,
                 subsection: str = ""):
        self.pharmacy_key = pharmacy_key
        self.pharmacy_name = pharmacy_name
        self.city = city
        self.address = address
        self.phones = phones
        self.duty_type = duty_type
        self.week_start = week_start
        self.week_end = week_end
        self.subsection = subsection


# ─────────────────────────────────────────────────────────────
# PARSEUR
# ─────────────────────────────────────────────────────────────

class InteriorGuardParser:
    """Parseur principal pour les PDFs de l'intérieur."""

    def __init__(self, pdf_path: str, reference_path: str | None = None):
        self.pdf_path = pdf_path
        self.reference_path = reference_path
        self.ref_df: pd.DataFrame | None = None
        self.month_num: int = 0
        self.month_slug: str = ""
        self.year: int = 0
        self.raw_entries: list[RawEntry] = []
        self.pharmacies: list[ParsedPharmacy] = []

        if reference_path:
            try:
                self.ref_df = pd.read_csv(reference_path, dtype=str)
                print(f"[INFO] Référentiel chargé: {len(self.ref_df)} entrées")
            except Exception as e:
                print(f"[WARN] Impossible de charger le référentiel: {e}")

    # ──────────────────────────────────
    # Extraction brute du PDF
    # ──────────────────────────────────

    def extract_lines(self) -> list[str]:
        """Extrait toutes les lignes du PDF (toutes pages)."""
        lines = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                for line in text.split("\n"):
                    line = normalize_apostrophes(line).strip()
                    if line:
                        lines.append(line)
        return lines

    # ──────────────────────────────────
    # Détection du mois/année
    # ──────────────────────────────────

    def detect_period(self, lines: list[str]) -> None:
        """Détecte mois et année à partir du titre du PDF."""
        for line in lines[:5]:
            m = RE_TITLE.search(ascii_upper(line))
            if m:
                month_str, year_str = m.groups()
                if month_str in MONTHS_FR:
                    self.month_num, self.month_slug = MONTHS_FR[month_str]
                    self.year = int(year_str)
                    print(f"[INFO] Période détectée: {self.month_slug} {self.year}")
                    return
        # Fallback: détecter depuis le nom de fichier
        fname = Path(self.pdf_path).stem.lower()
        for month_key, (num, slug) in MONTHS_FR.items():
            if slug in fname:
                self.month_num, self.month_slug = num, slug
                break
        m_year = re.search(r"20\d{2}", fname)
        if m_year:
            self.year = int(m_year.group())
        if not self.year:
            self.year = datetime.now().year
        if not self.month_num:
            self.month_num = datetime.now().month
            self.month_slug = list(MONTHS_FR.values())[self.month_num - 1][1]

    # ──────────────────────────────────
    # Reconnaissance de ligne
    # ──────────────────────────────────

    def is_ignore_line(self, line: str) -> bool:
        """Retourne True si la ligne doit être ignorée."""
        line_up = ascii_upper(line)
        for pat in IGNORE_PATTERNS:
            if re.search(pat, line_up):
                return True
        return False

    def is_week_header(self, line: str) -> bool:
        return bool(RE_WEEK_MAIN.search(ascii_upper(line)) or
                    RE_WEEK_CROSS.search(ascii_upper(line)))

    def is_subsection_header(self, line: str) -> tuple[bool, str]:
        """Détecte SOUS SECTION XXXX. Retourne (bool, nom_ville)."""
        m = re.match(r"SOUS SECTION\s+(?:DE\s+)?(.+)", ascii_upper(line))
        if m:
            city_raw = m.group(1).strip()
            canonical = KNOWN_CITIES.get(city_raw, city_raw.title())
            return True, canonical
        return False, ""

    def is_subsection_period_line(self, line: str) -> bool:
        """Ligne de période dans une sous-section (SAMEDI/LUNDI DD...)."""
        up = ascii_upper(line)
        return bool(re.match(r"^(SAMEDI|LUNDI)\s+\d", up))

    def detect_city_prefix(self, line: str) -> tuple[str, str]:
        """
        Détecte si la ligne commence par un nom de ville connu.
        Retourne (city_canonical, reste_de_ligne).
        """
        line_up = ascii_upper(line)

        # Trier par longueur décroissante pour éviter les faux positifs (ex: "SAN PEDRO" avant "SAN")
        for key in sorted(KNOWN_CITIES.keys(), key=len, reverse=True):
            if line_up.startswith(key + " ") or line_up == key:
                city = KNOWN_CITIES[key]
                rest = line[len(key):].strip()
                return city, rest

        return "", line

    def is_phcie_line(self, line: str) -> bool:
        """Détecte si la ligne est une entrée de pharmacie."""
        return bool(RE_PHCIE.search(line))

    def is_continuation_line(self, line: str) -> bool:
        """
        Ligne de continuation (adresse, suite TEL...).
        Ne commence ni par une ville ni par PHCIE.
        """
        city, _ = self.detect_city_prefix(line)
        if city:
            return False
        if self.is_phcie_line(line):
            return False
        if self.is_ignore_line(line):
            return False
        if self.is_week_header(line):
            return False
        is_ss, _ = self.is_subsection_header(line)
        if is_ss:
            return False
        if self.is_subsection_period_line(line):
            return False
        return True

    # ──────────────────────────────────
    # Parsing principal (pages 1-8)
    # ──────────────────────────────────

    def parse_main_pages(self, lines: list[str]) -> None:
        """
        Parse les pages 1-8 : format VILLE PHCIE ... / TEL ... / ADRESSE
        Gagnoa a un bloc "PERMANENCE SAMEDI..." qui marque une duty_type différente.
        """
        current_week_start: date | None = None
        current_week_end:   date | None = None
        current_city: str = ""
        pending_lines: list[str] = []   # lignes en cours d'accumulation
        gagnoa_reduced = False           # flag permanence réduite Gagnoa

        def flush_pending():
            """Transforme les lignes accumulées en RawEntry."""
            nonlocal pending_lines
            if not pending_lines:
                return
            combined = " ".join(pending_lines)
            if self.is_phcie_line(combined) and current_city:
                dtype = "PARTIELLE" if gagnoa_reduced else "24H"
                self.raw_entries.append(RawEntry(
                    city=current_city,
                    raw_lines=[combined],
                    week_start=current_week_start,
                    week_end=current_week_end,
                    duty_type=dtype,
                ))
            pending_lines = []

        # Marqueur pour pages sous-sections (page 9)
        in_subsection = False

        for line in lines:
            # Arrêt quand on entre dans les sous-sections
            if re.search(r"SOUS SECTION", ascii_upper(line)):
                flush_pending()
                in_subsection = True
                break

            # En-tête de semaine — PRIORITÉ absolue (la ligne contient aussi PERMANENCE)
            if self.is_week_header(line):
                flush_pending()
                start, end = parse_week_header(line, self.year)
                if start and end:
                    current_week_start, current_week_end = start, end
                    print(f"[INFO] Semaine: {start} → {end}")
                gagnoa_reduced = False
                continue

            # Ignorer les headers répétitifs (titre doc, permanence réduite Gagnoa…)
            if self.is_ignore_line(line):
                # Détecter flag permanence réduite Gagnoa
                if re.search(r"PERMANENCE DU SAMEDI", ascii_upper(line)):
                    gagnoa_reduced = True
                else:
                    gagnoa_reduced = False
                flush_pending()
                continue

            # Ligne commençant par un nom de ville
            city, rest = self.detect_city_prefix(line)
            if city:
                flush_pending()
                if city != current_city:
                    gagnoa_reduced = False  # Reset quand on change de ville
                current_city = city
                # Le reste peut commencer par PHCIE ou être vide
                if rest and self.is_phcie_line(rest):
                    pending_lines = [rest]
                elif rest:
                    # Cas rare: ville sans pharmacie sur la même ligne
                    pending_lines = [rest]
                # Sinon: la prochaine ligne sera la pharmacie
                continue

            # Ligne PHCIE (sans préfixe ville)
            if self.is_phcie_line(line):
                flush_pending()
                pending_lines = [line]
                continue

            # Ligne de continuation
            if self.is_continuation_line(line):
                if pending_lines:
                    pending_lines.append(line)
                # else: continuation orpheline → ignorer
                continue

    # ──────────────────────────────────
    # Parsing sous-sections (page 9)
    # ──────────────────────────────────

    def parse_subsections(self, lines: list[str]) -> None:
        """
        Parse les sous-sections spéciales (Azaguie, Bondoukou, Oume).
        Format: SAMEDI/LUNDI DD [MON] AU SAMEDI/DIMANCHE DD MON [YYYY]: PHCIE...
        ou:     SAMEDI/LUNDI...:
                PHCIE ...
                PHCIE ...
        """
        current_city = ""
        current_start: date | None = None
        current_end:   date | None = None
        pending_lines: list[str] = []
        in_subsection_block = False

        def flush():
            nonlocal pending_lines
            if pending_lines and current_city and current_start:
                combined = " ".join(pending_lines)
                if self.is_phcie_line(combined):
                    self.raw_entries.append(RawEntry(
                        city=current_city,
                        raw_lines=[combined],
                        week_start=current_start,
                        week_end=current_end,
                        duty_type="24H",
                        subsection=current_city,
                    ))
            pending_lines = []

        for line in lines:
            line_up = ascii_upper(line)

            # Détection entête sous-section
            is_ss, city = self.is_subsection_header(line)
            if is_ss:
                flush()
                current_city = city
                in_subsection_block = True
                current_start = None
                current_end = None
                continue

            if not in_subsection_block:
                continue

            # Ligne de période dans la sous-section
            if self.is_subsection_period_line(line):
                flush()
                start, end = parse_subsection_period(line, self.year)
                if start and end:
                    current_start, current_end = start, end
                # La pharmacie peut être sur la même ligne après ":"
                after_colon = re.split(r":\s*", line, maxsplit=1)
                if len(after_colon) > 1 and self.is_phcie_line(after_colon[1]):
                    pending_lines = [after_colon[1].strip()]
                continue

            # Ligne PHCIE
            if self.is_phcie_line(line):
                flush()
                pending_lines = [line]
                continue

            # Continuation
            if pending_lines and not self.is_ignore_line(line):
                pending_lines.append(line)

        flush()

    # ──────────────────────────────────
    # Normalisation d'une RawEntry
    # ──────────────────────────────────

    def normalize_entry(self, entry: RawEntry) -> ParsedPharmacy | None:
        """
        Normalise une RawEntry en ParsedPharmacy.
        Extrait: nom pharmacie, téléphones, adresse.
        """
        raw = " ".join(entry.raw_lines)
        raw = clean_space(raw)

        # ── Nom de la pharmacie ──────────────────────────────
        # Format: PHCIE <NOM> / <PHARMACIEN> - TEL. <num> / <adresse>
        # ou:     PHCIE <NOM> / <PHARMACIEN> - TEL <num> / <adresse>

        # ── Extraction du nom: ce qui est entre PHCIE et "/ MME|M.|MLLE|DR" ou "- TEL" ──
        # Formats courants:
        #   PHCIE NOM / MME PHARMACIEN - TEL ...
        #   PHCIE NOM / M PHARMACIEN - TEL ...
        #   PHCIE NOM -TEL ...
        #   PHCIE NOM/ M. PHARMACIEN - TEL ...
        name_match = re.match(
            r"PHCIE\s+(.+?)\s*(?:/\s*(?:MME?\.?\s+|M\.?\s+|MLLE?\.?\s+|DR\.?\s+)|[\s–-]+TEL)",
            raw,
            re.IGNORECASE,
        )
        if name_match:
            pharmacy_name = clean_space(name_match.group(1))
            # Supprimer le slash final résiduel
            pharmacy_name = pharmacy_name.rstrip("/ ")
        else:
            # Fallback: tout ce qui est avant le premier "/" ou "-TEL"
            parts = re.split(r"\s*/\s*", raw, maxsplit=1)
            pharmacy_name = clean_space(re.sub(r"^PHCIE\s+", "", parts[0], flags=re.IGNORECASE))
            # Si le nom contient encore un tiret + pharmacien
            pharmacy_name = re.sub(r"\s+[-–]\s+.*$", "", pharmacy_name)

        # Nettoyer le nom
        pharmacy_name = re.sub(r"^\s*[-–/]\s*", "", pharmacy_name)
        pharmacy_name = pharmacy_name.strip("/ ")

        # ── Téléphones ───────────────────────────────────────
        phones = extract_phones(raw)

        # ── Adresse ──────────────────────────────────────────
        # Extraire la partie après le dernier numéro de téléphone
        # Stratégie: chercher le dernier "/" après les téléphones
        addr_raw = raw

        # Localiser la fin des téléphones
        tel_section = re.search(
            r"TEL[.\s]*[\d\s./–-]+",
            addr_raw,
            re.IGNORECASE,
        )
        if tel_section:
            after_tel = addr_raw[tel_section.end():]
            # Supprimer les numéros résiduels en début
            after_tel = re.sub(r"^[\d\s./–-]+", "", after_tel)
            after_tel = re.sub(r"^\s*/\s*", "", after_tel)
            address = clean_space(after_tel)
        else:
            # Pas de TEL: prendre après le 2ème slash
            parts = re.split(r"\s*/\s*", raw)
            address = clean_space(" / ".join(parts[2:])) if len(parts) > 2 else ""

        # Supprimer les numéros de téléphone résiduels
        address = re.sub(r"\b\d{2}[\s./]\d{2}[\s./]\d{2}[\s./]\d{2}(?:[\s./]\d{2})?\b", "", address)
        address = re.sub(r"\b\d{8,10}\b", "", address)
        address = clean_space(address)

        # ── Clé ──────────────────────────────────────────────
        key = self._resolve_key(pharmacy_name, entry.city, address)

        if not pharmacy_name:
            return None

        return ParsedPharmacy(
            pharmacy_key=key,
            pharmacy_name=pharmacy_name,
            city=entry.city,
            address=address,
            phones=phones,
            duty_type=entry.duty_type,
            week_start=entry.week_start,
            week_end=entry.week_end,
            subsection=entry.subsection,
        )

    # ──────────────────────────────────
    # Résolution de clé (référentiel)
    # ──────────────────────────────────

    def _resolve_key(self, name: str, city: str, address: str) -> str:
        """
        Tente de retrouver la pharmacy_key dans le référentiel.
        Si trouvée (score suffisant), réutilise la clé existante.
        Sinon génère une nouvelle clé déterministe.
        """
        new_key = make_pharmacy_key(name, city, address)

        if self.ref_df is None or self.ref_df.empty:
            return new_key

        # Filtrer par ville
        city_mask = self.ref_df["city"].apply(
            lambda c: ascii_upper(str(c)) == ascii_upper(city)
        )
        candidates = self.ref_df[city_mask]

        if candidates.empty:
            return new_key

        best_score = 0
        best_key = new_key
        name_norm = normalize_for_key(name)

        for _, row in candidates.iterrows():
            score = 0
            ref_name = normalize_for_key(str(row.get("pharmacy_name", "")))
            ref_addr = normalize_for_key(str(row.get("address", "")))

            # Similarité nom
            sim_name = SequenceMatcher(None, name_norm, ref_name).ratio()
            score += int(sim_name * 60)

            # Similarité adresse
            if address:
                sim_addr = SequenceMatcher(
                    None, normalize_for_key(address), ref_addr
                ).ratio()
                score += int(sim_addr * 40)

            if score > best_score:
                best_score = score
                best_key = str(row.get("pharmacy_key", new_key))

        # Seuil d'acceptation
        threshold = 45
        if len(candidates) == 1:
            threshold = 10

        if best_score >= threshold:
            return best_key

        return new_key

    # ──────────────────────────────────
    # Orchestration principale
    # ──────────────────────────────────

    def run(self) -> None:
        """Exécute le pipeline ETL complet."""
        print(f"[INFO] Lecture du PDF: {self.pdf_path}")
        lines = self.extract_lines()

        self.detect_period(lines)

        # Séparer les lignes main vs sous-sections
        ss_start_idx = None
        for i, line in enumerate(lines):
            if re.search(r"SOUS SECTION", ascii_upper(line)):
                ss_start_idx = i
                break

        main_lines = lines[:ss_start_idx] if ss_start_idx is not None else lines
        ss_lines = lines[ss_start_idx:] if ss_start_idx is not None else []

        print(f"[INFO] Parsing pages principales ({len(main_lines)} lignes)...")
        self.parse_main_pages(main_lines)

        if ss_lines:
            print(f"[INFO] Parsing sous-sections ({len(ss_lines)} lignes)...")
            self.parse_subsections(ss_lines)

        print(f"[INFO] {len(self.raw_entries)} entrées brutes extraites")

        # Normalisation
        for entry in self.raw_entries:
            parsed = self.normalize_entry(entry)
            if parsed:
                self.pharmacies.append(parsed)

        print(f"[INFO] {len(self.pharmacies)} pharmacies normalisées")

    # ──────────────────────────────────
    # Génération des sorties
    # ──────────────────────────────────

    def build_pharmacies_df(self) -> pd.DataFrame:
        """Construit le DataFrame pharmacies dédupliqué."""
        records = []
        seen_keys: dict[str, dict] = {}

        for p in self.pharmacies:
            key = p.pharmacy_key
            if key not in seen_keys:
                seen_keys[key] = {
                    "pharmacy_key": key,
                    "pharmacy_name": p.pharmacy_name,
                    "city": p.city,
                    "address": p.address,
                    "phones_str": " / ".join(p.phones) if p.phones else "",
                    "phones_json": json.dumps(p.phones, ensure_ascii=False),
                }
            else:
                # Prendre le nom/adresse le plus long (meilleure qualité)
                existing = seen_keys[key]
                if len(p.pharmacy_name) > len(existing["pharmacy_name"]):
                    existing["pharmacy_name"] = p.pharmacy_name
                if len(p.address) > len(existing["address"]):
                    existing["address"] = p.address
                # Fusionner les téléphones
                existing_phones = json.loads(existing["phones_json"])
                for ph in p.phones:
                    if ph not in existing_phones:
                        existing_phones.append(ph)
                existing["phones_str"] = " / ".join(existing_phones)
                existing["phones_json"] = json.dumps(existing_phones, ensure_ascii=False)

        records = list(seen_keys.values())
        df = pd.DataFrame(records)
        if not df.empty:
            df = df.sort_values(["city", "pharmacy_name"]).reset_index(drop=True)
        return df

    def build_duty_periods_df(self) -> pd.DataFrame:
        """Construit le DataFrame des périodes de garde."""
        records = []
        for p in self.pharmacies:
            records.append({
                "pharmacy_key": p.pharmacy_key,
                "pharmacy_name": p.pharmacy_name,
                "city": p.city,
                "start_date": p.week_start.isoformat() if p.week_start else "",
                "end_date": p.week_end.isoformat() if p.week_end else "",
                "duty_type": p.duty_type,
                "source": "UNPPCI",
                "timezone": "Africa/Abidjan",
            })
        df = pd.DataFrame(records)
        if not df.empty:
            df = df.sort_values(["start_date", "city", "pharmacy_name"]).reset_index(drop=True)
        return df

    def build_seed_json(self, ph_df: pd.DataFrame, dp_df: pd.DataFrame) -> dict:
        """Construit le fichier JSON de métadonnées."""
        weeks = []
        if not dp_df.empty:
            for (s, e), grp in dp_df.groupby(["start_date", "end_date"]):
                if s:
                    weeks.append({"start": s, "end": e, "count": len(grp)})

        cities_dist = {}
        if not ph_df.empty:
            for city, cnt in ph_df["city"].value_counts().items():
                cities_dist[city] = int(cnt)

        ref_used = self.reference_path is not None and self.ref_df is not None

        # Calculer le taux de réutilisation des clés
        key_match_ratio = 0.0
        if ref_used and self.ref_df is not None and not ph_df.empty:
            ref_keys = set(self.ref_df["pharmacy_key"].dropna().tolist())
            matched = ph_df["pharmacy_key"].isin(ref_keys).sum()
            key_match_ratio = round(matched / len(ph_df), 3)

        return {
            "source": {
                "name": "UNPPCI",
                "document": f"Tour de Garde Villes de l'Intérieur - {self.month_slug.capitalize()} {self.year}",
                "pdf_file": Path(self.pdf_path).name,
                "generated_at": datetime.now().isoformat(),
            },
            "period": {
                "month": self.month_slug,
                "month_num": self.month_num,
                "year": self.year,
            },
            "stats": {
                "unique_pharmacies": len(ph_df),
                "duty_entries": len(dp_df),
                "weeks_covered": len(weeks),
                "weeks": weeks,
                "cities_distribution": cities_dist,
                "reference_used": ref_used,
                "key_match_ratio": key_match_ratio,
            },
        }

    def save(self, output_dir: str) -> dict[str, str]:
        """Sauvegarde les 3 fichiers de sortie. Retourne les chemins."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        slug = f"{self.month_slug}_{self.year}"
        paths = {
            "pharmacies": out / f"unppci_interieur_pharmacies_{slug}.csv",
            "duty_periods": out / f"unppci_interieur_duty_periods_{slug}.csv",
            "seed": out / f"unppci_interieur_seed_{slug}.json",
        }

        ph_df = self.build_pharmacies_df()
        dp_df = self.build_duty_periods_df()
        seed  = self.build_seed_json(ph_df, dp_df)

        ph_df.to_csv(paths["pharmacies"], index=False, encoding="utf-8-sig")
        dp_df.to_csv(paths["duty_periods"], index=False, encoding="utf-8-sig")
        with open(paths["seed"], "w", encoding="utf-8") as f:
            json.dump(seed, f, ensure_ascii=False, indent=2)

        print(f"\n[✓] Pharmacies uniques  : {len(ph_df)}")
        print(f"[✓] Périodes de garde   : {len(dp_df)}")
        print(f"[✓] Semaines couvertes  : {seed['stats']['weeks_covered']}")
        if seed["stats"].get("reference_used"):
            print(f"[✓] Taux réutilisation clés: {seed['stats']['key_match_ratio']*100:.1f}%")
        print(f"\n[✓] Fichiers sauvegardés:")
        for k, p in paths.items():
            print(f"    {p}")

        return {k: str(v) for k, v in paths.items()}


# ─────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ETL UNPPCI — Pharmacies de garde (Villes de l'Intérieur)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python garde_interieur.py --pdf garde-interieur-fevrier-2026.pdf --output-dir ./output

  python garde_interieur.py \\
      --pdf garde-interieur-mars-2026.pdf \\
      --output-dir ./output \\
      --reference ./output/unppci_interieur_pharmacies_fevrier_2026.csv
        """,
    )
    parser.add_argument("--pdf",         required=True, help="Chemin vers le PDF à parser")
    parser.add_argument("--output-dir",  default="./output", help="Dossier de sortie (défaut: ./output)")
    parser.add_argument("--reference",   default=None, help="CSV référentiel du mois précédent (optionnel)")
    args = parser.parse_args()

    if not Path(args.pdf).exists():
        print(f"[ERREUR] Fichier PDF introuvable: {args.pdf}", file=sys.stderr)
        sys.exit(1)

    etl = InteriorGuardParser(
        pdf_path=args.pdf,
        reference_path=args.reference,
    )
    etl.run()
    etl.save(args.output_dir)


if __name__ == "__main__":
    main()
