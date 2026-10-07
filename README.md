# ECG Verification

A desktop workspace for clinicians to review twelve-lead ECG recordings and refine candidate anomaly annotations.

## Workflow

1. Segment the ECG into PQRST components.
2. Apply clinical rules to localize candidate anomalous regions and generate pseudo-labels.
3. Review the candidates in ECG Verification: move or resize bounding boxes, add or remove annotations, and assign anomaly types.

The desktop app supports the clinician review stage; segmentation and rule-based localization produce its input annotations.

[Explore the project and interactive demo](https://uark-aicv.github.io/ECG_Verification/).

## Run

In an activated Python virtual environment:

```sh
python -m pip install -r requirements.txt
python main.py
```

Keep recordings and annotations in `sample/`, with `labels.json` and `group/record/` folders containing matching WFDB `.hea`, `.dat`, and `label.json` files. Edits are saved to the annotation files.

## Citation

If you use this tool, cite the repository:

> *ECG Verification* [Software]. https://github.com/UARK-AICV/ECG_Verification

```bibtex
@misc{ecg_verification,
  title = {ECG Verification},
  howpublished = {Software repository},
  url = {https://github.com/UARK-AICV/ECG_Verification},
  note = {Include the commit hash or release version used}
}
```
