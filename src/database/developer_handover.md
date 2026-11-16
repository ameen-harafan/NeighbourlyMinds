# Student 3 — Iteration 1 Developer Handover

## Acceptance Criterion

**AC 2.1.1 — Dynamic 2D Contrast Slider Adjuster**

The user changes the wall-to-frame colours in the conceptual room explorer and receives simple contrast feedback.

## Data Science output

Student 3 supplies:
1. the digital contrast formula;
2. a reusable Python calculation module;
3. badge logic;
4. test cases and expected results;
5. threshold evidence;
6. limitations and safe wording.

## Integration contract

### Inputs
Two digital sRGB HEX colours:

```json
{
  "wall_colour": "#F5F5F5",
  "frame_colour": "#505050"
}
```

### Calculation
Call:

```python
from contrast_calculator import evaluate_pair

result = evaluate_pair("#F5F5F5", "#505050")
```

### Suggested API-style output

```json
{
  "wall_colour": "#F5F5F5",
  "frame_colour": "#505050",
  "contrast_ratio": 7.49,
  "badge": "Improved contrast",
  "measurement_type": "digital_srgb_contrast",
  "disclaimer": "Conceptual digital contrast only; not measured material LRV."
}
```

### Badge rule

```text
contrast ratio < 3.0  => Low contrast
contrast ratio >= 3.0 => Improved contrast
```

Do not round a value such as 2.995 to 3.00 and mark it as passing. Compare the unrounded calculation against the threshold.

## Frontend behaviour

When the slider changes:
1. update the SVG wall/frame colour;
2. pass the current HEX values to the contrast function/API;
3. receive the calculated ratio and badge;
4. update the badge in real time;
5. keep the limitation message visible or readily accessible.

## Recommended UI copy

**Badge:**
- Low contrast
- Improved contrast

**Short helper text:**
"Digital contrast demonstration"

**Limitation:**
"This prototype demonstrates screen colour contrast and does not measure the Light Reflectance Value (LRV) of real paint or materials."

## Do not display

- "Safe"
- "Unsafe"
- "30% LRV achieved"
- "Complies with AS 1428.1"
- "Dementia-safe"

unless the team later has suitable real-world measurement data and verified compliance logic.

## Test requirement

Before Iteration 1 demo, the developer should run:

```bash
python -m unittest test_contrast_calculator.py
```

Expected result: all tests pass.
