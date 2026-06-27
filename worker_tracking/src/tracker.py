"""
tracker.py
----------
Integrates ByteTrack (via ultralytics) to assign persistent IDs to detected workers.

Design
~~~~~~
Ultralytics already ships ByteTrack as a built-in tracker that works directly
with model.track().  We expose it through a thin WorkerTracker wrapper so the
rest of the project stays decoupled from the tracker implementation detail.

Responsibilities
~~~~~~~~~~~~~~~~
* Accept a raw BGR frame.
* Run detection + tracking in a single model.track() call.
* Map each track result to a TrackedWorker object that carries the worker ID,
  bounding box, and confidence score.
* Maintain a frame-level result list ready for export to JSON.

Integration note for the Pose Estimation module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The public output of this class is a list[TrackedWorker] per frame.
Each TrackedWorker has:
    .worker_id  : int   — unique persistent ID
    .bbox       : list[int] — [x1, y1, x2, y2]
    .confidence : float

The frame-level structure matches the JSON schema documented in the README and
expected by the MediaPipe Pose module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from src.config import (
    DETECTION_CONFIDENCE_THRESHOLD,
    DETECTION_IOU_THRESHOLD,
    MODEL_PATH,
    TRACKER_CONFIG,
    YOLO_PERSON_CLASS_ID,
)

logger = logging.getLogger(__name__)


# ── Data transfer object ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class TrackedWorker:
    """
    One tracked worker in a single video frame.

    Attributes
    ----------
    worker_id : int
        Persistent ID assigned by ByteTrack.  Stable across frames as long as
        the track is not lost for longer than ``track_buffer`` frames.
    bbox : list[int]
        Bounding box [x1, y1, x2, y2] in absolute pixel coordinates.
    confidence : float
        YOLOv8 detection confidence for this track in this frame.
    """
    worker_id: int
    bbox: list[int]
    confidence: float

    def to_dict(self) -> dict:
        """
        Serialise to a JSON-compatible dict.

        Returns
        -------
        dict
            ``{"id": int, "bbox": [x1,y1,x2,y2], "confidence": float}``
        """
        return {
            "id": self.worker_id,
            "bbox": self.bbox,
            "confidence": round(self.confidence, 4),
        }


# ── Tracker class ──────────────────────────────────────────────────────────────

class WorkerTracker:
    """
    Runs YOLOv8 detection + ByteTrack association on each frame.

    The tracker is stateful: it maintains ByteTrack's internal track table
    between successive track() calls.  Always call track() with consecutive
    frames to preserve ID continuity.

    Parameters
    ----------
    model_path : Path, optional
        Path to YOLOv8 weights.
    confidence_threshold : float, optional
        Minimum detection confidence forwarded to YOLO.
    iou_threshold : float, optional
        NMS IoU threshold forwarded to YOLO.
    """

    def __init__(
        self,
        model_path: Path = MODEL_PATH,
        confidence_threshold: float = DETECTION_CONFIDENCE_THRESHOLD,
        iou_threshold: float = DETECTION_IOU_THRESHOLD,
    ) -> None:
        self._confidence_threshold = confidence_threshold
        self._iou_threshold = iou_threshold
        self._model = self._load_model(model_path)

        # Runtime state
        self._frame_count: int = 0

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _load_model(model_path: Path) -> YOLO:
        """Load YOLOv8 from disk; produce an actionable error if missing."""
        resolved = model_path.resolve()
        if not resolved.exists():
            raise FileNotFoundError(
                f"YOLOv8 model not found at '{resolved}'.\n"
                "Run:  from ultralytics import YOLO; YOLO('yolov8n.pt')\n"
                "then copy yolov8n.pt into the models/ directory."
            )
        logger.info("WorkerTracker — loading model from '%s'", resolved)
        return YOLO(str(resolved))

    @staticmethod
    def _build_tracker_yaml(cfg: dict) -> str:
        """
        Write a temporary YAML file with ByteTrack settings and return its path.

        ultralytics' model.track() accepts a tracker config YAML path.
        We build one programmatically so the user never has to edit YAML by hand.
        """
        import tempfile, yaml  # yaml is bundled with ultralytics (PyYAML)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as fh:
            yaml.dump(cfg, fh)
            return fh.name

    # ── Public interface ───────────────────────────────────────────────────────

    def track(self, frame: np.ndarray) -> list[TrackedWorker]:
        """
        Detect and track persons in one BGR video frame.

        Parameters
        ----------
        frame : np.ndarray
            BGR image from ``cv2.VideoCapture.read()``.

        Returns
        -------
        list[TrackedWorker]
            All workers visible in this frame, each with a persistent ID.
            Returns an empty list for blank or None frames.
        """
        if frame is None or frame.size == 0:
            logger.warning("track() received an empty frame — skipping.")
            return []

        self._frame_count += 1

        # model.track() runs detection + ByteTrack association internally.
        # persist=True is critical: it tells ultralytics to keep the tracker
        # state between consecutive calls (do not reset between frames).
        raw_results = self._model.track(
            source=frame,
            conf=self._confidence_threshold,
            iou=self._iou_threshold,
            classes=[YOLO_PERSON_CLASS_ID],
            tracker="bytetrack.yaml",   # Built-in ByteTrack config shipped with ultralytics
            persist=True,               # ← maintains track table across calls
            verbose=False,
            stream=False,
        )

        tracked_workers: list[TrackedWorker] = []

        for result in raw_results:
            if result.boxes is None:
                continue

            boxes = result.boxes

            # boxes.id is None when ByteTrack has not yet assigned IDs
            # (can happen on the very first frame before association stabilises)
            if boxes.id is None:
                logger.debug("Frame %d: no track IDs assigned yet.", self._frame_count)
                continue

            for box, track_id, conf in zip(
                boxes.xyxy, boxes.id, boxes.conf
            ):
                x1, y1, x2, y2 = box.tolist()
                worker = TrackedWorker(
                    worker_id=int(track_id),
                    bbox=[int(x1), int(y1), int(x2), int(y2)],
                    confidence=float(conf),
                )
                tracked_workers.append(worker)

        logger.debug(
            "Frame %d: %d tracked worker(s).",
            self._frame_count,
            len(tracked_workers),
        )
        return tracked_workers

    @property
    def frame_count(self) -> int:
        """Total number of frames processed since initialisation."""
        return self._frame_count

    @property
    def model(self) -> YOLO:
        """Expose underlying YOLO model for downstream integration."""
        return self._model
