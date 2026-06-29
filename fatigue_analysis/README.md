# Module 3 — Fatigue Analysis and Ergonomic Risk Assessment

Part of the **AI-based Worker Fatigue and Ergonomic Risk Assessment** final-year project.

Consumes `pose_data.json` from Module 2 and produces two JSON files for Module 4 (Dashboard).

| Input | Source |
|---|---|
| `input/pose_data.json` | Module 2 output |

| Output | Consumer |
|---|---|
| `output/fatigue_report.json` | Module 4 Dashboard |
| `output/ergonomic_scores.json` | Module 4 Dashboard |

---

## Folder Structure

```
fatigue_analysis/
├── input/
│   └── pose_data.json          ← copy from Module 2 output/
├── output/
│   ├── fatigue_report.json     ← auto-created
│   └── ergonomic_scores.json   ← auto-created
├── src/
│   ├── __init__.py
│   ├── config.py               ← all thresholds and weights
│   ├── angle_calculator.py     ← joint angle geometry
│   ├── ergonomic_analyzer.py   ← REBA-inspired risk scoring
│   ├── fatigue_detector.py     ← feature extraction + fatigue score
│   ├── risk_classifier.py      ← unified WorkerReport
│   └── json_exporter.py        ← writes output JSON files
├── main.py
├── requirements.txt
└── README.md
```

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## How to Run

```bash
# Copy Module 2 output
cp ../pose_estimation/output/pose_data.json input/

# Run
python main.py
```

Optional environment-variable overrides:
```bash
POSE_JSON=input/my_pose.json \
VIDEO_FPS=25 \
python main.py
```

---

## Mathematical Formulas

### Joint Angle (all angles use this formula)

Given three points **A** (proximal), **B** (vertex/joint), **C** (distal):

```
BA = A - B
BC = C - B

cos θ = (BA · BC) / (|BA| × |BC|)
θ = arccos(cos θ)          [degrees, range 0°–180°]

deviation = |180° - θ|     [0° = neutral posture]
```

### Specific Joints

| Angle | A | B (vertex) | C |
|---|---|---|---|
| Neck flexion | nose | shoulder-midpoint | hip-midpoint |
| Back/trunk flexion | shoulder-midpoint | hip-midpoint | knee-midpoint |
| Knee flexion | hip | knee | ankle |
| Shoulder elevation | elbow | shoulder | hip |

All deviations are reported as **degrees from neutral (180°)**, so 0° = fully upright.

---

## Fatigue Score (0–100)

Six features are extracted from the per-frame angle time-series:

| Feature | Description | Weight |
|---|---|---|
| `bending_ratio` | Fraction of frames where back angle > 20° | 0.25 |
| `forward_lean_ratio` | Fraction of frames where neck angle > 20° | 0.15 |
| `static_posture_ratio` | Fraction of frames in static posture | 0.20 |
| `repetitive_motion` | Bending repetitions / 200 | 0.20 |
| `posture_change_rate` | Posture changes / total frames | 0.10 |
| `max_back_angle` | Peak back angle / 90° | 0.10 |

```
fatigue_score = Σ (weight_i × feature_i) × 100    [clipped to 0–100]
```

| Score | Level |
|---|---|
| 0–30 | Low |
| 31–70 | Moderate |
| 71–100 | High |

---

## Ergonomic Risk Score (0–100)

Each joint angle is mapped to a 0–100 sub-score using piecewise linear interpolation:

```
angle < LOW_THRESHOLD   →  score ∈ [0, 33]    (low risk band)
LOW ≤ angle < MEDIUM    →  score ∈ [33, 66]   (medium risk band)
angle ≥ MEDIUM          →  score ∈ [66, 100]  (high risk band)
```

Default thresholds (configurable in `config.py`):

| Joint | Low threshold | Medium threshold |
|---|---|---|
| Neck | 20° | 45° |
| Back | 20° | 60° |
| Knee | 30° | 60° |
| Shoulder | 20° | 60° |

Composite score:
```
ergonomic_score = 0.35×back + 0.25×neck + 0.20×knee + 0.20×shoulder
```

| Score | Risk Level |
|---|---|
| 0–33 | LOW |
| 34–66 | MEDIUM |
| 67–100 | HIGH |

---

## Sample Output

### `fatigue_report.json`

```json
[
  {
    "worker_id": 1,
    "fatigue_score": 78,
    "fatigue_level": "High",
    "ergonomic_score": 72,
    "ergonomic_risk": "HIGH",
    "overall_risk": "HIGH",
    "alert": true,
    "mean_back_angle": 34.2,
    "mean_neck_angle": 22.1,
    "mean_knee_angle": 15.8,
    "duration_seconds": 120.0,
    "duration_bent_seconds": 68.4,
    "repetitive_motion_count": 24,
    "posture_change_count": 87,
    "summary": "Risk: HIGH | Fatigue: 78/100 (High) | Ergo: 72/100 (HIGH) | ⚠ ALERT"
  }
]
```

### `ergonomic_scores.json`

```json
[
  {
    "worker_id": 1,
    "mean_neck_angle": 22.1,
    "mean_back_angle": 34.2,
    "mean_knee_angle": 15.8,
    "mean_shoulder_angle": 12.5,
    "neck_score": 45.2,
    "back_score": 72.1,
    "knee_score": 18.4,
    "shoulder_score": 30.0,
    "ergonomic_score": 52,
    "risk_level": "MEDIUM",
    "alert": false
  }
]
```

---

## Integration Guide — Module 4 (Dashboard)

### Reading the outputs

```python
import json

with open("output/fatigue_report.json") as f:
    fatigue_reports = json.load(f)

with open("output/ergonomic_scores.json") as f:
    ergo_scores = json.load(f)

# Iterate workers
for report in fatigue_reports:
    worker_id    = report["worker_id"]
    fatigue      = report["fatigue_score"]
    risk         = report["overall_risk"]
    alert        = report["alert"]
    back_angle   = report["mean_back_angle"]

    if alert:
        print(f"⚠ Worker {worker_id} — {risk} RISK | Fatigue: {fatigue}/100")
```

### Key fields for the dashboard

| Field | Type | Use |
|---|---|---|
| `worker_id` | int | Primary key — matches Module 1 track IDs |
| `overall_risk` | "LOW"\|"MEDIUM"\|"HIGH" | Colour-code cards |
| `alert` | bool | Trigger notifications |
| `fatigue_score` | 0–100 | Progress bar / gauge |
| `ergonomic_score` | 0–100 | Progress bar / gauge |
| `mean_back_angle` | float° | Display in worker detail view |
| `duration_bent_seconds` | float | Time-at-risk metric |
| `summary` | str | One-liner for notification text |

---

## Configuration

All parameters in `src/config.py`:

| Parameter | Default | Description |
|---|---|---|
| `ASSUMED_FPS` | 30.0 | Used to convert frames → seconds |
| `BENDING_ANGLE_THRESHOLD` | 20° | Back angle that defines "bending" |
| `BACK_ANGLE_MEDIUM` | 60° | High-risk back angle threshold |
| `ALERT_THRESHOLD` | 70 | Score above which alert=true |
| `FATIGUE_WEIGHTS` | see config | Per-feature fatigue score weights |
| `ERGONOMIC_WEIGHTS` | see config | Per-joint ergonomic score weights |

---

## Team

- **Module 1** — Worker Detection and Tracking (YOLOv8 + ByteTrack)
- **Module 2** — Pose Estimation and Keypoint Extraction (MediaPipe)
- **Module 3** — Fatigue Analysis and Ergonomic Risk Assessment ← *this module*
- **Module 4** — Dashboard and Reporting
