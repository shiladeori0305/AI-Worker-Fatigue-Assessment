"""
pose_estimator.py
-----------------
MediaPipe Pose wrapper for per-worker keypoint extraction using modern Tasks API.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from src.config import (
    BBOX_PADDING,
    LANDMARK_NAMES,
    MIN_VISIBILITY,
    MP_ENABLE_SEGMENTATION,
    MP_MIN_DETECTION_CONFIDENCE,
    MP_MIN_TRACKING_CONFIDENCE,
    MP_MODEL_COMPLEXITY,
    MP_STATIC_IMAGE_MODE,
)

logger = logging.getLogger(__name__)


# ── Data models ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Keypoint:
    x: int
    y: int
    z: float
    visibility: float

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "z": round(self.z, 6),
            "visibility": round(self.visibility, 4),
        }


@dataclass
class WorkerPose:
    worker_id: int
    bbox: list[int]
    keypoints: dict[str, Optional[Keypoint]] = field(default_factory=dict)
    pose_detected: bool = False

    def to_dict(self) -> dict:
        serialised_kps: dict = {}
        for name, kp in self.keypoints.items():
            serialised_kps[name] = kp.to_dict() if kp is not None else None
        return {
            "worker_id": self.worker_id,
            "pose_detected": self.pose_detected,
            "keypoints": serialised_kps,
        }


# ── PoseEstimator ──────────────────────────────────────────────────────────────

class PoseEstimator:

    def __init__(
        self,
        model_complexity: int = MP_MODEL_COMPLEXITY,
        min_detection_confidence: float = MP_MIN_DETECTION_CONFIDENCE,
        min_tracking_confidence: float = MP_MIN_TRACKING_CONFIDENCE,
        model_path: str = "pose_landmarker_full.task",
    ) -> None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"MediaPipe model file not found at '{model_path}'. "
                "Please download pose_landmarker_full.task from Google MediaPipe."
            )

        base_options = python.BaseOptions(model_asset_path=model_path)

        running_mode = (
            vision.RunningMode.IMAGE
            if MP_STATIC_IMAGE_MODE
            else vision.RunningMode.VIDEO
        )

        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=running_mode,
            output_segmentation_masks=MP_ENABLE_SEGMENTATION,
            min_pose_detection_confidence=min_detection_confidence,
            min_pose_presence_confidence=min_tracking_confidence,
        )

        self._detector = vision.PoseLandmarker.create_from_options(options)

        # ── FIX 2: one counter that increments on every detect_for_video call ──
        # Previously this was incremented once per frame (outside the worker
        # loop), so two workers in the same frame would both call
        # detect_for_video() with the identical timestamp → crash.
        # Now it increments inside the loop so every call gets a unique value.
        self._timestamp_ms: int = 0

        logger.info(
            "PoseEstimator initialised (mode=%s, det_conf=%.2f, trk_conf=%.2f)",
            running_mode.name,
            min_detection_confidence,
            min_tracking_confidence,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _safe_crop(
        frame: np.ndarray,
        bbox: list[int],
        padding: int = BBOX_PADDING,
    ) -> tuple[np.ndarray | None, int, int]:
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = bbox

        cx1 = max(0, x1 - padding)
        cy1 = max(0, y1 - padding)
        cx2 = min(w, x2 + padding)
        cy2 = min(h, y2 + padding)

        if cx2 <= cx1 or cy2 <= cy1:
            logger.warning("Degenerate bbox %s after padding — skipping worker.", bbox)
            return None, cx1, cy1

        return frame[cy1:cy2, cx1:cx2], cx1, cy1

    def _extract_keypoints(
        self,
        mp_result,
        crop: np.ndarray,
        crop_x1: int,
        crop_y1: int,
    ) -> dict[str, Optional[Keypoint]]:
        crop_h, crop_w = crop.shape[:2]
        keypoints: dict[str, Optional[Keypoint]] = {}
        landmarks = mp_result.pose_landmarks[0]

        for idx, name in enumerate(LANDMARK_NAMES):
            if idx >= len(landmarks):
                keypoints[name] = None
                continue

            lm = landmarks[idx]

            if lm.visibility < MIN_VISIBILITY:
                keypoints[name] = None
                continue

            px = int(lm.x * crop_w) + crop_x1
            py = int(lm.y * crop_h) + crop_y1

            keypoints[name] = Keypoint(
                x=px,
                y=py,
                z=float(lm.z),
                visibility=float(lm.visibility),
            )

        return keypoints

    # ── Public interface ───────────────────────────────────────────────────────

    def estimate(
        self,
        frame: np.ndarray,
        workers: list[dict],
    ) -> list[WorkerPose]:
        if frame is None or frame.size == 0:
            logger.warning("estimate() called with an empty frame — returning [].")
            return []

        results: list[WorkerPose] = []

        # NOTE: self._timestamp_ms is NOT incremented here anymore.
        # It is incremented inside the loop below so that every individual
        # detect_for_video() call receives a strictly increasing value,
        # even when multiple workers share the same video frame.

        for worker in workers:
            worker_id: int  = int(worker["id"])
            bbox: list[int] = [int(v) for v in worker["bbox"]]

            crop, crop_x1, crop_y1 = self._safe_crop(frame, bbox)
            if crop is None:
                results.append(WorkerPose(worker_id=worker_id, bbox=bbox))
                continue

            rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_crop)

            # ── FIX 2: increment before every detect_for_video call ────────────
            self._timestamp_ms += 1

            if MP_STATIC_IMAGE_MODE:
                mp_result = self._detector.detect(mp_image)
            else:
                mp_result = self._detector.detect_for_video(mp_image, self._timestamp_ms)

            if not mp_result.pose_landmarks:
                logger.debug("Worker %d — no pose landmarks detected.", worker_id)
                results.append(WorkerPose(worker_id=worker_id, bbox=bbox))
                continue

            keypoints = self._extract_keypoints(mp_result, crop, crop_x1, crop_y1)

            results.append(
                WorkerPose(
                    worker_id=worker_id,
                    bbox=bbox,
                    keypoints=keypoints,
                    pose_detected=True,
                )
            )
            logger.debug(
                "Worker %d — %d/%d landmarks visible.",
                worker_id,
                sum(1 for v in keypoints.values() if v is not None),
                len(keypoints),
            )

        return results

    def close(self) -> None:
        self._detector.close()
        logger.debug("PoseEstimator closed.")

    def __enter__(self) -> "PoseEstimator":
        return self

    def __exit__(self, *_) -> None:
        self.close()
