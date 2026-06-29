"""
risk_classifier.py
------------------
Combines FatigueResult and ErgonomicResult into a unified WorkerReport
that is ready for JSON export and consumption by Module 4.

Final risk level logic
~~~~~~~~~~~~~~~~~~~~~~
The overall risk level for a worker is determined by the HIGHER of the
two individual risk levels (fatigue vs ergonomic):

    Fatigue level  ×  Ergonomic risk  →  Overall risk
    Low            ×  LOW             →  LOW
    Moderate       ×  LOW             →  MEDIUM
    Low            ×  MEDIUM          →  MEDIUM
    High           ×  any             →  HIGH
    any            ×  HIGH            →  HIGH

An alert is raised when either:
  - fatigue_score > ALERT_THRESHOLD, OR
  - ergonomic_score > ALERT_THRESHOLD

This ensures the dashboard (Module 4) is notified for any severe
condition regardless of which domain it originates in.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from src.config import ALERT_THRESHOLD
from src.ergonomic_analyzer import ErgonomicResult
from src.fatigue_detector import FatigueResult

logger = logging.getLogger(__name__)


# ── Unified worker report ──────────────────────────────────────────────────────

@dataclass
class WorkerReport:
    """
    Unified risk report for one worker — the primary output of Module 3.

    This is the data contract between Module 3 and Module 4 (Dashboard).

    Attributes
    ----------
    worker_id : int
    fatigue_score : int           0–100
    fatigue_level : str           "Low" | "Moderate" | "High"
    ergonomic_score : int         0–100
    ergonomic_risk : str          "LOW" | "MEDIUM" | "HIGH"
    overall_risk : str            "LOW" | "MEDIUM" | "HIGH"
    alert : bool                  True = immediate attention required
    mean_back_angle : float       Degrees (session average)
    mean_neck_angle : float       Degrees (session average)
    mean_knee_angle : float       Degrees (session average)
    duration_seconds : float      Total observed duration
    duration_bent_seconds : float Time spent bending
    repetitive_motion_count : int Number of bending repetitions
    posture_change_count : int
    summary : str                 Human-readable one-liner for reports
    """
    worker_id: int
    fatigue_score: int
    fatigue_level: str
    ergonomic_score: int
    ergonomic_risk: str
    overall_risk: str
    alert: bool
    mean_back_angle: Optional[float]
    mean_neck_angle: Optional[float]
    mean_knee_angle: Optional[float]
    duration_seconds: float
    duration_bent_seconds: float
    repetitive_motion_count: int
    posture_change_count: int
    summary: str

    def to_dict(self) -> dict:
        """Serialise to the Module 4 JSON schema."""
        return {
            "worker_id":               self.worker_id,
            "fatigue_score":           self.fatigue_score,
            "fatigue_level":           self.fatigue_level,
            "ergonomic_score":         self.ergonomic_score,
            "ergonomic_risk":          self.ergonomic_risk,
            "overall_risk":            self.overall_risk,
            "alert":                   self.alert,
            "mean_back_angle":         _fmt(self.mean_back_angle),
            "mean_neck_angle":         _fmt(self.mean_neck_angle),
            "mean_knee_angle":         _fmt(self.mean_knee_angle),
            "duration_seconds":        round(self.duration_seconds, 2),
            "duration_bent_seconds":   round(self.duration_bent_seconds, 2),
            "repetitive_motion_count": self.repetitive_motion_count,
            "posture_change_count":    self.posture_change_count,
            "summary":                 self.summary,
        }


def _fmt(v: Optional[float]) -> Optional[float]:
    return round(v, 2) if v is not None else None


# ── Risk Classifier ────────────────────────────────────────────────────────────

class RiskClassifier:
    """
    Merges fatigue and ergonomic analysis results into a unified WorkerReport.

    Usage
    -----
    classifier = RiskClassifier()
    report = classifier.classify(fatigue_result, ergonomic_result)
    """

    # Map fatigue level strings to numeric rank for comparison
    _FATIGUE_RANK: dict[str, int] = {"Low": 1, "Moderate": 2, "High": 3}
    _ERGO_RANK:    dict[str, int] = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
    _RANK_TO_OVERALL: dict[int, str] = {1: "LOW", 2: "MEDIUM", 3: "HIGH"}

    def classify(
        self,
        fatigue: FatigueResult,
        ergonomic: ErgonomicResult,
    ) -> WorkerReport:
        """
        Produce a unified WorkerReport from the two domain-specific results.

        Parameters
        ----------
        fatigue : FatigueResult
            Output of FatigueDetector.analyse().
        ergonomic : ErgonomicResult
            Output of ErgonomicAnalyzer.analyse().

        Returns
        -------
        WorkerReport
        """
        assert fatigue.worker_id == ergonomic.worker_id, \
            f"worker_id mismatch: {fatigue.worker_id} vs {ergonomic.worker_id}"

        # ── Overall risk = worst of the two domains ────────────────────────────
        f_rank = self._FATIGUE_RANK.get(fatigue.fatigue_level, 1)
        e_rank = self._ERGO_RANK.get(ergonomic.risk_level, 1)
        overall_rank    = max(f_rank, e_rank)
        overall_risk    = self._RANK_TO_OVERALL[overall_rank]

        # ── Alert if either score exceeds threshold ────────────────────────────
        alert = (
            fatigue.fatigue_score    > ALERT_THRESHOLD or
            ergonomic.ergonomic_score > ALERT_THRESHOLD
        )

        # ── Human-readable summary ─────────────────────────────────────────────
        summary = self._build_summary(fatigue, ergonomic, overall_risk, alert)

        logger.info(
            "Worker %d | overall_risk=%s | alert=%s | summary: %s",
            fatigue.worker_id, overall_risk, alert, summary,
        )

        return WorkerReport(
            worker_id=fatigue.worker_id,
            fatigue_score=fatigue.fatigue_score,
            fatigue_level=fatigue.fatigue_level,
            ergonomic_score=ergonomic.ergonomic_score,
            ergonomic_risk=ergonomic.risk_level,
            overall_risk=overall_risk,
            alert=alert,
            mean_back_angle=ergonomic.mean_back_angle,
            mean_neck_angle=ergonomic.mean_neck_angle,
            mean_knee_angle=ergonomic.mean_knee_angle,
            duration_seconds=fatigue.duration_seconds,
            duration_bent_seconds=fatigue.duration_bent_seconds,
            repetitive_motion_count=fatigue.repetitive_motion_count,
            posture_change_count=fatigue.posture_change_count,
            summary=summary,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _build_summary(
        fatigue: FatigueResult,
        ergonomic: ErgonomicResult,
        overall_risk: str,
        alert: bool,
    ) -> str:
        parts = [
            f"Risk: {overall_risk}",
            f"Fatigue: {fatigue.fatigue_score}/100 ({fatigue.fatigue_level})",
            f"Ergo: {ergonomic.ergonomic_score}/100 ({ergonomic.risk_level})",
        ]
        if ergonomic.mean_back_angle is not None:
            parts.append(f"Back: {ergonomic.mean_back_angle:.1f}°")
        if ergonomic.mean_neck_angle is not None:
            parts.append(f"Neck: {ergonomic.mean_neck_angle:.1f}°")
        if fatigue.repetitive_motion_count:
            parts.append(f"Reps: {fatigue.repetitive_motion_count}")
        if alert:
            parts.append("⚠ ALERT")
        return " | ".join(parts)
