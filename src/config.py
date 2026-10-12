"""Project configuration: data source, paths, time zone, split sizes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = ROOT / "reports"

# Source dataset, pinned to one commit so every run sees identical input.
# https://github.com/Vadimkin/ukrainian-air-raid-sirens-dataset
DATASET_REPO = "Vadimkin/ukrainian-air-raid-sirens-dataset"
DATASET_COMMIT = "d10c80fa696bab42822b9f05b423fc8a30e79d20"
DATASET_COMMIT_TIME_UTC = "2026-10-12T05:05:17Z"
OFFICIAL_FILE = "datasets/official_data_en.csv"
VOLUNTEER_FILE = "datasets/volunteer_data_en.csv"

TZ = "Europe/Kyiv"

# Chronological split sizes in days: train < validation < test.
TEST_DAYS = 56
VAL_DAYS = 56
