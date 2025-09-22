from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, UniqueConstraint, Enum, func
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import enum


# --- ENUMS for consistency ---
class UserRole(str, enum.Enum):
    voter = "voter"
    admin = "admin"
    superadmin = "superadmin"
    auditor = "auditor"


class ElectionStatus(str, enum.Enum):
    upcoming = "upcoming"
    ongoing = "ongoing"
    completed = "completed"


# --- MODELS ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    student_id = Column(String, unique=True, index=True, nullable=True)
    level = Column(String, nullable=True)
    course = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.voter, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    votes = relationship("Vote", back_populates="user", cascade="all, delete-orphan")
    


class Election(Base):
    __tablename__ = "elections"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(Enum(ElectionStatus), default=ElectionStatus.upcoming, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    candidates = relationship("Candidate", back_populates="election", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="election", cascade="all, delete-orphan")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    election_id = Column(Integer, ForeignKey("elections.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    level = Column(String, nullable=True)
    position = Column(String, nullable=False, index=True)  # <-- key field for per-position voting
    manifesto = Column(Text, nullable=True)
    photo_url = Column(String, nullable=True)

    election = relationship("Election", back_populates="candidates")
    votes = relationship("Vote", back_populates="candidate", cascade="all, delete-orphan")


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    election_id = Column(Integer, ForeignKey("elections.id", ondelete="CASCADE"), nullable=False)
    position = Column(String, nullable=False)  # <-- store position at time of voting
    timestamp = Column(DateTime, default=datetime.utcnow)
    receipt_id = Column(String, unique=True, nullable=False, index=True)

    user = relationship("User", back_populates="votes")
    candidate = relationship("Candidate", back_populates="votes")
    election = relationship("Election", back_populates="votes")

    __table_args__ = (
        # Ensure a voter can only vote once per position in a given election
        UniqueConstraint("user_id", "election_id", "position", name="uq_user_election_position_vote"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # optional link to user
    user_email = Column(String, nullable=False)
    action = Column(String, nullable=False)
    status = Column(String, nullable=False)
    details = Column(Text, nullable=True)
