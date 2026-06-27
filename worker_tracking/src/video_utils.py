"""
video_utils.py
--------------
Video I/O, frame annotation, and tracking-data export.

Responsibilities
~~~~~~~~~~~~~~~~
* VideoReader  — safe wrapper around cv2.VideoCapture.
* VideoWriter  — safe wrapper around cv2.VideoWriter.
* FrameAnnotator — draws bounding boxes, IDs, confidence, and FPS.
* TrackingDataExporter — accumulates per-frame records and writes JSON.

None of these classes import from detector.py or tracker.py directly;
they accept plain Python types (lists, dicts, TrackedWorker) to stay
loosely coupled and easily testable.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Generator

import cv2
import numpy as np

from src.config import (
    BOX_COLOR,
    BOX_THICKNESS,
    FONT_SCALE,
    FONT_THICKNESS,
    FPS_TEXT_COLOR,
    LABEL_PADDING,
    OUTPUT_CODEC,
    OUTPUT_FPS,
    TEXT_COLOR,
)

logger = logging.getLogger(__name__)


# ── VideoReader ────────────────────────────────────────────────────────────────

class VideoReader:
    """
    Wraps cv2.VideoCapture with validation and a clean generator interface.

    Parameters
    ----------
    video_path : Path
        Path to the input video file.

    Raises
    ------
    FileNotFoundError
        If the video file does not exist.
    IOError
        If OpenCV cannot open the file (codec, corruption, etc.).
    """

    def __init__(self, video_path: Path) -> None:
        resolved = video_path.resolve()
        if not resolved.exists():
            raise FileNotFoundError(
                f"Input video not found: '{resolved}'\n"
                "Place a video file at input/sample_video.mp4 (or update "
                "INPUT_VIDEO_PATH in src/config.py)."
            )

        self._cap = cv2.VideoCapture(str(resolved))
        if not self._cap.isOpened():
            raise IOError(
                f"OpenCV could not open '{resolved}'.  "
                "Check that the file is a valid video and the codec is installed."
            )

        self._path = resolved
        logger.info(
            "Opened video '%s' — %dx%d @ %.2f fps, %d total frames",
            resolved.name,
            self.width,
            self.height,
            self.fps,
            self.total_frames,
        )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def width(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def height(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    @property
    def fps(self) -> float:
        return self._cap.get(cv2.CAP_PROP_FPS)

    @property
    def total_frames(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # ── Frame iteration ────────────────────────────────────────────────────────

    def frames(self) -> Generator[tuple[int, np.ndarray], None, None]:
        """
        Yield ``(frame_index, bgr_frame)`` tuples until the video ends.

        frame_index is 1-based to match typical frame-number conventions.
        """
        frame_index = 0
        while True:
            ret, frame = self._cap.read()
            if not ret:
                break
            frame_index += 1
            yield frame_index, frame

    # ── Cleanup ────────────────────────────────────────────────────────────────

    def release(self) -> None:
        """Release the underlying VideoCapture."""
        self._cap.release()
        logger.debug("VideoReader released for '%s'.", self._path.name)

    def __enter__(self) -> "VideoReader":
        return self

    def __exit__(self, *_) -> None:
        self.release()


# ── VideoWriter ────────────────────────────────────────────────────────────────

class VideoWriter:
    """
    Wraps cv2.VideoWriter with automatic directory creation.

    Parameters
    ----------
    output_path : Path
        Destination path for the annotated output video.
    width : int
        Frame width (must match source video).
    height : int
        Frame height (must match source video).
    fps : float
        Output video frame rate.
    """

    def __init__(
        self,
        output_path: Path,
        width: int,
        height: int,
        fps: float,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*OUTPUT_CODEC)
        self._writer = cv2.VideoWriter(
            str(output_path), fourcc, fps, (width, height)
        )
        if not self._writer.isOpened():
            raise IOError(
                f"cv2.VideoWriter could not open '{output_path}'.  "
                f"Check that the codec '{OUTPUT_CODEC}' is available."
            )
        logger.info("VideoWriter ready → '%s'", output_path)

    def write(self, frame: np.ndarray) -> None:
        """Write a single annotated frame to the output file."""
        self._writer.write(frame)

    def release(self) -> None:
        """Flush and close the output file."""
        self._writer.release()
        logger.debug("VideoWriter released.")

    def __enter__(self) -> "VideoWriter":
        return self

    def __exit__(self, *_) -> None:
        self.release()


# ── FrameAnnotator ─────────────────────────────────────────────────────────────

class FrameAnnotator:
    """
    Draws bounding boxes, worker IDs, confidence scores, and FPS on a frame.

    All drawing is done in-place on the provided numpy array (no copy).
    """

    def __init__(self) -> None:
        self._font = cv2.FONT_HERSHEY_SIMPLEX
        # FPS smoothing: rolling window of wall-clock timestamps
        self._timestamps: list[float] = []
        self._fps_window: int = 30   # average over last 30 frames

    # ── Private helpers ────────────────────────────────────────────────────────

    def _draw_label(
        self,
        frame: np.ndarray,
        text: str,
        x1: int,
        y1: int,
    ) -> None:
        """
        Draw a filled rectangle behind ``text`` at the top-left of a bounding box.

        Parameters
        ----------
        frame : np.ndarray
            Frame to annotate (modified in-place).
        text : str
            Label text to render.
        x1, y1 : int
            Top-left corner of the bounding box.
        """
        (text_w, text_h), baseline = cv2.getTextSize(
            text, self._font, FONT_SCALE, FONT_THICKNESS
        )
        pad = LABEL_PADDING
        rect_x1 = x1
        rect_y1 = max(y1 - text_h - baseline - pad * 2, 0)
        rect_x2 = x1 + text_w + pad * 2
        rect_y2 = y1

        # Filled background rectangle for readability
        cv2.rectangle(frame, (rect_x1, rect_y1), (rect_x2, rect_y2), BOX_COLOR, -1)
        cv2.putText(
            frame,
            text,
            (x1 + pad, y1 - baseline - pad),
            self._font,
            FONT_SCALE,
            TEXT_COLOR,
            FONT_THICKNESS,
            cv2.LINE_AA,
        )

    def _current_fps(self) -> float:
        """Return a smoothed FPS estimate based on recent frame timestamps."""
        now = time.perf_counter()
        self._timestamps.append(now)
        # Keep only the last N timestamps
        if len(self._timestamps) > self._fps_window:
            self._timestamps.pop(0)
        if len(self._timestamps) < 2:
            return 0.0
        elapsed = self._timestamps[-1] - self._timestamps[0]
        return (len(self._timestamps) - 1) / elapsed if elapsed > 0 else 0.0

    # ── Public interface ───────────────────────────────────────────────────────

    def annotate(
        self,
        frame: np.ndarray,
        tracked_workers: list,   # list[TrackedWorker] — avoid circular import
    ) -> np.ndarray:
        """
        Draw all tracking overlays on a BGR frame.

        Parameters
        ----------
        frame : np.ndarray
            BGR frame (modified in-place and also returned).
        tracked_workers : list[TrackedWorker]
            Workers detected in this frame.

        Returns
        -------
        np.ndarray
            The annotated frame (same array, returned for convenience).
        """
        for worker in tracked_workers:
            x1, y1, x2, y2 = worker.bbox

            # Bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, BOX_THICKNESS)

            # Label: "ID:3  0.94"
            label = f"ID:{worker.worker_id}  {worker.confidence:.2f}"
            self._draw_label(frame, label, x1, y1)

        # FPS counter — top-left corner of the frame
        fps = self._current_fps()
        fps_text = f"FPS: {fps:.1f}"
        cv2.putText(
            frame,
            fps_text,
            (10, 28),
            self._font,
            0.70,
            FPS_TEXT_COLOR,
            2,
            cv2.LINE_AA,
        )

        # Worker count — next line below FPS
        count_text = f"Workers: {len(tracked_workers)}"
        cv2.putText(
            frame,
            count_text,
            (10, 56),
            self._font,
            0.65,
            FPS_TEXT_COLOR,
            1,
            cv2.LINE_AA,
        )

        return frame


# ── TrackingDataExporter ───────────────────────────────────────────────────────

class TrackingDataExporter:
    """
    Accumulates per-frame tracking records and writes them to a JSON file.

    The exported schema is::

        [
          {
            "frame": 1,
            "workers": [
              {"id": 1, "bbox": [x1, y1, x2, y2], "confidence": 0.95},
              ...
            ]
          },
          ...
        ]

    This schema is the interface contract between Module 1 (this module) and
    Module 2 (Pose Estimation / MediaPipe).  Do not change it without updating
    the downstream consumer.

    Parameters
    ----------
    output_path : Path
        Destination path for the JSON file.
    """

    def __init__(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._output_path = output_path
        self._records: list[dict] = []

    def record(self, frame_index: int, tracked_workers: list) -> None:
        """
        Append one frame's tracking data to the internal buffer.

        Parameters
        ----------
        frame_index : int
            1-based frame number.
        tracked_workers : list[TrackedWorker]
            All tracked workers in this frame.
        """
        self._records.append(
            {
                "frame": frame_index,
                "workers": [w.to_dict() for w in tracked_workers],
            }
        )

    def save(self) -> None:
        """Flush the buffer to disk as a formatted JSON file."""
        with open(self._output_path, "w", encoding="utf-8") as fh:
            json.dump(self._records, fh, indent=2)
        logger.info(
            "Tracking data saved → '%s'  (%d frames)",
            self._output_path,
            len(self._records),
        )

    @property
    def record_count(self) -> int:
        """Number of frame records accumulated so far."""
        return len(self._records)
