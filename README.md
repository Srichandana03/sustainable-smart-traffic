# EcoPath — AI Traffic Congestion & CO₂ Emission Analysis

Upload traffic video → detect vehicles (YOLOv8) → classify congestion (XGBoost) → estimate CO₂ → rank hotspots → forecast. Built for urban planners.

```
Video ──▶ Vehicle detection ──▶ Feature engineering ──▶ XGBoost congestion ──▶ CO₂ estimation
            (YOLOv8 / OpenCV)      (counts, time)         Low/Moderate/High      (EF × km × multiplier)
                                                                │
                                                PostgreSQL ◀────┘──▶ Hotspot ranking · Forecast (stub → LSTM)
                                                                │
                                                        FastAPI  ──▶  React dashboard (Recharts)
```

## Repo layout

```
backend/app/        FastAPI: api/ (auth, analysis) · models/ (SQLAlchemy) · services/ (auth, pipeline)
ml/                 vehicle_detection/ · congestion_model/ (features, train, predict) · emission_estimation/ · hotspots.py · forecasting/
frontend/           React 18 + Vite + Recharts (Login, Dashboard, Analyze, Hotspots, History)
data/               sample/ (synthetic clips) · raw/ (put Kaggle CSV here) · uploads/ (runtime)
models/             congestion_xgb.json + congestion_meta.json (trained model)
tests/              pytest end-to-end API tests (SQLite, no Postgres needed)
docker-compose.yml  Postgres 16 + API + nginx-served frontend
```

## Quick start (Docker — recommended)

```bash
cp .env.example .env
python -m ml.congestion_model.train --synthetic   # or --data data/raw/Traffic.csv (see below)
docker compose up --build
```
Open http://localhost:5173 → register → *Analyze video* → upload `data/sample/heavy_traffic.mp4`.
API docs: http://localhost:8000/docs

## Quick start (local dev)

```bash
# 1. Postgres (or set DATABASE_URL=sqlite:///./data/dev.db in .env to skip it)
docker compose up -d db

# 2. Backend
pip install -r backend/requirements.txt
pip install ultralytics          # optional: real YOLOv8 detection (downloads torch, ~2 GB)
python data/make_sample_video.py
python -m ml.congestion_model.train --synthetic
uvicorn backend.app.main:app --reload --port 8000

# 3. Frontend
cd frontend && npm install && npm run dev      # http://localhost:5173 (proxies /api → :8000)
```

## Training on the real dataset

We use the Kaggle **Traffic Prediction Dataset** (vehicle counts per 15 min → low/normal/heavy/high):
https://www.kaggle.com/datasets/hasibullahaman/traffic-prediction-dataset

```bash
# download Traffic.csv / TrafficTwoMonth.csv into data/raw/
python -m ml.congestion_model.train --data data/raw/TrafficTwoMonth.csv
```
Labels map: `low→Low`, `normal→Moderate`, `heavy/high→High`. Metrics (accuracy, macro-F1, confusion matrix, feature importance) are saved to `models/congestion_meta.json` and exposed at `GET /api/model/info`.

Features: car/bike/bus/truck counts, total, heavy-vehicle ratio, two-wheeler ratio, hour (+sin/cos), weekend, peak-hour flag. At inference, per-frame detections are converted to 15-min counts via an assumed 20 s dwell time (`ml/congestion_model/features.py::video_stats_to_features`).

## Vehicle detection backends

| `DETECTOR_BACKEND` | Needs | Notes |
|---|---|---|
| `yolo` | `pip install ultralytics` | YOLOv8n COCO classes car/motorcycle/bus/truck. Use for real footage. |
| `opencv` | nothing extra | MOG2 background subtraction + size heuristics. Dev/CI fallback; weak on static queues. |
| `auto` (default) | — | YOLO if importable, else OpenCV. |

## Emissions

`CO₂ = Σ_class vehicles × segment_km × EF_class × congestion_multiplier`, EF (g/km): car 150, motorcycle 40, bus 800, truck 600; multiplier Low 1.0 / Moderate 1.3 / High 1.8. Edit `ml/emission_estimation/estimator.py` for city-specific factors. Output includes the free-flow baseline and the *excess* CO₂ attributable to congestion — the number planners care about.

## Sustainability verdict (carbon limit)

Each analysis is checked against a configurable carbon cap (`CARBON_LIMIT_KG_PER_HOUR`, default **2500 kg CO₂/h** — set it to your city/government limit). This is a plain threshold check, not ML (`ml/sustainability/assessor.py`):

| CO₂ vs limit | Verdict | Colour |
|---|---|---|
| ≤ 80% of limit | **Eco-Friendly** | green |
| 80–100% | **Near Limit** | amber |
| > 100% | **Over Limit** | red |

The verdict (status, % of limit, headroom/overshoot) rides in each analysis' `details.sustainability`, and `/api/summary` reports how many sites stay within the cap. Shown on the Analyze result and the Dashboard.

## Before vs after XGBoost

`train.py` evaluates two methods on the *same* held-out test split so you can show what the model adds:
- **Before** — a no-learning rule that buckets Low/Moderate/High purely by total vehicle count (`ml/congestion_model/baseline.py`), plus a majority-class reference.
- **After** — the XGBoost classifier using all 12 features.

Accuracy and macro-F1 for both, the gain, and the majority-class score are saved to `congestion_meta.json` under `comparison` / `baseline_metrics` and exposed at `GET /api/model/info`. The Dashboard renders them as a before/after bar chart. (On synthetic data: rule ≈ 66% → XGBoost ≈ 86% accuracy.)

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/register`, `/api/auth/login`, GET `/api/auth/me` | JWT auth |
| POST | `/api/analyze` (multipart: file, location, latitude?, longitude?) | Run full pipeline |
| GET | `/api/analyses`, `/api/analyses/{id}`, DELETE `/api/analyses/{id}` | History |
| GET | `/api/summary` | Dashboard KPIs |
| GET | `/api/hotspots?top_n=10` | Ranked hotspots |
| GET | `/api/forecast?location=…&horizon_hours=6` | Forecast (baseline stub) |
| GET | `/api/model/info` | Trained-model metrics |

## Tests

```bash
pytest -q tests        # 6 end-to-end tests, ~5 s, SQLite
```

## Roadmap vs. requirements doc

- [x] Phase 1–3: detection, congestion model, emissions, API, dashboard, Postgres, auth
- [x] Hotspot ranking (score = 0.6·severity + 0.4·emission intensity)
- [ ] Phase 4: LSTM forecasting (`ml/forecasting/forecaster.py` is a seasonal-naive stub with the final signature)
- [ ] Phase 5: Alembic migrations, background job queue for long videos (currently synchronous), live camera streams, map view (Leaflet) on Hotspots page
