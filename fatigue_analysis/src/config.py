"""
config.py
---------
Central configuration for Module 3: Fatigue Analysis and Ergonomic Risk Assessment.
All thresholds, weights, and paths live here — no magic numbers anywhere else.
"""

from __future__ import annotations
import os
from pathlib import Path

# ── Project root ───────────────────────────────────────────────────────────────
ROOT_DIR: Path = Path(__file__).resolve().parent.parent

# ── Input / Output paths ───────────────────────────────────────────────────────
POSE_DATA_PATH: Path        = ROOT_DIR / "input"  / "pose_data.json"
FATIGUE_REPORT_PATH: Path   = ROOT_DIR / "output" / "fatigue_report.json"
ERGONOMIC_SCORES_PATH: Path = ROOT_DIR / "output" / "ergonomic_scores.json"

# ── Video / frame assumptions ──────────────────────────────────────────────────
# Used to convert frame counts to seconds when actual FPS is unavailable.
ASSUMED_FPS: float = 30.0

# ── Angle thresholds (degrees) ─────────────────────────────────────────────────
# Neck angle (nose → shoulder-center → hip-center)
NECK_ANGLE_LOW:    float = 20.0   # < 20°      → low risk
NECK_ANGLE_MEDIUM: float = 45.0   # 20° – 45°  → medium risk   > 45° → high

# Back / trunk angle (shoulder-center → hip-center → knee-center)
BACK_ANGLE_LOW:    float = 20.0
BACK_ANGLE_MEDIUM: float = 60.0

# Knee flexion angle (hip → knee → ankle)
KNEE_ANGLE_LOW:    float = 30.0
KNEE_ANGLE_MEDIUM: float = 60.0

# Shoulder elevation angle (elbow → shoulder → hip)
SHOULDER_ANGLE_LOW:    float = 20.0
SHOULDER_ANGLE_MEDIUM: float = 60.0

# ── Fatigue feature thresholds ─────────────────────────────────────────────────
# "Bending" = back angle exceeds this value (degrees)
BENDING_ANGLE_THRESHOLD: float = 20.0

# "Forward lean" = neck angle exceeds this value
FORWARD_LEAN_THRESHOLD: float = 20.0

# Static posture: worker is "static" when the mean per-frame angle change
# across all joints falls below this value (degrees/frame)
STATIC_POSTURE_DELTA_THRESHOLD: float = 2.0

# Repetitive motion: a new repetition is counted each time the back-angle
# signal crosses BENDING_ANGLE_THRESHOLD, provided at least this many
# frames have passed since the last crossing.
REPETITION_MIN_GAP_FRAMES: int = 15

# A "posture change" is registered when back angle shifts by more than
# this many degrees between consecutive frames.
POSTURE_CHANGE_THRESHOLD: float = 10.0

# Max expected repetitions in a session (used for normalisation to 0–100)
MAX_EXPECTED_REPETITIONS: int = 200

# ── Fatigue score weights (must sum to 1.0) ────────────────────────────────────
FATIGUE_WEIGHTS: dict[str, float] = {
    "bending_ratio":        0.25,  # fraction of frames spent bending
    "forward_lean_ratio":   0.15,  # fraction of frames leaning forward
    "static_posture_ratio": 0.20,  # fraction of frames in static posture
    "repetitive_motion":    0.20,  # normalised repetition count
    "posture_change_rate":  0.10,  # posture changes per frame (normalised)
    "max_back_angle":       0.10,  # peak back angle / 90°  (capped at 1.0)
}

# ── Fatigue score bands ────────────────────────────────────────────────────────
FATIGUE_LOW_MAX:    int = 30   # 0–30   → Low Fatigue
FATIGUE_MEDIUM_MAX: int = 70   # 31–70  → Moderate Fatigue  >70 → High

# ── Ergonomic risk score weights (must sum to 1.0) ────────────────────────────
ERGONOMIC_WEIGHTS: dict[str, float] = {
    "neck_score":     0.25,
    "back_score":     0.35,
    "knee_score":     0.20,
    "shoulder_score": 0.20,
}

# ── Risk level bands (ergonomic composite score 0–100) ────────────────────────
RISK_LOW_MAX:    int = 33
RISK_MEDIUM_MAX: int = 66

# ── Alert threshold ────────────────────────────────────────────────────────────
# Alert is raised when fatigue score OR ergonomic score exceeds this value.
ALERT_THRESHOLD: int = 70

# Ensure output directory exists on import
os.makedirs(ROOT_DIR / "output", exist_ok=True)
