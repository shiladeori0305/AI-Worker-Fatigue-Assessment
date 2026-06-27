"""
main.py
-------
Entry point for Module 1: Worker Detection and Tracking.

Orchestrates:
    1. Video reading (VideoReader)
    2. Worker detection + ByteTrack tracking (WorkerTracker)
    3. Frame annotation (FrameAnnotator)
    4. Annotated video output (VideoWriter)
    5. JSON tracking-data export (TrackingDataExporter)

Run from the project root:
    python main.py

Optional overrides via environment variables:
    INPUT_VIDEO   — path to input video (overrides config.INPUT_VIDEO_PATH)
    OUTPUT_VIDEO  — path to output video (overrides config.OUTPUT_VIDEO_PATH)
    TRACKING_JSON — path to tracking JSON (overrides config.TRACKING_DATA_PATH)
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

from src.config import (
    FRAME_SKIP,
    FRAME_SKIP_INTERVAL,
    INPUT_VIDEO_PATH,
    OUTPUT_FPS,
    OUTPUT_VIDEO_PATH,
    TRACKING_DATA_PATH,
)
from src.tracker import WorkerTracker
from src.video_utils import (
    FrameAnnotator,
    TrackingDataExporter,
    VideoReader,
    VideoWriter,
)

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Path resolution (allow env-var overrides) ──────────────────────────────────
def _resolve_paths() -> tuple[Path, Path, Path]:
    input_video = Path(os.environ.get("INPUT_VIDEO", INPUT_VIDEO_PATH))
    output_video = Path(os.environ.get("OUTPUT_VIDEO", OUTPUT_VIDEO_PATH))
    tracking_json = Path(os.environ.get("TRACKING_JSON", TRACKING_DATA_PATH))
    return input_video, output_video, tracking_json


# ── Pipeline ───────────────────────────────────────────────────────────────────

def run_pipeline(
    input_video: Path,
    output_video: Path,
    tracking_json: Path,
) -> None:
    """
    Execute the full detection-and-tracking pipeline.

    Parameters
    ----------
    input_video : Path
        Source CCTV / test video.
    output_video : Path
        Destination for the annotated video.
    tracking_json : Path
        Destination for the JSON tracking export.
    """
    logger.info("═" * 60)
    logger.info("  Worker Detection & Tracking — Module 1")
    logger.info("═" * 60)
    logger.info("Input  : %s", input_video)
    logger.info("Output : %s", output_video)
    logger.info("JSON   : %s", tracking_json)

    # ── Initialise components ──────────────────────────────────────────────────
    tracker = WorkerTracker()                        # Loads YOLOv8 + ByteTrack
    annotator = FrameAnnotator()
    exporter = TrackingDataExporter(tracking_json)

    with VideoReader(input_video) as reader:
        fps_out = OUTPUT_FPS if OUTPUT_FPS else reader.fps
        with VideoWriter(output_video, reader.width, reader.height, fps_out) as writer:

            pipeline_start = time.perf_counter()
            processed_frames = 0
            total_workers_detected = 0

            try:
                for frame_index, frame in reader.frames():

                    # ── Optional frame skipping for performance ────────────────
                    if FRAME_SKIP and (frame_index % FRAME_SKIP_INTERVAL != 0):
                        writer.write(frame)   # write unannotated duplicate
                        continue

                    # ── Detection + tracking ───────────────────────────────────
                    tracked_workers = tracker.track(frame)

                    # ── Record data for JSON export ────────────────────────────
                    exporter.record(frame_index, tracked_workers)

                    # ── Annotate and write frame ───────────────────────────────
                    annotated = annotator.annotate(frame, tracked_workers)
                    writer.write(annotated)

                    processed_frames += 1
                    total_workers_detected += len(tracked_workers)

                    # ── Progress log every 100 frames ──────────────────────────
                    if frame_index % 100 == 0:
                        elapsed = time.perf_counter() - pipeline_start
                        throughput = processed_frames / elapsed if elapsed > 0 else 0
                        logger.info(
                            "Frame %5d | workers: %2d | throughput: %.1f fps",
                            frame_index,
                            len(tracked_workers),
                            throughput,
                        )

            except KeyboardInterrupt:
                logger.warning("Interrupted by user — saving partial results.")

    # ── Export JSON ────────────────────────────────────────────────────────────
    exporter.save()

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed_total = time.perf_counter() - pipeline_start
    avg_fps = processed_frames / elapsed_total if elapsed_total > 0 else 0
    logger.info("═" * 60)
    logger.info("  Pipeline complete")
    logger.info("  Frames processed : %d", processed_frames)
    logger.info("  Total detections : %d", total_workers_detected)
    logger.info("  Elapsed time     : %.2f s", elapsed_total)
    logger.info("  Average FPS      : %.1f", avg_fps)
    logger.info("  Output video     : %s", output_video)
    logger.info("  Tracking JSON    : %s", tracking_json)
    logger.info("═" * 60)


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    """Resolve paths, validate environment, and run the pipeline."""
    input_video, output_video, tracking_json = _resolve_paths()

    try:
        run_pipeline(input_video, output_video, tracking_json)
    except FileNotFoundError as exc:
        logger.error("File not found:\n%s", exc)
        sys.exit(1)
    except IOError as exc:
        logger.error("I/O error:\n%s", exc)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()