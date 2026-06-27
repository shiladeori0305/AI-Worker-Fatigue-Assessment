"""
json_exporter.py
----------------
Accumulates per-frame pose records and writes them to a JSON file.

Output Schema
~~~~~~~~~~~~~
The exported JSON is the interface contract between Module 2 (Pose Estimation)
and Module 3 (Fatigue Feature Extraction / Ergonomic Scoring).

[
  {
    "frame": 1,
    "workers": [
      {
        "worker_id": 1,
        "pose_detected": true,
        "keypoints": {
          "nose":           {"x": 320, "y": 110, "z": -0.12, "visibility": 0.99},
          "left_shoulder":  {"x": 290, "y": 180, "z": -0.08, "visibility": 0.97},
          "right_shoulder": {"x": 350, "y": 180, "z": -0.09, "visibility": 0.96},
          "left_elbow":     null,
          ...
          "right_foot_index": {"x": 370, "y": 460, "z": 0.02, "visibility": 0.88}
        }
      }
    ]
  },
  ...
]

Notes for Module 3
~~~~~~~~~~~~~~~~~~
- All coordinate values (x, y) are in full-frame pixel space.
- z is MediaPipe's depth estimate (negative = closer to camera).
- A null keypoint value means the landmark was not visible (visibility < MIN_VISIBILITY).
- pose_detected=false means MediaPipe found no person in the crop; all keypoints will be absent.
- Frames where no workers appear still produce a record (empty workers list).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.pose_estimator import WorkerPose

logger = logging.getLogger(__name__)


class PoseDataExporter:
    """
    Buffers per-frame pose records and flushes them to a JSON file.

    Parameters
    ----------
    output_path : Path
        Destination for the JSON file.
    """

    def __init__(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._output_path = output_path
        self._records: list[dict] = []

    def record(
        self,
        frame_index: int,
        worker_poses: list[WorkerPose],
    ) -> None:
        """
        Append one frame's pose data to the internal buffer.

        Parameters
        ----------
        frame_index : int
            1-based frame number (matches Module 1's tracking_data.json).
        worker_poses : list[WorkerPose]
            Pose estimation results for all workers in this frame.
        """
        self._records.append(
            {
                "frame": frame_index,
                "workers": [wp.to_dict() for wp in worker_poses],
            }
        )

    def save(self) -> None:
        """Flush the buffer to disk as a formatted JSON file."""
        with open(self._output_path, "w", encoding="utf-8") as fh:
            json.dump(self._records, fh, indent=2)
        logger.info(
            "Pose data saved → '%s'  (%d frames, %d total worker records)",
            self._output_path,
            len(self._records),
            sum(len(r["workers"]) for r in self._records),
        )

    @property
    def record_count(self) -> int:
        """Number of frame records accumulated so far."""
        return len(self._records)
