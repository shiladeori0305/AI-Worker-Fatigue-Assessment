"""
angle_calculator.py
-------------------
Pure geometric functions for computing body joint angles from 2D keypoints.

Mathematical basis
~~~~~~~~~~~~~~~~~~
All angles are computed using the dot-product formula:

    Given three points A (proximal), B (vertex), C (distal):

        vector BA = A - B
        vector BC = C - B

        cos θ = (BA · BC) / (|BA| × |BC|)

        θ = arccos(cos θ)    [radians → degrees]

    This gives the interior angle at the vertex joint B,
    which corresponds to the anatomical joint angle used in
    REBA / RULA ergonomic assessment.

Coordinate system
~~~~~~~~~~~~~~~~~
All inputs are (x, y) pixel coordinates from Module 2's pose_data.json.
The y-axis points DOWNWARD (image convention).

Angles are always returned in degrees, in the range [0°, 180°].
None is returned whenever a required keypoint is missing (null in JSON).
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np


# ── Type alias ─────────────────────────────────────────────────────────────────
Point = Optional[tuple[float, float]]   # (x, y) or None


# ── Core geometry ──────────────────────────────────────────────────────────────

def angle_between_three_points(
    a: Point,
    b: Point,
    c: Point,
) -> Optional[float]:
    """
    Compute the interior angle (in degrees) at vertex B formed by A–B–C.

    Parameters
    ----------
    a : Point
        Proximal point (e.g. nose for neck angle).
    b : Point
        Vertex / joint point (e.g. shoulder center).
    c : Point
        Distal point (e.g. hip center).

    Returns
    -------
    float | None
        Angle in degrees [0, 180], or None if any point is missing or
        the vectors are degenerate (zero length).

    Examples
    --------
    >>> angle_between_three_points((0,0), (1,0), (1,1))
    90.0
    """
    if a is None or b is None or c is None:
        return None

    # Vectors from vertex B to A and C
    ba = np.array([a[0] - b[0], a[1] - b[1]], dtype=float)
    bc = np.array([c[0] - b[0], c[1] - b[1]], dtype=float)

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)

    if norm_ba < 1e-6 or norm_bc < 1e-6:
        return None   # Degenerate — points are coincident

    cos_theta = np.dot(ba, bc) / (norm_ba * norm_bc)
    # Clamp to [-1, 1] to guard against floating-point drift
    cos_theta = float(np.clip(cos_theta, -1.0, 1.0))

    return math.degrees(math.acos(cos_theta))


def midpoint(a: Point, b: Point) -> Point:
    """
    Return the midpoint between two 2-D points.

    Parameters
    ----------
    a, b : Point
        Two (x, y) coordinates.  Returns None if either is None.
    """
    if a is None or b is None:
        return None
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


# ── Named joint angles ─────────────────────────────────────────────────────────

def neck_angle(landmarks: dict) -> Optional[float]:
    """
    Neck flexion / extension angle.

    Anatomical definition
    ~~~~~~~~~~~~~~~~~~~~~
    Measured at the shoulder-center, between the line running up to the
    nose and the line running down to the hip-center.

    A value near 180° = upright head.
    Decreasing angle = increasing forward neck flexion.

    For ergonomic risk we report the DEVIATION from 180°:
        neck_deviation = 180° − raw_angle

    so that 0° = neutral and larger values indicate more flexion.

    Landmarks used: nose, left_shoulder, right_shoulder, left_hip, right_hip
    """
    nose          = landmarks.get("nose")
    left_shoulder = landmarks.get("left_shoulder")
    right_shoulder= landmarks.get("right_shoulder")
    left_hip      = landmarks.get("left_hip")
    right_hip     = landmarks.get("right_hip")

    shoulder_mid = midpoint(left_shoulder, right_shoulder)
    hip_mid      = midpoint(left_hip, right_hip)

    raw = angle_between_three_points(nose, shoulder_mid, hip_mid)
    if raw is None:
        return None
    # Convert to forward-flexion deviation (0 = neutral upright)
    return round(abs(180.0 - raw), 2)


def back_angle(landmarks: dict) -> Optional[float]:
    """
    Trunk / back flexion angle.

    Anatomical definition
    ~~~~~~~~~~~~~~~~~~~~~
    Measured at the hip-center, between the line running up to the
    shoulder-center and the line running down to the knee-center.

    A value near 180° = upright spine.
    Deviation from 180° = degree of trunk flexion.

    Landmarks used: left_shoulder, right_shoulder,
                    left_hip, right_hip,
                    left_knee, right_knee
    """
    left_shoulder = landmarks.get("left_shoulder")
    right_shoulder= landmarks.get("right_shoulder")
    left_hip      = landmarks.get("left_hip")
    right_hip     = landmarks.get("right_hip")
    left_knee     = landmarks.get("left_knee")
    right_knee    = landmarks.get("right_knee")

    shoulder_mid = midpoint(left_shoulder, right_shoulder)
    hip_mid      = midpoint(left_hip, right_hip)
    knee_mid     = midpoint(left_knee, right_knee)

    raw = angle_between_three_points(shoulder_mid, hip_mid, knee_mid)
    if raw is None:
        return None
    return round(abs(180.0 - raw), 2)


def knee_angle(landmarks: dict, side: str = "left") -> Optional[float]:
    """
    Knee flexion angle for one leg.

    Anatomical definition
    ~~~~~~~~~~~~~~~~~~~~~
    Measured at the knee, between hip → knee → ankle.
    180° = fully extended leg.
    Deviation from 180° = degree of knee flexion.

    Parameters
    ----------
    side : str
        "left" or "right".
    """
    hip   = landmarks.get(f"{side}_hip")
    knee  = landmarks.get(f"{side}_knee")
    ankle = landmarks.get(f"{side}_ankle")

    raw = angle_between_three_points(hip, knee, ankle)
    if raw is None:
        return None
    return round(abs(180.0 - raw), 2)


def shoulder_angle(landmarks: dict, side: str = "left") -> Optional[float]:
    """
    Shoulder elevation angle for one arm.

    Anatomical definition
    ~~~~~~~~~~~~~~~~~~~~~
    Measured at the shoulder, between elbow → shoulder → hip.
    0° = arm hanging straight down (neutral).
    Larger values = greater arm elevation.

    Parameters
    ----------
    side : str
        "left" or "right".
    """
    elbow    = landmarks.get(f"{side}_elbow")
    shoulder = landmarks.get(f"{side}_shoulder")
    hip      = landmarks.get(f"{side}_hip")

    raw = angle_between_three_points(elbow, shoulder, hip)
    if raw is None:
        return None
    return round(abs(180.0 - raw), 2)


# ── Frame-level angle bundle ───────────────────────────────────────────────────

def compute_all_angles(landmarks: dict) -> dict[str, Optional[float]]:
    """
    Compute all joint angles for one frame's landmark set.

    Parameters
    ----------
    landmarks : dict
        Landmark dict from pose_data.json.
        Values may be dicts ``{"x": int, "y": int, ...}`` or None.

    Returns
    -------
    dict[str, float | None]
        Keys: neck_angle, back_angle, left_knee_angle, right_knee_angle,
              left_shoulder_angle, right_shoulder_angle,
              avg_knee_angle, avg_shoulder_angle
    """
    # Normalise: accept both {"x":…,"y":…} dicts and bare [x,y] lists
    def to_point(v) -> Point:
        if v is None:
            return None
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            return (float(v[0]), float(v[1]))
        if isinstance(v, dict) and "x" in v and "y" in v:
            return (float(v["x"]), float(v["y"]))
        return None

    kp = {k: to_point(v) for k, v in landmarks.items()}

    l_knee = knee_angle(kp, "left")
    r_knee = knee_angle(kp, "right")
    l_sho  = shoulder_angle(kp, "left")
    r_sho  = shoulder_angle(kp, "right")

    # Average bilateral angles; fall back to whichever side is available
    def safe_avg(a, b):
        vals = [x for x in (a, b) if x is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    return {
        "neck_angle":          neck_angle(kp),
        "back_angle":          back_angle(kp),
        "left_knee_angle":     l_knee,
        "right_knee_angle":    r_knee,
        "left_shoulder_angle": l_sho,
        "right_shoulder_angle":r_sho,
        "avg_knee_angle":      safe_avg(l_knee, r_knee),
        "avg_shoulder_angle":  safe_avg(l_sho,  r_sho),
    }
