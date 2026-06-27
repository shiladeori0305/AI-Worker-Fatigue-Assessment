# Module 1 — Worker Detection and Tracking

Part of the **AI-based Worker Fatigue and Ergonomic Risk Assessment** final-year project.

This module is self-contained and produces two artefacts consumed by the downstream modules:

| Artefact | Path | Consumer |
|---|---|---|
| Annotated video | `output/tracked_video.mp4` | QA / demo |
| Tracking data | `output/tracking_data.json` | Module 2 (Pose Estimation) |

---

## Folder Structure

```
worker_tracking/
│
├── models/
│   └── yolov8n.pt            ← download once (see Installation)
│
├── input/
│   └── sample_video.mp4      ← place your CCTV footage here
│
├── output/
│   ├── tracked_video.mp4     ← annotated output (auto-created)
│   └── tracking_data.json    ← per-frame tracking data (auto-created)
│
├── src/
│   ├── __init__.py
│   ├── config.py             ← all tunable parameters
│   ├── detector.py           ← YOLOv8 person detection wrapper
│   ├── tracker.py            ← ByteTrack integration + TrackedWorker model
│   └── video_utils.py        ← VideoReader, VideoWriter, FrameAnnotator,
│                                TrackingDataExporter
│
├── main.py                   ← pipeline entry point
├── requirements.txt
└── README.md
```

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `ultralytics` | ≥ 8.2.0 | YOLOv8 model + built-in ByteTrack |
| `opencv-python` | ≥ 4.9.0 | Video I/O and frame drawing |
| `numpy` | ≥ 1.26.0 | Array operations |
| Python | 3.11+ | Type hints, `match`, `Path` |

ByteTrack is bundled inside Ultralytics — no separate install required.

---

## Installation

### 1 — Clone and create a virtual environment

```bash
git clone https://github.com/your-org/worker-fatigue-assessment.git
cd worker-fatigue-assessment/worker_tracking

python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

### 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### 3 — Download the YOLOv8n weights

```python
# Run once from inside the project root
from ultralytics import YOLO
model = YOLO("yolov8n.pt")   # downloads ~6 MB automatically
```

Then move (or copy) the downloaded file:

```bash
mv yolov8n.pt models/yolov8n.pt
```

### 4 — Add your input video

```bash
cp /path/to/your/cctv_clip.mp4 input/sample_video.mp4
```

---

## How to Run

```bash
# From the project root (worker_tracking/)
python main.py
```

### Override paths via environment variables

```bash
INPUT_VIDEO=input/factory_line.mp4 \
OUTPUT_VIDEO=output/factory_tracked.mp4 \
TRACKING_JSON=output/factory_data.json \
python main.py
```

### GPU acceleration

If a CUDA-capable GPU is available, Ultralytics will use it automatically.
No code change is required — only the correct PyTorch CUDA build:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

---

## Configuration

All parameters live in `src/config.py`.  Common adjustments:

| Parameter | Default | Description |
|---|---|---|
| `DETECTION_CONFIDENCE_THRESHOLD` | `0.40` | Min YOLO confidence to keep a detection |
| `DETECTION_IOU_THRESHOLD` | `0.45` | NMS IoU threshold |
| `TRACKER_CONFIG["track_buffer"]` | `30` | Frames to keep a lost track alive (increase for longer occlusions) |
| `TRACKER_CONFIG["track_high_thresh"]` | `0.50` | ByteTrack high-confidence lane threshold |
| `FRAME_SKIP` | `False` | Skip alternate frames for faster processing |

---

## Output

### Annotated Video (`output/tracked_video.mp4`)

Each frame contains:
- **Green bounding box** around every tracked worker
- **Label**: `ID:<n>  <confidence>` (e.g. `ID:3  0.94`)
- **FPS counter** (top-left, amber)
- **Worker count** (below FPS, amber)

### Tracking Data (`output/tracking_data.json`)

```json
[
  {
    "frame": 1,
    "workers": [
      { "id": 1, "bbox": [120, 80, 250, 420], "confidence": 0.95 },
      { "id": 2, "bbox": [430, 70, 560, 410], "confidence": 0.92 }
    ]
  },
  {
    "frame": 2,
    "workers": [
      { "id": 1, "bbox": [122, 81, 252, 421], "confidence": 0.94 }
    ]
  }
]
```

**Field reference:**

| Field | Type | Description |
|---|---|---|
| `frame` | `int` | 1-based frame index |
| `workers[].id` | `int` | Persistent ByteTrack worker ID |
| `workers[].bbox` | `[int, int, int, int]` | `[x1, y1, x2, y2]` absolute pixels |
| `workers[].confidence` | `float` | YOLO detection confidence (4 d.p.) |

---

## Integration Guide — Module 2 (MediaPipe Pose Estimation)

This section explains exactly how another developer can consume this module's output.

### Option A — JSON file handoff (recommended for decoupled development)

Module 2 reads `output/tracking_data.json` produced by this module.

```python
import json
import cv2
import mediapipe as mp

