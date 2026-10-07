# ECG Verification

A Python desktop tool for reviewing twelve-lead ECG recordings, editing annotations, and measuring intervals. Built with PySide6 and WFDB.

## Run from source

Create a virtual environment and install the dependencies:

```sh
python -m venv .venv
```

Activate it with `source .venv/bin/activate` on macOS/Linux or `.venv\Scripts\activate` on Windows, then run:

```sh
python -m pip install -r requirements.txt
python main.py
```

## Data layout

The app loads recordings from the `sample` directory beside the source files. One example recording is included.

```text
sample/
├── labels.json
└── group/
    └── record/
        ├── record.hea
        ├── record.dat
        └── label.json
```

WFDB record filenames must match their containing folder name. The current app uses a 500 Hz sample rate. Label definitions live in `sample/labels.json`.

## Review workflow

- Navigate recordings with Previous and Next.
- Open a lead to create, move, resize, or delete annotation spans.
- Toggle label visibility and add custom labels.
- Measure intervals, or use Mark First, Mark Last, and Uniform Fill to distribute annotations.

Annotation changes are saved to the local label files. Keep a backup of recordings and labels before editing.

The `ecg` and `processed` directories, virtual environments, caches, and build output are excluded from Git.
