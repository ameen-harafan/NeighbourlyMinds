# NeighbourlyMinds — Student 3 Iteration 1 Package

## Owner
Student 3 — Contrast Calculation and Testing

## Scope
AC 2.1.1 — Dynamic 2D Contrast Slider Adjuster

## Files

- `contrast_calculator.py` — production-style digital contrast functions
- `test_contrast_calculator.py` — automated unit tests
- `contrast_test_cases.csv` — handover test matrix with expected results
- `threshold_evidence.md` — digital vs physical contrast evidence and limitation
- `developer_handover.md` — implementation contract for the IT team
- `Student3_Iteration1_Contrast_Notebook.ipynb` — runnable explanation/demo notebook

## Run

From this folder:

```bash
python contrast_calculator.py
python -m unittest test_contrast_calculator.py
```

## Iteration 1 decision

The prototype uses W3C sRGB digital contrast ratio for its on-screen demonstration.

Feedback:
- `< 3:1` → `Low contrast`
- `>= 3:1` → `Improved contrast`

The 30% physical doorway luminance-contrast concept is documented separately but is **not** calculated from screen RGB values.

## Key limitation

This is a conceptual digital contrast demonstration. It is not a physical Light Reflectance Value (LRV) measurement or a building-compliance certification.
