"""
main.py
-------
Entry point for Module 2: Pose Estimation and Keypoint Extraction.

Run from the project root:
    python main.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

import cv2

from src.config import (
    INPUT_VIDEO_PATH,
    OUTPUT_FPS,
    OUTPUT_VIDEO_PATH,
    POSE_DATA_PATH,
    TRACKING_DATA_PATH,
)
from src.json_exporter import PoseDataExporter
from src.pose_estimator import PoseEstimator
from src.skeleton_drawer import SkeletonDrawer
from src.video_utils import VideoWriter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _resolve_paths() -> tuple[Path, Path, Path, Path]:
    return (
        Path(os.environ.get("INPUT_VIDEO",   INPUT_VIDEO_PATH)),
        Path(os.environ.get("TRACKING_JSON", TRACKING_DATA_PATH)),
        Path(os.environ.get("OUTPUT_VIDEO",  OUTPUT_VIDEO_PATH)),
        Path(os.environ.get("POSE_JSON",     POSE_DATA_PATH)),
    )


def _load_tracking_data(json_path: Path) -> dict[int, list[dict]]:
    if not json_path.exists():
        raise FileNotFoundError(
            f"Tracking data not found: '{json_path}'\n"
            "Copy tracking_data.json from Module 1's output/ into input/."
        )
    with open(json_path, encoding="utf-8") as fh:
        try:
            raw: list[dict] = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse '{json_path}': {exc}") from exc

    indexed: dict[int, list[dict]] = {
        int(r["frame"]): r.get("workers", []) for r in raw
    }
    logger.info(
        "Tracking data loaded: %d frames, %d total worker records.",
        len(indexed),
        sum(len(v) for v in indexed.values()),
    )
    return indexed


def _open_video(video_path: Path) -> cv2.VideoCapture:
    if not video_path.exists():
        raise FileNotFoundError(
            f"Input video not found: '{video_path}'\n"
            "Copy tracked_video.mp4 from Module 1's output/ into input/."
        )
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IOError(f"OpenCV could not open '{video_path}'.")
    return cap


def run_pipeline(
    input_video: Path,
    tracking_json: Path,
    output_video: Path,
    pose_json: Path,
) -> None:
    logger.info("═" * 60)
    logger.info("  Pose Estimation & Keypoint Extraction — Module 2")
    logger.info("═" * 60)
    logger.info("Input video   : %s", input_video)
    logger.info("Tracking JSON : %s", tracking_json)
    logger.info("Output video  : %s", output_video)
    logger.info("Pose JSON     : %s", pose_json)

    tracking_index = _load_tracking_data(tracking_json)

    cap = _open_video(input_video)
    width       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    src_fps     = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_out     = OUTPUT_FPS if OUTPUT_FPS else src_fps

    logger.info("Video: %dx%d @ %.2f fps, %d frames", width, height, src_fps, total_frames)

    exporter = PoseDataExporter(pose_json)
    drawer   = SkeletonDrawer()

    # VideoWriter handles the mp4v → H.264 re-encode on close
    with PoseEstimator() as estimator, VideoWriter(output_video, width, height, fps_out) as writer:
        pipeline_start = time.perf_counter()
        frame_index    = 0
        poses_detected = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_index += 1
                workers = tracking_index.get(frame_index, [])

                worker_poses = estimator.estimate(frame, workers)
                poses_detected += sum(1 for wp in worker_poses if wp.pose_detected)

                exporter.record(frame_index, worker_poses)

                annotated = drawer.draw(frame, worker_poses)
                writer.write(annotated)

                if frame_index % 100 == 0:
                    elapsed  = time.perf_counter() - pipeline_start
                    fps_live = frame_index / elapsed if elapsed > 0 else 0
                    logger.info(
                        "Frame %5d/%d | workers: %2d | throughput: %.1f fps",
                        frame_index, total_frames, len(worker_poses), fps_live,
                    )

        except KeyboardInterrupt:
            logger.warning("Interrupted — saving partial results.")

    cap.release()
    exporter.save()

    elapsed_total = time.perf_counter() - pipeline_start
    logger.info("═" * 60)
    logger.info("  Pipeline complete")
    logger.info("  Frames processed   : %d", frame_index)
    logger.info("  Poses detected     : %d", poses_detected)
    logger.info("  Elapsed time       : %.2f s", elapsed_total)
    logger.info("  Average throughput : %.1f fps", frame_index / elapsed_total if elapsed_total else 0)
    logger.info("  Output video       : %s", output_video)
    logger.info("  Pose JSON          : %s", pose_json)
    logger.info("═" * 60)


def main() -> None:
    input_video, tracking_json, output_video, pose_json = _resolve_paths()
    try:
        run_pipeline(input_video, tracking_json, output_video, pose_json)
    except FileNotFoundError as exc:
        logger.error("File not found:\n%s", exc)
        sys.exit(1)
    except (IOError, ValueError) as exc:
        logger.error("Error:\n%s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()