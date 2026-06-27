"""
config.py
---------
Central configuration for Module 2: Pose Estimation and Keypoint Extraction.

All tunable parameters are defined here.  No other file should hard-code
paths, thresholds, or visual constants — import them from here instead.
"""

from __future__ import annotations
import os
from pathlib import Path

# ── Project root (one level above /src) ───────────────────────────────────────
ROOT_DIR: Path = Path(__file__).resolve().parent.parent

# ── Input paths (produced by Module 1) ────────────────────────────────────────
INPUT_VIDEO_PATH: Path   = ROOT_DIR / "input" / "tracked_video.mp4"
TRACKING_DATA_PATH: Path = ROOT_DIR / "input" / "tracking_data.json"

# ── Output paths ───────────────────────────────────────────────────────────────
OUTPUT_VIDEO_PATH: Path = ROOT_DIR / "output" / "pose_video.mp4"
POSE_DATA_PATH: Path    = ROOT_DIR / "output" / "pose_data.json"

# ── MediaPipe Pose settings ────────────────────────────────────────────────────
MP_STATIC_IMAGE_MODE: bool          = False
MP_MODEL_COMPLEXITY: int            = 1       # 0=Lite  1=Full  2=Heavy
MP_SMOOTH_LANDMARKS: bool           = True
MP_ENABLE_SEGMENTATION: bool        = False
MP_SMOOTH_SEGMENTATION: bool        = False
MP_MIN_DETECTION_CONFIDENCE: float  = 0.50
MP_MIN_TRACKING_CONFIDENCE: float   = 0.50

# ── Bounding-box safety margin ─────────────────────────────────────────────────
# Expand each worker bbox by this many pixels before cropping.
# Gives MediaPipe a bit of context around body edges.
BBOX_PADDING: int = 20

# ── Skeleton visualisation (BGR) ───────────────────────────────────────────────
LANDMARK_COLOR: tuple[int, int, int]   = (0, 255, 0)
CONNECTION_COLOR: tuple[int, int, int] = (255, 165, 0)
WORKER_ID_COLOR: tuple[int, int, int]  = (255, 255, 255)
LABEL_BG_COLOR: tuple[int, int, int]   = (0, 120, 255)

LANDMARK_RADIUS: int      = 4
CONNECTION_THICKNESS: int = 2
FONT_SCALE: float         = 0.55
FONT_THICKNESS: int       = 1
LABEL_PADDING: int        = 4

# ── Video output ───────────────────────────────────────────────────────────────
OUTPUT_CODEC: str        = "mp4v"
OUTPUT_FPS: float | None = None   # None → inherit from input video

# ── Keypoint visibility threshold ─────────────────────────────────────────────
# Landmarks below this visibility are stored as null and not drawn.
MIN_VISIBILITY: float = 0.50

# ── MediaPipe Pose landmark index → human-readable name ───────────────────────
LANDMARK_NAMES: list[str] = [
    "nose",
    "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear",
    "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_pinky", "right_pinky",
    "left_index", "right_index",
    "left_thumb", "right_thumb",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
]

# Ensure output directory exists at import time
os.makedirs(ROOT_DIR / "output", exist_ok=True)
