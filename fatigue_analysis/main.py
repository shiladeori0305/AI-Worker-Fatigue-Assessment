"""
main.py
-------
Entry point for Module 3: Fatigue Analysis and Ergonomic Risk Assessment.

Pipeline
~~~~~~~~
    pose_data.json  (from Module 2)
           │
           ▼
    Load and index pose data by worker ID
           │
           ▼  per worker
    AngleCalculator  →  per-frame angle time-series
           │
           ├──► FatigueDetector    →  FatigueResult
           │
           ├──► ErgonomicAnalyzer  →  ErgonomicResult
           │
           └──► RiskClassifier     →  WorkerReport
                      │
           ┌──────────┘
           ▼
    ResultExporter
           ├──► output/fatigue_report.json
           └──► output/ergonomic_scores.json

Run from the project root:
    python main.py

Optional environment-variable overrides:
    POSE_JSON        — path to pose_data.json
    FATIGUE_REPORT   — destination for fatigue_report.json
    ERGO_SCORES      — destination for ergonomic_scores.json
    VIDEO_FPS        — actual video FPS (overrides config.ASSUMED_FPS)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

from src.angle_calculator import compute_all_angles
from src.config import (
    ASSUMED_FPS,
    ERGONOMIC_SCORES_PATH,
    FATIGUE_REPORT_PATH,
    POSE_DATA_PATH,
)
from src.ergonomic_analyzer import ErgonomicAnalyzer, ErgonomicResult
from src.fatigue_detector import FatigueDetector, FatigueResult
from src.json_exporter import ResultExporter
from src.risk_classifier import RiskClassifier, WorkerReport

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Path resolution ────────────────────────────────────────────────────────────

def _resolve_paths() -> tuple[Path, Path, Path]:
    return (
        Path(os.environ.get("POSE_JSON",      POSE_DATA_PATH)),
        Path(os.environ.get("FATIGUE_REPORT", FATIGUE_REPORT_PATH)),
        Path(os.environ.get("ERGO_SCORES",    ERGONOMIC_SCORES_PATH)),
    )


# ── Pose data loader ───────────────────────────────────────────────────────────

def _load_pose_data(json_path: Path) -> dict[int, list[dict]]:
    """
    Load pose_data.json and index frames by worker ID.

    Handles both Module 2 output schemas:
      - keypoints as {"x": int, "y": int, ...} dicts (new Tasks API format)
      - keypoints as [x, y] lists (legacy format)
      - worker key "worker_id" OR "id"

    Returns
    -------
    dict[int, list[dict]]
        worker_id → ordered list of landmark dicts (one per frame, in order)
    """
    if not json_path.exists():
        raise FileNotFoundError(
            f"pose_data.json not found at '{json_path}'.\n"
            "Copy pose_data.json from Module 2's output/ into this module's input/."
        )

    with open(json_path, encoding="utf-8") as fh:
        try:
            raw: list[dict] = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Cannot parse '{json_path}': {exc}") from exc

    # Index: worker_id → [ {landmark_name: point, ...}, ... ] per frame in order
    worker_frames: dict[int, list[dict]] = defaultdict(list)
    total_records = 0

    for record in raw:
        frame_idx = record.get("frame", 0)
        workers   = record.get("workers", [])

        for w in workers:
            # Accept both "worker_id" and "id" keys
            wid = w.get("worker_id") or w.get("id")
            if wid is None:
                logger.warning("Frame %d: worker record missing ID — skipping.", frame_idx)
                continue

            wid = int(wid)

            if not w.get("pose_detected", True):
                # No pose in this frame — append an empty landmark dict so the
                # frame-index stays aligned (angles will all be None)
                worker_frames[wid].append({})
                continue

            # Normalise keypoints to a flat {name: (x, y)} dict
            raw_kps = w.get("keypoints") or w.get("landmarks") or {}
            landmarks: dict[str, Optional[tuple[float, float]]] = {}

            for name, val in raw_kps.items():
                if val is None:
                    landmarks[name] = None
                elif isinstance(val, (list, tuple)) and len(val) >= 2:
                    landmarks[name] = (float(val[0]), float(val[1]))
                elif isinstance(val, dict) and "x" in val and "y" in val:
                    landmarks[name] = (float(val["x"]), float(val["y"]))
                else:
                    landmarks[name] = None

            worker_frames[wid].append(landmarks)
            total_records += 1

    logger.info(
        "Pose data loaded: %d frames total, %d workers, %d worker-frame records.",
        len(raw),
        len(worker_frames),
        total_records,
    )
    return dict(worker_frames)


# ── Pipeline ───────────────────────────────────────────────────────────────────

def run_pipeline(
    pose_json: Path,
    fatigue_report: Path,
    ergo_scores: Path,
    fps: float = ASSUMED_FPS,
) -> None:
    logger.info("═" * 60)
    logger.info("  Fatigue Analysis & Ergonomic Risk Assessment — Module 3")
    logger.info("═" * 60)
    logger.info("Input  : %s", pose_json)
    logger.info("Output : %s", fatigue_report)
    logger.info("Output : %s", ergo_scores)
    logger.info("FPS    : %.1f (assumed)", fps)

    # ── Load pose data ─────────────────────────────────────────────────────────
    worker_frames = _load_pose_data(pose_json)

    if not worker_frames:
        logger.warning("No worker data found in pose_data.json — nothing to analyse.")
        return

    # ── Initialise analysis components ─────────────────────────────────────────
    fatigue_detector   = FatigueDetector(fps=fps)
    ergo_analyzer      = ErgonomicAnalyzer()
    risk_classifier    = RiskClassifier()
    exporter           = ResultExporter(fatigue_report, ergo_scores)

    worker_reports:    list[WorkerReport]    = []
    ergonomic_results: list[ErgonomicResult] = []

    start = time.perf_counter()

    for worker_id in sorted(worker_frames.keys()):
        frames = worker_frames[worker_id]
        logger.info("── Worker %d: %d frames ──", worker_id, len(frames))

        # ── Step 1: compute joint angles for every frame ───────────────────────
        frame_angles = []
        for landmarks in frames:
            if not landmarks:
                # Empty frame (no pose detected) — all angles are None
                frame_angles.append({
                    "neck_angle": None, "back_angle": None,
                    "avg_knee_angle": None, "avg_shoulder_angle": None,
                    "left_knee_angle": None, "right_knee_angle": None,
                    "left_shoulder_angle": None, "right_shoulder_angle": None,
                })
            else:
                frame_angles.append(compute_all_angles(landmarks))

        # ── Step 2: fatigue analysis ───────────────────────────────────────────
        fatigue_result: FatigueResult = fatigue_detector.analyse(worker_id, frame_angles)

        # ── Step 3: ergonomic risk assessment ─────────────────────────────────
        ergo_result: ErgonomicResult = ergo_analyzer.analyse(worker_id, frame_angles)

        # ── Step 4: unified risk classification ───────────────────────────────
        report: WorkerReport = risk_classifier.classify(fatigue_result, ergo_result)

        worker_reports.append(report)
        ergonomic_results.append(ergo_result)

    # ── Export results ─────────────────────────────────────────────────────────
    exporter.export(worker_reports, ergonomic_results)

    elapsed = time.perf_counter() - start

    # ── Summary ────────────────────────────────────────────────────────────────
    logger.info("═" * 60)
    logger.info("  Analysis complete in %.2f s", elapsed)
    logger.info("  Workers analysed : %d", len(worker_reports))
    alerts = sum(1 for r in worker_reports if r.alert)
    logger.info("  Alerts raised    : %d", alerts)
    for r in worker_reports:
        logger.info(
            "  Worker %2d → fatigue=%3d (%s) | ergo=%3d (%s) | %s%s",
            r.worker_id,
            r.fatigue_score, r.fatigue_level,
            r.ergonomic_score, r.ergonomic_risk,
            r.overall_risk,
            " ⚠" if r.alert else "",
        )
    logger.info("═" * 60)


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    pose_json, fatigue_report, ergo_scores = _resolve_paths()
    fps = float(os.environ.get("VIDEO_FPS", ASSUMED_FPS))

    try:
        run_pipeline(pose_json, fatigue_report, ergo_scores, fps)
    except FileNotFoundError as exc:
        logger.error("File not found:\n%s", exc)
        sys.exit(1)
    except (ValueError, KeyError) as exc:
        logger.error("Data error:\n%s", exc)
        sys.exit(1)
    except Exception as exc:   # noqa: BLE001
        logger.exception("Unexpected error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
