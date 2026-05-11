"""Central configuration for the euro_sdt pipeline.

All paths, URLs, and constants referenced across scripts live here.
Override values via environment variables where supported.
"""

import os
from pathlib import Path

# ── Project root ────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ── Database ────────────────────────────────────────────────────────────────

DB_PATH = str(PROJECT_ROOT / "euro_sdt.db")

# ── Data directories ────────────────────────────────────────────────────────

SOURCES_DIR = str(PROJECT_ROOT / "sources")
WIKI_DIR = str(PROJECT_ROOT / "sources" / "wikipedia")
DG_CV_DIR = str(PROJECT_ROOT / "sources" / "dg_cvs")
DECLARATIONS_DIR = str(PROJECT_ROOT / "sources" / "declarations")
CJEU_DIR = str(PROJECT_ROOT / "sources" / "cjeu")
REVOLVING_DOOR_DIR = str(PROJECT_ROOT / "sources" / "revolving_door")
EP_HEARINGS_DIR = str(PROJECT_ROOT / "sources" / "ep_hearings")
ORG_SITES_DIR = str(PROJECT_ROOT / "sources" / "org_sites")
ENTITIES_MD_DIR = str(PROJECT_ROOT / "sources" / "entities_md")

MANIFEST_DIR = str(PROJECT_ROOT / "manifests")
PAPERS_DIR = str(PROJECT_ROOT / "papers")
WIKI_OUTPUT_DIR = str(PROJECT_ROOT / "wiki")
WIKI_IMG_DIR = str(PROJECT_ROOT / "wiki" / "img")

# ── DeepSeek API ────────────────────────────────────────────────────────────

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-pro"
DEEPSEEK_MAX_TOKENS = 800
DEEPSEEK_TEMPERATURE = 0.0
LLM_WORKERS = 4

# ── Wikidata / Wikipedia ────────────────────────────────────────────────────

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
WIKIDATA_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"

# ── Commission URLs ─────────────────────────────────────────────────────────

COMMISSION_WIKI_PAGES = {
    "santer": "https://en.wikipedia.org/wiki/Santer_Commission",
    "prodi": "https://en.wikipedia.org/wiki/Prodi_Commission",
    "barroso_i": "https://en.wikipedia.org/wiki/Barroso_Commission_I",
    "barroso_ii": "https://en.wikipedia.org/wiki/Barroso_Commission_II",
    "juncker": "https://en.wikipedia.org/wiki/Juncker_Commission",
    "vdl_i": "https://en.wikipedia.org/wiki/Von_der_Leyen_Commission_I",
    "vdl_ii": "https://en.wikipedia.org/wiki/Von_der_Leyen_Commission_II",
}

CJEU_URL = "https://www.curia.europa.eu/jcms/jcms/Jo2_7026/en/"

# ── Data directories ─────────────────────────────────────────────────────────

DATA_DIR = str(PROJECT_ROOT / "data")

# ── Input CSV/JSON files ────────────────────────────────────────────────────

MEP_LIST_CSV = str(PROJECT_ROOT / "data" / "meps_2024_2029.csv")
MEP_CV_CSV = str(PROJECT_ROOT / "data" / "cvs" / "mep_cv_data.csv")
COMMISSION_CV_CSV = str(PROJECT_ROOT / "data" / "cvs" / "commission_cv_data.csv")
COMMISSION_2024_2029_CSV = str(PROJECT_ROOT / "data" / "commissions" / "commission_2024_2029.csv")
AFFILIATIONS_CSV = str(PROJECT_ROOT / "data" / "affiliations" / "commission_affiliations.csv")
ORG_CLASSIFIED_CSV = str(PROJECT_ROOT / "data" / "affiliations" / "organisations_classified.csv")
DG_CVS_CSV = str(PROJECT_ROOT / "data" / "officials" / "commission_dg_cvs.csv")
EDU_BY_COUNTRY_CSV = str(PROJECT_ROOT / "data" / "analysis" / "commissioner_education_by_country.csv")
REVOLVING_DOOR_CSV = str(PROJECT_ROOT / "data" / "affiliations" / "commission_revolving_door.csv")
SENIOR_OFFICIALS_CSV = str(PROJECT_ROOT / "data" / "officials" / "commission_senior_officials.csv")
ATLANTICIST_CSV = str(PROJECT_ROOT / "data" / "analysis" / "atlanticist_comparison.csv")
CJEU_MEMBERS_CSV = str(PROJECT_ROOT / "data" / "cjeu" / "cjeu_members_list.csv")
TRANSNATIONAL_COMPANIES_CSV = str(PROJECT_ROOT / "data" / "corporate" / "transnational_companies.csv")

DOI_ZIP = str(PROJECT_ROOT / "Machine-Readable-DOIs.zip")
CJEU_BIOS_JSON = str(PROJECT_ROOT / "cjeu_bios_full.json")
JUNCKER_WIKI_JSON = str(PROJECT_ROOT / "commission_juncker_wiki_texts.json")

MANIFEST_INDEX = str(PROJECT_ROOT / "manifests" / "_index.json")
MANIFEST_DEDUP = str(PROJECT_ROOT / "manifests" / "_dedup.json")
EDU_DEDUP_JSON = str(PROJECT_ROOT / "manifests" / "_edu_dedup.json")
SOURCE_MANIFEST = str(PROJECT_ROOT / "sources" / "manifest.json")

VERIFICATION_REPORT_CSV = str(PROJECT_ROOT / "data" / "verification_report.csv")
VERIFICATION_CACHE_JSON = str(PROJECT_ROOT / "verification_cache.json")

# ── Validation ──────────────────────────────────────────────────────────────

BLACKLIST_PATTERNS = [
    r"\beuropean\s+commission\b",
    r"\beuropean\s+parliament\b",
    r"\bcouncil\s+of\s+the\s+european\s+union\b",
    r"\beuropean\s+union\b",
    r"\bunited\s+nations\b",
    r"\beuropean\s+council\b",
    r"\beuropean\s+cen?tral\s+bank\b",
    r"\bcjue\b",
    r"\bcourt\s+of\s+justice\b",
    r"\bnato\b(?!\s*foundation|\s*trust|\s*parliamentary)",
    r"\bwto\b",
    r"\bimf\b",
    r"\bworld\s+bank\b",
    r"\bwho\b",
    r"\boecd\b",
    r"\bthe\s+commission\b",
    r"\bcommission\s+of\s+the\s+european\s+communities\b",
    r"\bhigh\s+authority\b.*\becsc\b",
    r"\bcouncil\s+of\s+ministers\b",
    r"\beuropean\s+community\b",
    r"\bec\b.*\bcommission\b",
    r"\beuropean\s+economic\s+community\b",
]
