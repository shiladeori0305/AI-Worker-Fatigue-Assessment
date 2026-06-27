"""
skeleton_drawer.py
------------------
Renders pose skeletons, landmarks, and worker ID labels on video frames.
Updated to pull canonical landmark connections from the modern Tasks API.
"""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision

from src.config import (
    CONNECTION_COLOR,
    CONNECTION_THICKNESS,
    FONT_SCALE,
    FONT_THICKNESS,
    LABEL_BG_COLOR,
    LABEL_PADDING,
    LANDMARK_COLOR,
    LANDMARK_NAMES,
    LANDMARK_RADIUS,
    MIN_VISIBILITY,
    WORKER_ID_COLOR,
)
from src.pose_estimator import Keypoint, WorkerPose

logger = logging.getLogger(__name__)

# Fetch the modern, non-deprecated skeleton connections mapping
_POSE_CONNECTIONS = vision.PoseLandmarksConnections.POSE_LANDMARKS

class SkeletonDrawer:
    """
    Draws pose skeletons on video frames.

    Usage
    -----
    drawer = SkeletonDrawer()
    annotated_frame = drawer.draw(frame, worker_poses)
    """

    def __init__(self) -> None:
        self._font = cv2.FONT_HERSHEY_SIMPLEX

    # ── Private helpers ────────────────────────────────────────────────────────

    def _draw_connections(
        self,
        frame: np.ndarray,
        keypoints: dict[str, Optional[Keypoint]],
    ) -> None:
        """
        Draw skeleton bones between connected landmark pairs.
        Only draws a connection when both endpoints are visible (non-None).
        """
        for conn in _POSE_CONNECTIONS:
            start_idx, end_idx = conn.start, conn.end
            # Safely guard indices against custom configuration names lengths
            if start_idx >= len(LANDMARK_NAMES) or end_idx >= len(LANDMARK_NAMES):
                continue

            start_name = LANDMARK_NAMES[start_idx]
            end_name   = LANDMARK_NAMES[end_idx]

            kp_start = keypoints.get(start_name)
            kp_end   = keypoints.get(end_name)

            if kp_start is None or kp_end is None:
                continue  # Skip occluded connections

            cv2.line(
                frame,
                (kp_start.x, kp_start.y),
                (kp_end.x,   kp_end.y),
                CONNECTION_COLOR,
                CONNECTION_THICKNESS,
                cv2.LINE_AA,
            )

    def _draw_landmarks(
        self,
        frame: np.ndarray,
        keypoints: dict[str, Optional[Keypoint]],
    ) -> None:
        """Draw a filled circle at each visible landmark."""
        for kp in keypoints.values():
            if kp is None:
                continue
            cv2.circle(
                frame,
                (kp.x, kp.y),
                LANDMARK_RADIUS,
                LANDMARK_COLOR,
                -1,           # Filled
                cv2.LINE_AA,
            )

    def _draw_worker_label(
        self,
        frame: np.ndarray,
        worker_pose: WorkerPose,
    ) -> None:
        """Draw a "Worker ID: N" label above the bounding box or shoulder anchors."""
        x1, y1, x2, y2 = worker_pose.bbox
        text = f"Worker ID: {worker_pose.worker_id}"

        # Attempt to place label at the higher shoulder for naturalness
        left_shoulder  = worker_pose.keypoints.get("left_shoulder")
        right_shoulder = worker_pose.keypoints.get("right_shoulder")

        if left_shoulder and right_shoulder:
            label_x = min(left_shoulder.x, right_shoulder.x)
            label_y = min(left_shoulder.y, right_shoulder.y) - 10
        else:
            label_x = x1
            label_y = max(y1 - 10, 0)

        (text_w, text_h), baseline = cv2.getTextSize(
            text, self._font, FONT_SCALE, FONT_THICKNESS
        )
        pad = LABEL_PADDING
        rect_y1 = max(label_y - text_h - baseline - pad * 2, 0)
        rect_y2 = label_y
        rect_x2 = label_x + text_w + pad * 2

        # Filled background rectangle
        cv2.rectangle(
            frame,
            (label_x, rect_y1),
            (rect_x2, rect_y2),
            LABEL_BG_COLOR,
            -1,
        )
        cv2.putText(
            frame,
            text,
            (label_x + pad, label_y - baseline - pad),
            self._font,
            FONT_SCALE,
            WORKER_ID_COLOR,
            FONT_THICKNESS,
            cv2.LINE_AA,
        )

    def _draw_no_pose_indicator(
        self,
        frame: np.ndarray,
        worker_pose: WorkerPose,
    ) -> None:
        """Draw a bounding box and 'No Pose' label when estimation drops."""
        x1, y1, x2, y2 = worker_pose.bbox
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 200), 1)
        text = f"ID:{worker_pose.worker_id} [no pose]"
        cv2.putText(
            frame,
            text,
            (x1 + 2, max(y1 - 6, 10)),
            self._font,
            0.45,
            (0, 0, 200),
            1,
            cv2.LINE_AA,
        )

    # ── Public interface ───────────────────────────────────────────────────────

    def draw(
        self,
        frame: np.ndarray,
        worker_poses: list[WorkerPose],
    ) -> np.ndarray:
        """
        Annotate a frame with skeletons for all tracked workers.
        """
        for wp in worker_poses:
            if not wp.pose_detected:
                self._draw_no_pose_indicator(frame, wp)
                continue

            # Draw in back-to-front layers
            self._draw_connections(frame, wp.keypoints)
            self._draw_landmarks(frame, wp.keypoints)
            self._draw_worker_label(frame, wp)

        return frame