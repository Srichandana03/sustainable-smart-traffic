"""Vehicle detection from traffic video.

Two backends:
  * ``yolo``   – Ultralytics YOLOv8 (COCO classes car/motorcycle/bus/truck). Used when
                 the ``ultralytics`` package is installed. Recommended for real deployments.
  * ``opencv`` – Background-subtraction (MOG2) + contour analysis. No deep-learning
                 dependency; useful for dev machines, CI and as a safety fallback.

Both produce the same ``FrameResult`` objects so the rest of the pipeline is backend-agnostic.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterator, Literal

import cv2
import numpy as np

log = logging.getLogger(__name__)

VehicleClass = Literal["car", "motorcycle", "bus", "truck"]
VEHICLE_CLASSES: tuple[VehicleClass, ...] = ("car", "motorcycle", "bus", "truck")

# COCO ids used by YOLOv8 pretrained weights
COCO_VEHICLES: dict[int, VehicleClass] = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


@dataclass
class Detection:
    cls: VehicleClass
    conf: float
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def area(self) -> int:
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)


@dataclass
class FrameResult:
    frame_index: int
    timestamp_s: float
    detections: list[Detection] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.detections)

    def counts_by_class(self) -> dict[str, int]:
        out = {c: 0 for c in VEHICLE_CLASSES}
        for d in self.detections:
            out[d.cls] += 1
        return out


@dataclass
class VideoStats:
    """Aggregate statistics produced from a whole video."""

    source: str
    backend: str
    frames_total: int
    frames_analyzed: int
    fps: float
    duration_s: float
    width: int
    height: int
    avg_vehicles_per_frame: float
    max_vehicles_per_frame: int
    counts_by_class: dict[str, float]      # average per analyzed frame
    total_by_class: dict[str, int]         # summed across analyzed frames
    density: float                         # fraction of frame area covered by vehicle boxes (avg)
    avg_speed_px_s: float                  # crude optical-flow-derived motion estimate
    per_frame_counts: list[int]

    def to_dict(self) -> dict:
        return asdict(self)


class VehicleDetector:
    def __init__(self, backend: Literal["auto", "yolo", "opencv"] = "auto",
                 model_path: str = "yolov8n.pt", conf: float = 0.35, device: str = "cpu"):
        self.conf = conf
        self.backend = backend
        self._yolo = None
        if backend in ("auto", "yolo"):
            try:
                from ultralytics import YOLO  # type: ignore

                self._yolo = YOLO(model_path)
                self._device = device
                self.backend = "yolo"
                log.info("Using YOLO backend (%s)", model_path)
            except Exception as exc:  # ImportError or weight download failure
                if backend == "yolo":
                    raise
                log.warning("YOLO unavailable (%s); falling back to OpenCV detector", exc)
                self.backend = "opencv"
        if self.backend == "opencv":
            self._bg = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=40, detectShadows=True)

    # ------------------------------------------------------------------ backends
    def _detect_yolo(self, frame: np.ndarray) -> list[Detection]:
        res = self._yolo.predict(frame, conf=self.conf, device=self._device, verbose=False)[0]
        out: list[Detection] = []
        for box in res.boxes:
            cid = int(box.cls.item())
            if cid not in COCO_VEHICLES:
                continue
            x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
            out.append(Detection(COCO_VEHICLES[cid], float(box.conf.item()), x1, y1, x2, y2))
        return out

    def _detect_opencv(self, frame: np.ndarray) -> list[Detection]:
        h, w = frame.shape[:2]
        mask = self._bg.apply(frame)
        _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)  # drop shadows (127)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = 0.0015 * w * h
        out: list[Detection] = []
        frame_area = float(w * h)
        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            rel = area / frame_area
            # crude size-based class heuristic
            if rel < 0.004:
                cls: VehicleClass = "motorcycle"
            elif rel < 0.02:
                cls = "car"
            elif bw > bh * 1.6:
                cls = "bus"
            else:
                cls = "truck"
            out.append(Detection(cls, min(0.99, 0.4 + rel * 10), x, y, x + bw, y + bh))
        return out

    def detect(self, frame: np.ndarray) -> list[Detection]:
        if self.backend == "yolo":
            return self._detect_yolo(frame)
        return self._detect_opencv(frame)

    # ------------------------------------------------------------------ video
    def iter_video(self, path: str | Path, sample_every: int = 5, max_frames: int | None = None
                   ) -> Iterator[tuple[FrameResult, np.ndarray]]:
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise FileNotFoundError(f"Cannot open video: {path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        idx = analyzed = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if self.backend == "opencv":
                    # background model needs every frame
                    dets = self._detect_opencv(frame) if idx % sample_every == 0 else None
                    if idx % sample_every != 0:
                        self._bg.apply(frame)
                else:
                    dets = self.detect(frame) if idx % sample_every == 0 else None
                if dets is not None:
                    yield FrameResult(idx, idx / fps, dets), frame
                    analyzed += 1
                    if max_frames and analyzed >= max_frames:
                        break
                idx += 1
        finally:
            cap.release()


def _motion_estimate(prev: np.ndarray | None, cur: np.ndarray, dt: float) -> float:
    """Mean magnitude of dense optical flow in px/s (rough proxy for traffic speed)."""
    if prev is None or dt <= 0:
        return 0.0
    g0 = cv2.cvtColor(cv2.resize(prev, (320, 180)), cv2.COLOR_BGR2GRAY)
    g1 = cv2.cvtColor(cv2.resize(cur, (320, 180)), cv2.COLOR_BGR2GRAY)
    flow = cv2.calcOpticalFlowFarneback(g0, g1, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    mag = np.linalg.norm(flow, axis=2)
    moving = mag[mag > 0.5]
    if moving.size == 0:
        return 0.0
    scale = cur.shape[1] / 320.0
    return float(moving.mean() * scale / dt)


def analyze_video(path: str | Path, detector: VehicleDetector | None = None,
                  sample_every: int = 5, max_frames: int | None = 120) -> VideoStats:
    detector = detector or VehicleDetector()
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    per_frame: list[int] = []
    cls_totals = {c: 0 for c in VEHICLE_CLASSES}
    densities: list[float] = []
    speeds: list[float] = []
    prev_frame, prev_t = None, 0.0
    frame_area = float(w * h) or 1.0

    for fr, frame in detector.iter_video(path, sample_every=sample_every, max_frames=max_frames):
        per_frame.append(fr.count)
        for c, n in fr.counts_by_class().items():
            cls_totals[c] += n
        densities.append(sum(d.area for d in fr.detections) / frame_area)
        speeds.append(_motion_estimate(prev_frame, frame, fr.timestamp_s - prev_t))
        prev_frame, prev_t = frame, fr.timestamp_s

    n = max(1, len(per_frame))
    return VideoStats(
        source=str(path),
        backend=detector.backend,
        frames_total=total,
        frames_analyzed=len(per_frame),
        fps=float(fps),
        duration_s=total / fps if fps else 0.0,
        width=w, height=h,
        avg_vehicles_per_frame=float(np.mean(per_frame)) if per_frame else 0.0,
        max_vehicles_per_frame=int(max(per_frame)) if per_frame else 0,
        counts_by_class={c: v / n for c, v in cls_totals.items()},
        total_by_class=cls_totals,
        density=float(np.mean(densities)) if densities else 0.0,
        avg_speed_px_s=float(np.mean(speeds[1:])) if len(speeds) > 1 else 0.0,
        per_frame_counts=per_frame,
    )
