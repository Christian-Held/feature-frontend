from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class JobStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task = Column(Text, nullable=False)
    repo_owner = Column(String, nullable=False)
    repo_name = Column(String, nullable=False)
    branch_base = Column(String, nullable=False)
    status = Column(String, default=JobStatus.PENDING, nullable=False)
    budget_usd = Column(Float, nullable=False)
    max_requests = Column(Integer, nullable=False)
    max_minutes = Column(Integer, nullable=False)
    model_cto = Column(String, nullable=True)
    model_coder = Column(String, nullable=True)
    cost_usd = Column(Float, default=0.0)
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    requests_made = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    cancelled = Column(Boolean, default=False)
    last_action = Column(String, nullable=True)
    pr_links = Column(JSON, default=list)
    agents_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    steps = relationship("JobStepModel", back_populates="job", cascade="all, delete-orphan")
    costs = relationship("CostEntryModel", back_populates="job", cascade="all, delete-orphan")


class JobStepModel(Base):
    __tablename__ = "job_steps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    name = Column(String, nullable=False)
    step_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    details = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("JobModel", back_populates="steps")


class CostEntryModel(Base):
    __tablename__ = "cost_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("JobModel", back_populates="costs")
