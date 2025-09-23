from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Literal, Annotated
from datetime import datetime
from enum import Enum


# ======================
# USERS
# ======================

class UserBase(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=50, examples=["John Doe"])]
    email: EmailStr = Field(..., examples=["john@example.com"])


class UserCreate(UserBase):
    password: Annotated[str, Field(min_length=8, examples=["StrongPass123!"])]
    student_id: Optional[
        Annotated[str, Field(pattern=r"^[A-Za-z0-9/_-]{3,20}$", examples=["21/69/0069", "NACOS-123"])]
    ] = None
    level: Optional[Annotated[str, Field(max_length=10, examples=["HND2"])]] = None
    course: Optional[str] = Field(None, examples=["Computer Science"])
    role: Literal["voter", "admin", "superadmin", "auditor"] = "voter"


class UserResponse(UserBase):
    id: int
    student_id: Optional[str]
    level: Optional[str]
    course: Optional[str]
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ======================
# AUTH
# ======================

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    sub: Optional[str] = None   # email (subject)
    exp: Optional[int] = None   # expiration timestamp
    role: Optional[str] = None  # role string
    user_id: Optional[int] = None


# ======================
# CANDIDATES
# ======================

class CandidateBase(BaseModel):
    name: str = Field(..., examples=["Jane Smith"])
    level: Optional[str] = Field(None, examples=["HND1"])
    position: str = Field(..., examples=["President"])
    manifesto: Optional[str] = Field(None, examples=["Transparency and Innovation"])
    photo_url: Optional[str] = None


class CandidateCreate(CandidateBase):
    pass


class CandidateResponse(CandidateBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ======================
# ELECTIONS
# ======================

class ElectionStatus(str, Enum):
    upcoming = "upcoming"
    ongoing = "ongoing"
    completed = "completed"

class ElectionBase(BaseModel):
    title: str = Field(..., examples=["NACOS General Election 2026"])
    start_date: datetime = Field(..., alias="startDate")
    end_date: datetime = Field(..., alias="endDate")

    class Config:
        populate_by_name = True   # allows both start_date and startDate


class ElectionCreate(ElectionBase):
    pass



class ElectionUpdate(BaseModel):
    title: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[ElectionStatus] = None



class ElectionResponse(ElectionBase):
    id: int
    status: ElectionStatus = ElectionStatus.upcoming
    candidates: List[CandidateResponse] = []

    model_config = ConfigDict(from_attributes=True)



# ======================
# VOTING
# ======================

class VoteCreate(BaseModel):
    candidate_id: int = Field(..., examples=[1])


class VoteResponse(BaseModel):
    id: int
    election_id: int
    candidate_id: int
    receipt_id: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# ======================
# AUDIT LOGS
# ======================

class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    user_email: str
    action: str
    status: str
    details: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ======================
# LIVE RESULTS
# ======================

class CandidateResult(BaseModel):
    candidateId: int
    name: str
    position: str
    votes: int


class LiveResultsResponse(BaseModel):
    totalVotes: int
    candidates: List[CandidateResult]
