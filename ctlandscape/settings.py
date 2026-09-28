"""Project settings. Change CONDITION to run the same analysis on another indication."""

from pathlib import Path

CONDITION = "non-small cell lung cancer"

# Analysis window for time-trend charts (by trial start year).
FIRST_YEAR = 2010

API_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 1000          # API maximum
PAUSE_SECONDS = 0.25      # between pages
TIMEOUT_SECONDS = 90
USER_AGENT = "nsclc-trial-landscape/1.0 (academic portfolio project; python-requests)"

# Only the fields the analysis uses. Keeps each page small.
FIELDS = [
    "NCTId", "BriefTitle", "OverallStatus", "WhyStopped",
    "StartDate", "StartDateType", "CompletionDate", "CompletionDateType",
    "StudyType", "Phase", "EnrollmentCount",
    "LeadSponsorName", "LeadSponsorClass",
    "InterventionType", "InterventionName",
    "LocationCountry",
]

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
FIG_DIR = ROOT / "figures"
REPORT_DIR = ROOT / "reports"
RAW_FILE = DATA_DIR / "raw_studies.json"
META_FILE = DATA_DIR / "fetch_meta.json"
CLEAN_FILE = DATA_DIR / "trials_clean.csv"
