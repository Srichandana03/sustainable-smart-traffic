import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ml.forecasting import forecast_congestion
from ml.hotspots import rank_hotspots

from ..config import settings
from ..database import get_db
from ..models import Analysis, User, Video
from ..schemas import AnalysisOut, ForecastPoint, HotspotOut, SummaryOut
from ..services.auth import get_current_user
from ..services.pipeline import get_model, run_analysis

router = APIRouter(prefix="/api", tags=["analysis"])
ALLOWED = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def _to_out(a: Analysis) -> AnalysisOut:
    v = a.video
    return AnalysisOut(
        id=a.id, video_id=v.id, status=a.status, location=v.location, latitude=v.latitude,
        longitude=v.longitude, filename=v.filename, detector_backend=a.detector_backend,
        avg_vehicles=a.avg_vehicles, max_vehicles=a.max_vehicles, congestion_level=a.congestion_level,
        congestion_confidence=a.congestion_confidence, co2_kg_per_hour=a.co2_kg_per_hour,
        details=a.details, error=a.error, created_at=a.created_at,
    )


@router.post("/analyze", response_model=AnalysisOut, status_code=201)
def analyze(
    file: UploadFile = File(...),
    location: str = Form(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a traffic video and run detection → congestion → emissions synchronously."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"Unsupported file type {ext!r}; allowed: {sorted(ALLOWED)}")
    dest = settings.upload_dir / f"{uuid.uuid4().hex}{ext}"
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)

    video = Video(owner_id=user.id, filename=file.filename, stored_path=str(dest),
                  location=location.strip(), latitude=latitude, longitude=longitude)
    db.add(video)
    db.flush()
    analysis = Analysis(video_id=video.id)
    db.add(analysis)
    db.commit()
    analysis = run_analysis(db, analysis.id)
    return _to_out(analysis)


@router.get("/analyses", response_model=list[AnalysisOut])
def list_analyses(limit: int = 50, location: str | None = None,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Analysis).join(Video)
    if location:
        q = q.filter(Video.location == location)
    rows = q.order_by(Analysis.created_at.desc()).limit(min(limit, 500)).all()
    return [_to_out(a) for a in rows]


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.get(Analysis, analysis_id)
    if not a:
        raise HTTPException(404, "Analysis not found")
    return _to_out(a)


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.get(Analysis, analysis_id)
    if not a:
        raise HTTPException(404, "Analysis not found")
    video = a.video
    if video.owner_id != user.id and user.role != "admin":
        raise HTTPException(403, "Not your analysis")
    Path(video.stored_path).unlink(missing_ok=True)
    db.delete(video)  # cascades to analysis
    db.commit()


@router.get("/hotspots", response_model=list[HotspotOut])
def hotspots(top_n: int = 10, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Analysis).join(Video).filter(Analysis.status == "done").all()
    recs = [{"location": a.video.location, "latitude": a.video.latitude, "longitude": a.video.longitude,
             "congestion_level": a.congestion_level, "co2_kg_per_hour": a.co2_kg_per_hour,
             "created_at": a.created_at} for a in rows]
    return rank_hotspots(recs, top_n)


@router.get("/forecast", response_model=list[ForecastPoint])
def forecast(location: str, horizon_hours: int = 6,
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(Analysis).join(Video)
            .filter(Analysis.status == "done", Video.location == location).all())
    hist = [{"created_at": a.created_at, "congestion_level": a.congestion_level} for a in rows]
    return forecast_congestion(hist, horizon_hours)


@router.get("/summary", response_model=SummaryOut)
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Analysis).join(Video).filter(Analysis.status == "done").all()
    dist = {"Low": 0, "Moderate": 0, "High": 0}
    for a in rows:
        dist[a.congestion_level] = dist.get(a.congestion_level, 0) + 1
    limit = settings.carbon_limit_kg_per_hour
    within = sum(1 for a in rows if (a.co2_kg_per_hour or 0) <= limit)
    over = len(rows) - within
    from ..services.pipeline import new_detector  # lazy: constructs detector once for backend name
    return SummaryOut(
        total_analyses=len(rows),
        locations=len({a.video.location for a in rows}),
        level_distribution=dist,
        total_co2_kg_per_hour=round(sum(a.co2_kg_per_hour or 0 for a in rows), 2),
        avg_vehicles=round(sum(a.avg_vehicles or 0 for a in rows) / len(rows), 2) if rows else 0.0,
        model_trained=get_model().is_trained,
        detector_backend=new_detector().backend,
        carbon_limit_kg_per_hour=limit,
        within_limit=within,
        over_limit=over,
        pct_within_limit=round(100 * within / len(rows), 1) if rows else 0.0,
    )


@router.get("/model/info")
def model_info(user: User = Depends(get_current_user)):
    m = get_model()
    return {"trained": m.is_trained, "path": str(m.model_path), **m.meta}
