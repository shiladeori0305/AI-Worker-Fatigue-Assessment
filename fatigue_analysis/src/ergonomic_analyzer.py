"""
ergonomic_analyzer.py
---------------------
REBA/RULA-inspired ergonomic risk scoring from averaged joint angles.

Approach
~~~~~~~~
For each joint (neck, back, knee, shoulder) we compute a sub-score on a
0–100 scale based on where the mean observed angle falls relative to the
Low / Medium / High risk bands defined in config.py.

The four sub-scores are combined into a composite Ergonomic Risk Score
using the weights in config.ERGONOMIC_WEIGHTS.

    composite = Σ weight_i × sub_score_i   (already 0–100 scale)

Risk bands
~~~~~~~~~~
    0 – 33  → LOW RISK
    34 – 66 → MEDIUM RISK
    67 – 100→ HIGH RISK

This is a simplified model; a full REBA/RULA implementation would also
account for load, coupling, activity multipliers, etc.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from src.config import (
    ALERT_THRESHOLD,
    BACK_ANGLE_LOW,
    BACK_ANGLE_MEDIUM,
    ERGONOMIC_WEIGHTS,
    KNEE_ANGLE_LOW,
    KNEE_ANGLE_MEDIUM,
    NECK_ANGLE_LOW,
    NECK_ANGLE_MEDIUM,
    RISK_LOW_MAX,
    RISK_MEDIUM_MAX,
    SHOULDER_ANGLE_LOW,
    SHOULDER_ANGLE_MEDIUM,
)

logger = logging.getLogger(__name__)


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class ErgonomicResult:
    """
    Ergonomic risk assessment for one worker across the full session.

    Attributes
    ----------
    worker_id : int
    mean_neck_angle : float | None      Mean neck angle over session (degrees)
    mean_back_angle : float | None      Mean back angle over session
    mean_knee_angle : float | None      Mean knee angle (bilateral average)
    mean_shoulder_angle : float | None  Mean shoulder elevation (bilateral)
    neck_score : float                  Sub-score 0–100
    back_score : float                  Sub-score 0–100
    knee_score : float                  Sub-score 0–100
    shoulder_score : float              Sub-score 0–100
    ergonomic_score : int               Composite 0–100
    risk_level : str                    "LOW" | "MEDIUM" | "HIGH"
    alert : bool                        True when score > ALERT_THRESHOLD
    """
    worker_id: int
    mean_neck_angle:     Optional[float]
    mean_back_angle:     Optional[float]
    mean_knee_angle:     Optional[float]
    mean_shoulder_angle: Optional[float]
    neck_score:     float
    back_score:     float
    knee_score:     float
    shoulder_score: float
    ergonomic_score: int
    risk_level: str
    alert: bool

    def to_dict(self) -> dict:
        return {
            "worker_id":           self.worker_id,
            "mean_neck_angle":     _fmt(self.mean_neck_angle),
            "mean_back_angle":     _fmt(self.mean_back_angle),
            "mean_knee_angle":     _fmt(self.mean_knee_angle),
            "mean_shoulder_angle": _fmt(self.mean_shoulder_angle),
            "neck_score":          round(self.neck_score, 2),
            "back_score":          round(self.back_score, 2),
            "knee_score":          round(self.knee_score, 2),
            "shoulder_score":      round(self.shoulder_score, 2),
            "ergonomic_score":     self.ergonomic_score,
            "risk_level":          self.risk_level,
            "alert":               self.alert,
        }


def _fmt(v: Optional[float]) -> Optional[float]:
    return round(v, 2) if v is not None else None


# ── Ergonomic Analyzer ─────────────────────────────────────────────────────────

class ErgonomicAnalyzer:
    """
    Scores ergonomic risk for a worker based on their mean joint angles.

    Usage
    -----
    analyzer = ErgonomicAnalyzer()
    result = analyzer.analyse(worker_id, frame_angles)
    """

    # ── Public interface ───────────────────────────────────────────────────────

    def analyse(
        self,
        worker_id: int,
        frame_angles: list[dict[str, Optional[float]]],
    ) -> ErgonomicResult:
        """
        Compute ergonomic risk from a worker's per-frame angle time-series.

        Parameters
        ----------
        worker_id : int
        frame_angles : list[dict]
            One dict per frame; keys include neck_angle, back_angle,
            avg_knee_angle, avg_shoulder_angle.

        Returns
        -------
        ErgonomicResult
        """
        # ── Compute mean angles over the session ───────────────────────────────
        mean_neck     = self._mean_angle(frame_angles, "neck_angle")
        mean_back     = self._mean_angle(frame_angles, "back_angle")
        mean_knee     = self._mean_angle(frame_angles, "avg_knee_angle")
        mean_shoulder = self._mean_angle(frame_angles, "avg_shoulder_angle")

        # ── Convert mean angles to 0–100 risk sub-scores ───────────────────────
        neck_score     = self._angle_to_score(mean_neck,     NECK_ANGLE_LOW,     NECK_ANGLE_MEDIUM)
        back_score     = self._angle_to_score(mean_back,     BACK_ANGLE_LOW,     BACK_ANGLE_MEDIUM)
        knee_score     = self._angle_to_score(mean_knee,     KNEE_ANGLE_LOW,     KNEE_ANGLE_MEDIUM)
        shoulder_score = self._angle_to_score(mean_shoulder, SHOULDER_ANGLE_LOW, SHOULDER_ANGLE_MEDIUM)

        # ── Weighted composite ─────────────────────────────────────────────────
        composite = (
            ERGONOMIC_WEIGHTS["neck_score"]     * neck_score +
            ERGONOMIC_WEIGHTS["back_score"]     * back_score +
            ERGONOMIC_WEIGHTS["knee_score"]     * knee_score +
            ERGONOMIC_WEIGHTS["shoulder_score"] * shoulder_score
        )
        ergonomic_score = int(round(min(max(composite, 0), 100)))
        risk_level      = self._risk_level(ergonomic_score)
        alert           = ergonomic_score > ALERT_THRESHOLD

        logger.info(
            "Worker %d | ergo_score=%d (%s) | back=%.1f° neck=%.1f°",
            worker_id, ergonomic_score, risk_level,
            mean_back or 0, mean_neck or 0,
        )

        return ErgonomicResult(
            worker_id=worker_id,
            mean_neck_angle=mean_neck,
            mean_back_angle=mean_back,
            mean_knee_angle=mean_knee,
            mean_shoulder_angle=mean_shoulder,
            neck_score=neck_score,
            back_score=back_score,
            knee_score=knee_score,
            shoulder_score=shoulder_score,
            ergonomic_score=ergonomic_score,
            risk_level=risk_level,
            alert=alert,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _mean_angle(
        frame_angles: list[dict],
        key: str,
    ) -> Optional[float]:
        """Compute the mean of a named angle across all frames, ignoring None."""
        vals = [fa[key] for fa in frame_angles if fa.get(key) is not None]
        if not vals:
            return None
        return round(sum(vals) / len(vals), 2)

    @staticmethod
    def _angle_to_score(
        angle: Optional[float],
        low_threshold: float,
        medium_threshold: float,
    ) -> float:
        """
        Map a joint angle (degrees) to a risk sub-score in [0, 100].

        Scoring bands
        ~~~~~~~~~~~~~
        angle < low_threshold    →  0 – 33   (low risk band)
        low ≤ angle < medium     → 33 – 66   (medium risk band)
        angle ≥ medium           → 66 – 100  (high risk band)

        Within each band the score is linearly interpolated so the
        function is continuous and monotonically increasing.
        """
        if angle is None:
            return 0.0   # Unknown → assume no risk

        if angle < low_threshold:
            # Linear from 0 → 33 as angle goes 0 → low_threshold
            return (angle / low_threshold) * 33.0

        if angle < medium_threshold:
            # Linear from 33 → 66 as angle goes low_threshold → medium_threshold
            t = (angle - low_threshold) / (medium_threshold - low_threshold)
            return 33.0 + t * 33.0

        # Linear from 66 → 100 as angle goes medium_threshold → medium_threshold*2
        t = min((angle - medium_threshold) / medium_threshold, 1.0)
        return 66.0 + t * 34.0

    @staticmethod
    def _risk_level(score: int) -> str:
        if score <= RISK_LOW_MAX:
            return "LOW"
        if score <= RISK_MEDIUM_MAX:
            return "MEDIUM"
        return "HIGH"