# Load tracking data from Module 1
with open("output/tracking_data.json") as f:
    tracking_data = json.load(f)

cap = cv2.VideoCapture("input/sample_video.mp4")
pose = mp.solutions.pose.Pose()

for record in tracking_data:
    frame_idx = record["frame"]

    # Seek to the corresponding frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx - 1)
    ret, frame = cap.read()
    if not ret:
        continue

    for worker in record["workers"]:
        worker_id = worker["id"]
        x1, y1, x2, y2 = worker["bbox"]

        # Crop the worker region for pose estimation
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        pose_results = pose.process(rgb_crop)

        # pose_results.pose_landmarks now contains the 33 keypoints
        # for worker `worker_id` in frame `frame_idx`
```

### Option B — Real-time pipeline integration

Import `WorkerTracker` and `TrackedWorker` directly into Module 2's pipeline loop:

```python
from src.tracker import WorkerTracker, TrackedWorker

tracker = WorkerTracker()   # initialise once

# Inside your frame loop:
tracked_workers: list[TrackedWorker] = tracker.track(frame)

for worker in tracked_workers:
    # worker.worker_id  → persistent int ID
    # worker.bbox       → [x1, y1, x2, y2]
    # worker.confidence → float
    x1, y1, x2, y2 = worker.bbox
    crop = frame[y1:y2, x1:x2]
    # → pass crop to MediaPipe Pose
```

### Key integration rules

1. **Never reset the tracker between frames** — `tracker.track()` maintains ByteTrack's internal state; call it once per frame in sequence.
2. **Worker IDs are stable but not gapless** — IDs are integers starting from 1 and count upward; they are not necessarily 1, 2, 3… if earlier tracks were lost.
3. **Empty frames are safe** — `tracker.track()` returns an empty list for blank/corrupt frames rather than raising an exception.
4. **Coordinate system** — all bounding boxes are in absolute pixel coordinates matching the original video resolution.  If Module 2 resizes frames, scale the bbox accordingly.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `FileNotFoundError: YOLOv8 model not found` | `models/yolov8n.pt` missing | Run the one-liner in Installation §3 |
| `FileNotFoundError: Input video not found` | Wrong path | Update `INPUT_VIDEO_PATH` in `config.py` or set `INPUT_VIDEO` env var |
| IDs reset every frame | `persist=True` missing in tracker call | Ensure you use the provided `WorkerTracker.track()` — do not call `model.predict()` directly |
| Very low FPS | CPU-only inference | Install CUDA PyTorch build; or enable `FRAME_SKIP=True` in `config.py` |
| Workers not detected | Low confidence / occlusion | Lower `DETECTION_CONFIDENCE_THRESHOLD` in `config.py` |
| IDs flicker on reappearance | `track_buffer` too small | Increase `TRACKER_CONFIG["track_buffer"]` (e.g. to 60) |

---

## Team

Built as **Module 1** of a 4-module final-year project.  
Downstream modules: Pose Estimation (Module 2), Fatigue Feature Extraction (Module 3), Risk Scoring + Dashboard (Module 4).
