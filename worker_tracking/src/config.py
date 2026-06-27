"""
config.py
---------
Central configuration for the Worker Detection and Tracking module.
All tunable parameters live here so other modules never need to be
edited for routine adjustments.
"""

import os
from pathlib import Path

# ── Project root (one level above /src) ───────────────────────────────────────
ROOT_DIR: Path = Path(__file__).resolve().parent.parent

# ── Paths ─────────────────────────────────────────────────────────────────────
MODEL_PATH: Path = ROOT_DIR / "models" / "yolov8n.pt"
INPUT_VIDEO_PATH: Path = ROOT_DIR / "input" / "sample_video.mp4"
OUTPUT_VIDEO_PATH: Path = ROOT_DIR / "output" / "tracked_video.mp4"
TRACKING_DATA_PATH: Path = ROOT_DIR / "output" / "tracking_data.json"

# ── Detection settings ─────────────────────────────────────────────────────────
YOLO_PERSON_CLASS_ID: int = 0          # COCO class index for "person"
DETECTION_CONFIDENCE_THRESHOLD: float = 0.40   # Min confidence to keep a detection
DETECTION_IOU_THRESHOLD: float = 0.45          # NMS IoU threshold

# ── ByteTrack / tracker settings ──────────────────────────────────────────────
# These are forwarded verbatim to ultralytics' tracker config.
# Increasing track_buffer keeps IDs alive longer during occlusions.
TRACKER_CONFIG: dict = {
    "tracker_type": "bytetrack",
    "track_high_thresh": 0.50,   # High-confidence detection threshold
    "track_low_thresh": 0.10,    # Low-confidence detection threshold (byte association)
    "new_track_thresh": 0.60,    # Threshold to initialise a new track
    "track_buffer": 30,          # Frames to keep a lost track alive
    "match_thresh": 0.80,        # IoU matching threshold for association
}

# ── Video output settings ──────────────────────────────────────────────────────
OUTPUT_CODEC: str = "mp4v"        # FourCC codec for cv2.VideoWriter
OUTPUT_FPS: float | None = None   # None → inherit FPS from input video

# ── Visualisation settings ────────────────────────────────────────────────────
# BGR colour for bounding-box and label overlay
BOX_COLOR: tuple[int, int, int] = (0, 255, 0)        # Green
TEXT_COLOR: tuple[int, int, int] = (255, 255, 255)   # White
FPS_TEXT_COLOR: tuple[int, int, int] = (0, 200, 255) # Amber
BOX_THICKNESS: int = 2
FONT_SCALE: float = 0.55
FONT_THICKNESS: int = 1
LABEL_PADDING: int = 4   # pixels of padding inside the label background rect

# ── Performance ───────────────────────────────────────────────────────────────
# Set to True to skip frames and boost throughput (halves processing load).
FRAME_SKIP: bool = False
FRAME_SKIP_INTERVAL: int = 2   # Process every Nth frame when FRAME_SKIP=True

# Ensure output directory exists at import time
os.makedirs(ROOT_DIR / "output", exist_ok=True)

