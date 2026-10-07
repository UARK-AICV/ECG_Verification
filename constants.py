from pathlib import Path
import sys


if getattr(sys, "frozen", False):
    executable = Path(sys.executable).resolve()
    app_bundle = next((parent for parent in executable.parents if parent.suffix == ".app"), None)
    APP_ROOT = app_bundle.parent if app_bundle else executable.parent
else:
    APP_ROOT = Path(__file__).resolve().parent

PROCESSED_ROOT = APP_ROOT / "sample"
LABELS_FILE = PROCESSED_ROOT / "labels.json"
LEAD_ORDER = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
SAMPLE_RATE = 500
