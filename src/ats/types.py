from pydantic import BaseModel,Field , EmailStr, HttpUrl
from typing_extensions import Literal
from typing import List, Optional
from datetime import datetime


class JobDescription(BaseModel):
    title: str
    description: str
    skills: str


class Candidate(BaseModel):
    id: str
    name: str
    email: str
    bio: str
    years_of_exp:str
    skills: str

class CandidateFilter(BaseModel):
    id: str
    name:str
    email: str
    result: Literal["Pass", "Fail"] = Field(
        None, description="The Pass or Fail result"
    )
    reason:str

class CandidateScore(BaseModel):
    id: str
    score: int
    reason: str


class ScoredCandidate(BaseModel):
    id: str
    name: str
    email: str
    bio: str
    skills: str
    score: int
    reason: str


class ResumeData(BaseModel):
    name: str
    email: str
    mobile_number: str
    skills: List[str]
    education: List[str]
    objective:Optional[List[str]]
    experience_years: Optional[float]
    experience_details: Optional[List[str]]
    projects: Optional[List[str]]
    certifications: Optional[List[str]]
    linkedin: Optional[str]
    github: Optional[str]

class Resume_Final(BaseModel):
    resume_data:str
    feedback:str
    score:str