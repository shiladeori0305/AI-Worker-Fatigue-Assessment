"""
fatigue_detector.py
-------------------
Extracts fatigue-related features from a worker's per-frame angle time-series
and computes a composite Fatigue Score (0–100).

Features computed
~~~~~~~~~~~~~~~~~
1.  bending_ratio        — fraction of frames where back_angle > threshold
2.  forward_lean_ratio   — fraction of frames where neck_angle > threshold
3.  static_posture_ratio — fraction of frames in "static" posture
4.  repetitive_motion    — count of bending repetitions (normalised)
5.  posture_change_rate  — posture changes per frame (normalised)
6.  max_back_angle       — peak back angle normalised to 90°

Fatigue Score formula
~~~~~~~~~~~~~~~~~~~~~
    raw_score = Σ (weight_i × feature_i_normalised_to_0_1) × 100
    fatigue_score = clip(raw_score, 0, 100)

Each feature is already in [0, 1] before weighting.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from src.config import (
    ASSUMED_FPS,
    BENDING_ANGLE_THRESHOLD,
    FATIGUE_LOW_MAX,
    FATIGUE_MEDIUM_MAX,
    FATIGUE_WEIGHTS,
    FORWARD_LEAN_THRESHOLD,
    MAX_EXPECTED_REPETITIONS,
    POSTURE_CHANGE_THRESHOLD,
    REPETITION_MIN_GAP_FRAMES,
    STATIC_POSTURE_DELTA_THRESHOLD,
)

logger = logging.getLogger(__name__)


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class FatigueResult:
    """
    Complete fatigue analysis result for one worker across the full session.

    Attributes
    ----------
    worker_id : int
    total_frames : int
    fps : float
    duration_seconds : float
    bending_ratio : float           Fraction of time spent bending [0–1]
    forward_lean_ratio : float      Fraction of time leaning forward [0–1]
    static_posture_ratio : float    Fraction of time in static posture [0–1]
    repetitive_motion_count : int   Raw number of bending repetitions
    posture_change_count : int      Raw number of posture changes
    max_back_angle : float          Peak back angle observed (degrees)
    duration_bent_seconds : float   Seconds spent bending
    duration_static_seconds : float Seconds in static posture
    fatigue_score : int             Composite score 0–100
    fatigue_level : str             "Low" | "Moderate" | "High"
    feature_contributions : dict    Per-feature weighted sub-scores
    """
    worker_id: int
    total_frames: int
    fps: float
    duration_seconds: float
    bending_ratio: float
    forward_lean_ratio: float
    static_posture_ratio: float
    repetitive_motion_count: int
    posture_change_count: int
    max_back_angle: float
    duration_bent_seconds: float
    duration_static_seconds: float
    fatigue_score: int
    fatigue_level: str
    feature_contributions: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "worker_id":               self.worker_id,
            "total_frames":            self.total_frames,
            "duration_seconds":        round(self.duration_seconds, 2),
            "fatigue_score":           self.fatigue_score,
            "fatigue_level":           self.fatigue_level,
            "bending_ratio":           round(self.bending_ratio, 4),
            "forward_lean_ratio":      round(self.forward_lean_ratio, 4),
            "static_posture_ratio":    round(self.static_posture_ratio, 4),
            "repetitive_motion_count": self.repetitive_motion_count,
            "posture_change_count":    self.posture_change_count,
            "max_back_angle":          round(self.max_back_angle, 2),
            "duration_bent_seconds":   round(self.duration_bent_seconds, 2),
            "duration_static_seconds": round(self.duration_static_seconds, 2),
            "feature_contributions":   {
                k: round(v, 4) for k, v in self.feature_contributions.items()
            },
        }


# ── FatigueDetector ────────────────────────────────────────────────────────────

class FatigueDetector:
    """
    Analyses a per-frame angle time-series for one worker and returns a
    FatigueResult with all extracted features and the composite fatigue score.

    Parameters
    ----------
    fps : float
        Video frame rate. Defaults to config.ASSUMED_FPS.
    """

    def __init__(self, fps: float = ASSUMED_FPS) -> None:
        self._fps = fps

    # ── Public interface ───────────────────────────────────────────────────────

    def analyse(
        self,
        worker_id: int,
        frame_angles: list[dict[str, Optional[float]]],
    ) -> FatigueResult:
        """
        Run the full fatigue analysis pipeline for one worker.

        Parameters
        ----------
        worker_id : int
            Persistent worker ID from Module 1.
        frame_angles : list[dict]
            Ordered list (one entry per frame) of angle dicts produced by
            angle_calculator.compute_all_angles().
            Keys expected: back_angle, neck_angle, avg_knee_angle,
                           avg_shoulder_angle (all optional / may be None).

        Returns
        -------
        FatigueResult
        """
        if not frame_angles:
            logger.warning("Worker %d: no frame angles — returning zero fatigue.", worker_id)
            return self._zero_result(worker_id)

        back_angles = self._extract_series(frame_angles, "back_angle")
        neck_angles = self._extract_series(frame_angles, "neck_angle")
        n = len(frame_angles)

        # ── Feature 1: bending ratio ───────────────────────────────────────────
        bending_frames = sum(1 for a in back_angles if a is not None and a > BENDING_ANGLE_THRESHOLD)
        bending_ratio  = bending_frames / n if n else 0.0

        # ── Feature 2: forward lean ratio ─────────────────────────────────────
        lean_frames       = sum(1 for a in neck_angles if a is not None and a > FORWARD_LEAN_THRESHOLD)
        forward_lean_ratio = lean_frames / n if n else 0.0

        # ── Feature 3: static posture ratio ───────────────────────────────────
        static_frames      = self._count_static_frames(back_angles, neck_angles)
        static_posture_ratio = static_frames / n if n else 0.0

        # ── Feature 4: repetitive motion count ────────────────────────────────
        rep_count = self._count_repetitions(back_angles)

        # ── Feature 5: posture change count ───────────────────────────────────
        change_count = self._count_posture_changes(back_angles)

        # ── Feature 6: max back angle ──────────────────────────────────────────
        valid_back = [a for a in back_angles if a is not None]
        max_back   = max(valid_back) if valid_back else 0.0

        # ── Normalise features to [0, 1] ──────────────────────────────────────
        features_norm = {
            "bending_ratio":        min(bending_ratio, 1.0),
            "forward_lean_ratio":   min(forward_lean_ratio, 1.0),
            "static_posture_ratio": min(static_posture_ratio, 1.0),
            "repetitive_motion":    min(rep_count / MAX_EXPECTED_REPETITIONS, 1.0),
            "posture_change_rate":  min(change_count / max(n, 1), 1.0),
            "max_back_angle":       min(max_back / 90.0, 1.0),
        }

        # ── Weighted composite fatigue score ──────────────────────────────────
        raw_score = sum(
            FATIGUE_WEIGHTS[k] * features_norm[k] for k in FATIGUE_WEIGHTS
        ) * 100.0

        fatigue_score = int(round(min(max(raw_score, 0), 100)))
        fatigue_level = self._fatigue_level(fatigue_score)

        # Per-feature weighted sub-score (for transparency / reporting)
        contributions = {
            k: round(FATIGUE_WEIGHTS[k] * features_norm[k] * 100, 2)
            for k in FATIGUE_WEIGHTS
        }

        # ── Durations in seconds ───────────────────────────────────────────────
        duration_seconds        = n / self._fps
        duration_bent_seconds   = bending_frames / self._fps
        duration_static_seconds = static_frames  / self._fps

        logger.info(
            "Worker %d | fatigue_score=%d (%s) | bent=%.1fs | reps=%d",
            worker_id, fatigue_score, fatigue_level,
            duration_bent_seconds, rep_count,
        )

        return FatigueResult(
            worker_id=worker_id,
            total_frames=n,
            fps=self._fps,
            duration_seconds=duration_seconds,
            bending_ratio=bending_ratio,
            forward_lean_ratio=forward_lean_ratio,
            static_posture_ratio=static_posture_ratio,
            repetitive_motion_count=rep_count,
            posture_change_count=change_count,
            max_back_angle=max_back,
            duration_bent_seconds=duration_bent_seconds,
            duration_static_seconds=duration_static_seconds,
            fatigue_score=fatigue_score,
            fatigue_level=fatigue_level,
            feature_contributions=contributions,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _extract_series(
        frame_angles: list[dict],
        key: str,
    ) -> list[Optional[float]]:
        """Extract a single angle key from every frame's dict."""
        return [fa.get(key) for fa in frame_angles]

    @staticmethod
    def _count_static_frames(
        back_angles: list[Optional[float]],
        neck_angles: list[Optional[float]],
    ) -> int:
        """
        Count frames where the worker is in a static posture.

        A frame is "static" when the absolute change in back angle
        AND neck angle from the previous frame are both below the
        configured threshold (i.e. almost no movement).
        """
        static = 0
        for i in range(1, len(back_angles)):
            back_prev, back_curr = back_angles[i - 1], back_angles[i]
            neck_prev, neck_curr = neck_angles[i - 1], neck_angles[i]

            if None in (back_prev, back_curr, neck_prev, neck_curr):
                continue

            back_delta = abs(back_curr - back_prev)  # type: ignore[operator]
            neck_delta = abs(neck_curr - neck_prev)  # type: ignore[operator]

            if (back_delta < STATIC_POSTURE_DELTA_THRESHOLD and
                    neck_delta < STATIC_POSTURE_DELTA_THRESHOLD):
                static += 1

        return static

    @staticmethod
    def _count_repetitions(back_angles: list[Optional[float]]) -> int:
        """
        Count bending repetitions using threshold-crossing detection.

        A repetition is counted each time the back-angle signal crosses
        BENDING_ANGLE_THRESHOLD in the upward direction (below → above),
        provided at least REPETITION_MIN_GAP_FRAMES have elapsed since
        the last crossing.
        """
        count = 0
        last_crossing_frame = -REPETITION_MIN_GAP_FRAMES
        above = False

        for i, angle in enumerate(back_angles):
            if angle is None:
                continue
            is_above = angle > BENDING_ANGLE_THRESHOLD
            if is_above and not above:
                # Rising edge: below → above threshold
                if i - last_crossing_frame >= REPETITION_MIN_GAP_FRAMES:
                    count += 1
                    last_crossing_frame = i
            above = is_above

        return count

    @staticmethod
    def _count_posture_changes(back_angles: list[Optional[float]]) -> int:
        """Count frames where back angle shifts by more than the threshold."""
        changes = 0
        for i in range(1, len(back_angles)):
            prev, curr = back_angles[i - 1], back_angles[i]
            if prev is not None and curr is not None:
                if abs(curr - prev) > POSTURE_CHANGE_THRESHOLD:
                    changes += 1
        return changes

    @staticmethod
    def _fatigue_level(score: int) -> str:
        if score <= FATIGUE_LOW_MAX:
            return "Low"
        if score <= FATIGUE_MEDIUM_MAX:
            return "Moderate"
        return "High"

    def _zero_result(self, worker_id: int) -> FatigueResult:
        """Return a zero-value result for workers with no usable data."""
        return FatigueResult(
            worker_id=worker_id,
            total_frames=0,
            fps=self._fps,
            duration_seconds=0.0,
            bending_ratio=0.0,
            forward_lean_ratio=0.0,
            static_posture_ratio=0.0,
            repetitive_motion_count=0,
            posture_change_count=0,
            max_back_angle=0.0,
            duration_bent_seconds=0.0,
            duration_static_seconds=0.0,
            fatigue_score=0,
            fatigue_level="Low",
        )
