import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
DATA_DIR = BASE_DIR / "data"
PROFILE_DIR = BASE_DIR / "browser_profile"
CV_PATH = BASE_DIR / "ATS CV - Nasaruddin.pdf"

# Ensure directories exist
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

# Database
DB_FILE = DATA_DIR / "applied_tracker.json"

# URLs
REVOU_JOB_MATCHING_URL = "https://next.revou.tech/dashboard/quality-application/job-matching"
REVOU_APPLICATION_URL = "https://next.revou.tech/dashboard/quality-application/application"
LINKEDIN_JOBS_URL = "https://www.linkedin.com/jobs/search/"

# Search Target Settings
TARGET_ROLES = [
    "Junior Backend Developer",
    "Junior Software Engineer",
    "Backend Developer",
    "Software Engineer",
    "Junior Full Stack Developer",
    "Node.js Developer",
    "TypeScript Developer"
]

TARGET_COUNTRIES = [
    "Australia",
    "United States",
    "United Kingdom",
    "Germany",
    "Netherlands",
    "Japan",
    "United Arab Emirates",
    "Saudi Arabia",
    "Qatar"
]

# LinkedIn Search query filters
SEARCH_REMOTE = True
SEARCH_EASY_APPLY_ONLY = True  # Can be toggled if user wants external apply
DEFAULT_WEEKLY_LIMIT = 10

# Browser Settings
CHROME_DEBUG_PORT = 9222
HEADLESS = False  # Set False so user can supervise & log in smoothly
PAGE_TIMEOUT = 25  # seconds
HUMAN_DELAY_MIN = 2.0
HUMAN_DELAY_MAX = 5.0
