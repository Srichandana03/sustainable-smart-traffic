import datetime as dt

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="planner")  # planner | admin
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    videos: Mapped[list["Video"]] = relationship(back_populates="owner")


class Video(Base):
    __tablename__ = "videos"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(512))
    stored_path: Mapped[str] = mapped_column(String(1024))
    location: Mapped[str] = mapped_column(String(255), index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="videos")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="video", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|running|done|failed
    detector_backend: Mapped[str | None] = mapped_column(String(32), nullable=True)
    avg_vehicles: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_vehicles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    congestion_level: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    congestion_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    co2_kg_per_hour: Mapped[float | None] = mapped_column(Float, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # full stats/prediction/emissions
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    video: Mapped["Video"] = relationship(back_populates="analyses")
