"""Generate synthetic traffic clips (rectangles moving on a road) for dev/testing.

    python data/make_sample_video.py            # writes data/sample/{light,heavy}_traffic.mp4
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

OUT = Path(__file__).resolve().parent / "sample"


def make(path: Path, n_vehicles: int, seconds: int = 8, fps: int = 25, w: int = 640, h: int = 360, seed: int = 1):
    rng = np.random.default_rng(seed)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    lanes = [h * 0.35, h * 0.5, h * 0.65, h * 0.8]
    cars = []
    for i in range(n_vehicles):
        size = rng.choice([(40, 22), (18, 10), (90, 30), (70, 30)], p=[0.6, 0.2, 0.1, 0.1])
        cars.append({"x": rng.uniform(-w, w), "y": float(rng.choice(lanes)), "v": rng.uniform(2, 6) * (1 if i % 2 else -1),
                     "w": int(size[0]), "h": int(size[1]),
                     "color": tuple(int(c) for c in rng.integers(60, 255, 3))})
    for f in range(seconds * fps):
        frame = np.full((h, w, 3), (70, 70, 70), np.uint8)
        frame[: int(h * 0.25)] = (170, 200, 230)  # sky
        for ly in lanes:
            cv2.line(frame, (0, int(ly) + 18), (w, int(ly) + 18), (200, 200, 200), 1, cv2.LINE_AA)
        for c in cars:
            c["x"] = (c["x"] + c["v"]) % (w + 200) - 100
            x, y = int(c["x"]), int(c["y"])
            cv2.rectangle(frame, (x, y), (x + c["w"], y + c["h"]), c["color"], -1)
        noise = rng.integers(0, 6, (h, w, 3), dtype=np.uint8)
        frame = cv2.add(frame, noise)
        vw.write(frame)
    vw.release()
    print("wrote", path)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    make(OUT / "light_traffic.mp4", 4, seed=1)
    make(OUT / "heavy_traffic.mp4", 22, seed=2)
