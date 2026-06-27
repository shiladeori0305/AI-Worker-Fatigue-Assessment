"""
detector.py
-----------
Wraps YOLOv8 person detection.

Responsibilities
~~~~~~~~~~~~~~~~
* Load the YOLOv8 model once at initialisation.
* Accept a raw BGR frame (np.ndarray).
* Return only "person" detections above the configured confidence threshold.
* Expose detections as plain Python objects so the tracker stays decoupled
  from the YOLO internals.

The tracker and visualiser never import ultralytics directly — they only
consume DetectionResult objects produced here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from src.config import (
    DETECTION_CONFIDENCE_THRESHOLD,
    DETECTION_IOU_THRESHOLD,
    MODEL_PATH,
    YOLO_PERSON_CLASS_ID,
)

logger = logging.getLogger(__name__)


# ── Data transfer object ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class DetectionResult:
    """
    A single detected person in one video frame.

    Attributes
    ----------
    bbox : list[int]
        Bounding box as [x1, y1, x2, y2] in absolute pixel coordinates.
    confidence : float
        Detection confidence score in [0, 1].
    """
    bbox: list[int]
    confidence: float

    def to_dict(self) -> dict:
        """Serialise to a JSON-friendly dict (used by the data exporter)."""
        return {"bbox": self.bbox, "confidence": round(self.confidence, 4)}


# ── Detector class ─────────────────────────────────────────────────────────────

class WorkerDetector:
    """
    Detects workers (persons) in video frames using YOLOv8n.

    Parameters
    ----------
    model_path : Path, optional
        Path to the YOLOv8 weights file.  Defaults to ``config.MODEL_PATH``.
    confidence_threshold : float, optional
        Minimum detection confidence.  Defaults to
        ``config.DETECTION_CONFIDENCE_THRESHOLD``.
    iou_threshold : float, optional
        NMS IoU threshold.  Defaults to ``config.DETECTION_IOU_THRESHOLD``.
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

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _load_model(model_path: Path) -> YOLO:
        """Load YOLOv8 weights; raise FileNotFoundError with a clear message."""
        resolved = model_path.resolve()
        if not resolved.exists():
            raise FileNotFoundError(
                f"YOLOv8 model not found at '{resolved}'.\n"
                "Download it by running:\n"
                "    from ultralytics import YOLO; YOLO('yolov8n.pt')\n"
                "and move yolov8n.pt into the models/ folder."
            )
        logger.info("Loading YOLOv8 model from '%s'", resolved)
        model = YOLO(str(resolved))
        logger.info("Model loaded — class names: %s", model.names)
        return model

    # ── Public interface ───────────────────────────────────────────────────────

    def detect(self, frame: np.ndarray) -> list[DetectionResult]:
        """
        Run inference on one BGR frame and return person detections.

        Parameters
        ----------
        frame : np.ndarray
            BGR image as returned by ``cv2.VideoCapture.read()``.

        Returns
        -------
        list[DetectionResult]
            Zero or more detections, each with a bounding box and confidence.
        """
        if frame is None or frame.size == 0:
            logger.warning("detect() called with an empty frame — skipping.")
            return []

        # Run YOLO inference (returns a list of Results objects, one per image)
        raw_results = self._model.predict(
            source=frame,
            conf=self._confidence_threshold,
            iou=self._iou_threshold,
            classes=[YOLO_PERSON_CLASS_ID],  # Only "person"
            verbose=False,                   # Suppress per-frame console spam
            stream=False,
        )

        detections: list[DetectionResult] = []

        for result in raw_results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                # xyxy gives absolute pixel coords as a tensor of shape (1, 4)
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf: float = float(box.conf[0])

                detections.append(
                    DetectionResult(
                        bbox=[int(x1), int(y1), int(x2), int(y2)],
                        confidence=conf,
                    )
                )

        logger.debug("Frame detections: %d person(s) found.", len(detections))
        return detections

    @property
    def model(self) -> YOLO:
        """Expose the underlying YOLO model (needed by the ByteTrack integration)."""
        return self._model
