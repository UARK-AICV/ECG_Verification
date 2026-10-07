import json
import math

import wfdb
from PySide6.QtGui import QColor

from constants import LABELS_FILE, LEAD_ORDER


def load_label_definitions():
    if not LABELS_FILE.exists():
        return []
    with LABELS_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


LABEL_DEFINITIONS = []
LABEL_METADATA = {}


def reload_label_definitions():
    global LABEL_DEFINITIONS, LABEL_METADATA
    LABEL_DEFINITIONS = load_label_definitions()
    LABEL_METADATA = {item["name"]: item for item in LABEL_DEFINITIONS}
    return LABEL_DEFINITIONS


def get_label_definitions():
    return list(LABEL_DEFINITIONS)


def get_label_metadata(label_name):
    return LABEL_METADATA.get(label_name, {})


def add_label_definition(name, color, abnormal=1):
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Label name cannot be empty.")
    if any(item["name"].casefold() == normalized_name.casefold() for item in LABEL_DEFINITIONS):
        raise ValueError(f'Label "{normalized_name}" already exists.')

    class_order = max((item.get("class_order", -1) for item in LABEL_DEFINITIONS), default=-1) + 1
    new_label = {
        "name": normalized_name,
        "color": color,
        "class_order": class_order,
        "abnormal": abnormal,
    }
    updated_labels = LABEL_DEFINITIONS + [new_label]
    with LABELS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(updated_labels, handle, indent=2)
    reload_label_definitions()
    return new_label


reload_label_definitions()


def discover_sample_files(root):
    return sorted(root.glob("*/*/label.json"))


def build_runs(positions):
    if not positions:
        return []

    runs = []
    start = positions[0]
    prev = positions[0]
    for value in positions[1:]:
        if value == prev + 1:
            prev = value
            continue
        runs.append((start, prev))
        start = prev = value
    runs.append((start, prev))
    return runs


def lead_sort_key(lead):
    try:
        return (LEAD_ORDER.index(lead), lead)
    except ValueError:
        return (len(LEAD_ORDER), lead)


def normalize_lead_name(lead):
    upper = lead.upper()
    if upper == "AVR":
        return "aVR"
    if upper == "AVL":
        return "aVL"
    if upper == "AVF":
        return "aVF"
    return upper


def label_color(label):
    metadata = LABEL_METADATA.get(label)
    if metadata and metadata.get("color"):
        return QColor(metadata["color"])
    hue = sum((index + 1) * ord(char) for index, char in enumerate(label)) % 360
    return QColor.fromHsv(hue, 165, 225)


def group_entries_by_lead(entries):
    grouped = {}
    for entry in entries:
        grouped.setdefault(normalize_lead_name(entry.get("lead", "")), []).append(entry)
    for lead_name in grouped:
        grouped[lead_name].sort(key=lambda item: (item.get("label", ""), item.get("class_order", math.inf)))
    return grouped


def load_sample_bundle(sample_file):
    with sample_file.open("r", encoding="utf-8") as handle:
        sample_data = json.load(handle)

    record_path = sample_file.parent / sample_file.parent.name
    record = wfdb.rdrecord(str(record_path))
    return sample_data, record.p_signal, list(record.sig_name)
