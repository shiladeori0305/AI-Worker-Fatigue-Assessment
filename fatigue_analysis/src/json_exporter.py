"""
json_exporter.py
----------------
Writes the two output JSON files consumed by Module 4 (Dashboard):

    output/fatigue_report.json      — full per-worker fatigue analysis
    output/ergonomic_scores.json    — ergonomic scores + unified risk report

Both files use the same worker ordering.

Output schema (fatigue_report.json)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
[
  {
    "worker_id": 1,
    "fatigue_score": 78,
    "fatigue_level": "High",
    "ergonomic_score": 72,
    "ergonomic_risk": "HIGH",
    "overall_risk": "HIGH",
    "alert": true,
    "mean_back_angle": 34.2,
    "mean_neck_angle": 22.1,
    "mean_knee_angle": 15.8,
    "duration_seconds": 120.0,
    "duration_bent_seconds": 68.4,
    "repetitive_motion_count": 24,
    "posture_change_count": 87,
    "summary": "Risk: HIGH | Fatigue: 78/100 (High) | ..."
  }
]

Output schema (ergonomic_scores.json)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
[
  {
    "worker_id": 1,
    "neck_score": 45.2,
    "back_score": 72.1,
    "knee_score": 18.4,
    "shoulder_score": 30.0,
    "ergonomic_score": 52,
    "risk_level": "MEDIUM",
    "alert": false,
    "mean_neck_angle": 22.1,
    "mean_back_angle": 34.2,
    "mean_knee_angle": 15.8,
    "mean_shoulder_angle": 12.5
  }
]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.ergonomic_analyzer import ErgonomicResult
from src.risk_classifier import WorkerReport

logger = logging.getLogger(__name__)


class ResultExporter:
    """
    Serialises analysis results and writes them to JSON files.

    Parameters
    ----------
    fatigue_report_path : Path
        Destination for fatigue_report.json
    ergonomic_scores_path : Path
        Destination for ergonomic_scores.json
    """

    def __init__(
        self,
        fatigue_report_path: Path,
        ergonomic_scores_path: Path,
    ) -> None:
        fatigue_report_path.parent.mkdir(parents=True, exist_ok=True)
        ergonomic_scores_path.parent.mkdir(parents=True, exist_ok=True)
        self._fatigue_path   = fatigue_report_path
        self._ergo_path      = ergonomic_scores_path

    def export(
        self,
        worker_reports: list[WorkerReport],
        ergonomic_results: list[ErgonomicResult],
    ) -> None:
        """
        Write both output JSON files.

        Parameters
        ----------
        worker_reports : list[WorkerReport]
            One unified report per worker (from RiskClassifier).
        ergonomic_results : list[ErgonomicResult]
            Raw ergonomic sub-scores per worker (from ErgonomicAnalyzer).
        """
        self._write_fatigue_report(worker_reports)
        self._write_ergonomic_scores(ergonomic_results)

    def _write_fatigue_report(self, reports: list[WorkerReport]) -> None:
        data = [r.to_dict() for r in reports]
        with open(self._fatigue_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        logger.info(
            "fatigue_report.json saved → '%s'  (%d workers)",
            self._fatigue_path, len(reports),
        )

    def _write_ergonomic_scores(self, results: list[ErgonomicResult]) -> None:
        data = [r.to_dict() for r in results]
        with open(self._ergo_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        logger.info(
            "ergonomic_scores.json saved → '%s'  (%d workers)",
            self._ergo_path, len(results),
        )
