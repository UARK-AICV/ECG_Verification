import json

from data_utils import build_runs, get_label_metadata, normalize_lead_name


def runs_to_positions(runs):
    positions = []
    for start, end in runs:
        positions.extend(range(start, end + 1))
    return positions


def update_entry_run(entry, run_index, new_start, new_end):
    runs = build_runs(entry.get("positions", []))
    if 0 <= run_index < len(runs):
        runs[run_index] = (new_start, new_end)
        runs.sort()
        entry["positions"] = runs_to_positions(runs)


def remove_entry_run(entry, run_index):
    runs = build_runs(entry.get("positions", []))
    if 0 <= run_index < len(runs):
        del runs[run_index]
        entry["positions"] = runs_to_positions(runs)


def remove_all_in_lead(sample_data, lead_name):
    sample_data["entries"] = [
        entry for entry in sample_data.get("entries", [])
        if normalize_lead_name(entry.get("lead", "")) != lead_name
    ]


def remove_all_for_label_in_lead(sample_data, lead_name, disease_name):
    sample_data["entries"] = [
        entry
        for entry in sample_data.get("entries", [])
        if not (
            normalize_lead_name(entry.get("lead", "")) == lead_name
            and entry.get("label") == disease_name
        )
    ]


def distribute_runs_uniformly(entry, first_run_index, last_run_index, boxes_between):
    if boxes_between <= 0:
        return

    runs = build_runs(entry.get("positions", []))
    if not runs:
        return

    first_index = min(first_run_index, last_run_index)
    last_index = max(first_run_index, last_run_index)
    if first_index == last_index or not (0 <= first_index < len(runs)) or not (0 <= last_index < len(runs)):
        return

    first_run = runs[first_index]
    last_run = runs[last_index]

    generated = []
    for step in range(1, boxes_between + 1):
        ratio = step / (boxes_between + 1)
        start = round(first_run[0] + (last_run[0] - first_run[0]) * ratio)
        end = round(first_run[1] + (last_run[1] - first_run[1]) * ratio)
        if end <= start:
            end = start + 1
        generated.append((start, end))

    new_runs = runs[: first_index + 1] + generated + runs[last_index:]
    entry["positions"] = runs_to_positions(new_runs)


def persist_sample(sample_file, sample_data):
    sample_data["entries"] = [
        entry for entry in sample_data.get("entries", [])
        if entry.get("positions")
    ]
    with sample_file.open("w", encoding="utf-8") as handle:
        json.dump(sample_data, handle, indent=2)


def create_box(sample_data, lead_name, disease_name, start, end):
    metadata = get_label_metadata(disease_name)
    entries = sample_data.setdefault("entries", [])

    target_entry = None
    for entry in entries:
        if normalize_lead_name(entry.get("lead", "")) == lead_name and entry.get("label") == disease_name:
            target_entry = entry
            break

    if target_entry is None:
        target_entry = {
            "class_order": metadata.get("class_order", -1),
            "lead": lead_name,
            "label": disease_name,
            "positions": [],
        }
        entries.append(target_entry)

    runs = build_runs(target_entry.get("positions", []))
    runs.append((start, end))
    runs.sort()
    target_entry["positions"] = runs_to_positions(runs)
    return target_entry
