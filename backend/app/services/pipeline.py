"""Glue between the API and the ML package: run the full analysis for one video."""
from __future__ import annotations

import datetime as dt
import logging
from functools import lru_cache

from sqlalchemy.orm import Session

from ml.congestion_model import CongestionModel
from ml.emission_estimation import estimate_emissions
from ml.sustainability import assess_sustainability
from ml.vehicle_detection import VehicleDetector, analyze_video

from ..config import settings
from ..models import Analysis, Video

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_model() -> CongestionModel:
    return CongestionModel(settings.model_path)


def new_detector() -> VehicleDetector:
    # Detector keeps per-video state (background model), so create one per run.
    return VehicleDetector(backend=settings.detector_backend, model_path=settings.yolo_weights)


def run_analysis(db: Session, analysis_id: int) -> Analysis:
    analysis = db.get(Analysis, analysis_id)
    video: Video = analysis.video
    analysis.status = "running"
    db.commit()
    try:
        det = new_detector()
        stats = analyze_video(video.stored_path, det, settings.frame_sample_every, settings.max_frames).to_dict()
        pred = get_model().predict_from_stats(stats, dt.datetime.now())
        emis = estimate_emissions(stats, pred["level"], settings.road_segment_km)
        sustain = assess_sustainability(emis["co2_kg_per_hour"], settings.carbon_limit_kg_per_hour)

        video.duration_s = stats["duration_s"]
        analysis.detector_backend = stats["backend"]
        analysis.avg_vehicles = stats["avg_vehicles_per_frame"]
        analysis.max_vehicles = stats["max_vehicles_per_frame"]
        analysis.congestion_level = pred["level"]
        analysis.congestion_confidence = pred["confidence"]
        analysis.co2_kg_per_hour = emis["co2_kg_per_hour"]
        analysis.details = {"stats": stats, "prediction": pred, "emissions": emis,
                            "sustainability": sustain}
        analysis.status = "done"
    except Exception as exc:  # noqa: BLE001
        log.exception("analysis %s failed", analysis_id)
        analysis.status = "failed"
        analysis.error = str(exc)[:2000]
    db.commit()
    db.refresh(analysis)
    return analysis
