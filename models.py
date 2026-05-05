from pydantic import BaseModel, Field
from typing import List, Optional

class UserProfile(BaseModel):
    skills: List[str]
    interests: List[str]
    goals: str
    experience_level: str

class Opportunity(BaseModel):
    id: str
    title: str
    description: str
    url: str
    source: str
    published_date: str
    relevance_score: Optional[int] = 0
    reasoning: Optional[str] = None
    difficulty_level: Optional[str] = None
    is_urgent: Optional[bool] = False
    status: Optional[str] = "new"

class OpportunityEvaluation(BaseModel):
    relevance_score: int = Field(..., description="Score from 0 to 100 on how well this matches the profile")
    reasoning: str = Field(..., description="Brief explanation of why it matches or doesn't match")
    difficulty_level: str = Field(..., description="Estimated difficulty: 'beginner', 'intermediate', 'advanced'")
    is_urgent: bool = Field(..., description="True if the deadline is approaching soon or highly temporal")

class ApplicationDraft(BaseModel):
    draft_content: str = Field(..., description="The generated cover letter, proposal, or application content")
