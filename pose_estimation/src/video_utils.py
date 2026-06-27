"""
video_utils.py
--------------
Video writer with automatic H.264 re-encoding via ffmpeg.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class VideoWriter:

    def __init__(self, output_path: Path, width: int, height: int, fps: float) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._output_path = output_path
        self._fps = fps   # saved so ffmpeg can use it

        self._tmp_file = tempfile.NamedTemporaryFile(
            suffix=".mp4", delete=False
        )
        self._tmp_path = Path(self._tmp_file.name)
        self._tmp_file.close()

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(
            str(self._tmp_path), fourcc, fps, (width, height)
        )
        if not self._writer.isOpened():
            raise IOError(f"cv2.VideoWriter could not open '{self._tmp_path}'.")
        logger.info("VideoWriter ready → final output: '%s'", output_path.name)

    def write(self, frame: np.ndarray) -> None:
        self._writer.write(frame)

    def release(self) -> None:
        self._writer.release()

        if shutil.which("ffmpeg"):
            # ── FIX 1: add -r <fps> before -i so ffmpeg knows the input rate ──
            # Without this flag, mp4v containers with missing/corrupt timing
            # metadata cause ffmpeg to fail with a timestamp error.
            cmd = [
                "ffmpeg", "-y",
                "-r", str(int(self._fps)),   # force input framerate
                "-i", str(self._tmp_path),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-movflags", "+faststart",
                str(self._output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                size_mb = self._output_path.stat().st_size / 1_048_576
                logger.info(
                    "H.264 video saved → '%s'  (%.2f MB)",
                    self._output_path, size_mb
                )
            else:
                logger.error(
                    "ffmpeg re-encoding failed (code %d):\n%s\nFalling back to raw file.",
                    result.returncode,
                    result.stderr[-400:],
                )
                shutil.copy2(self._tmp_path, self._output_path)
        else:
            logger.warning(
                "ffmpeg not found — video may not play in all players.\n"
                "Install from https://ffmpeg.org"
            )
            shutil.copy2(self._tmp_path, self._output_path)

        try:
            os.remove(self._tmp_path)
        except OSError:
            pass

    def __enter__(self) -> "VideoWriter":
        return self

    def __exit__(self, *_) -> None:
        self.release()