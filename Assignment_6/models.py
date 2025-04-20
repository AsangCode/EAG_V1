from pydantic import BaseModel
from typing import List, Optional, Dict, Union
from datetime import datetime

class UserPreferences(BaseModel):
    name: str
    location: str
    favorite_genres: List[str]
    favorite_movies: List[str]
    preferred_languages: List[str]
    mood: Optional[str] = None

class ReasoningStep(BaseModel):
    step: int
    action: str
    reasoning: str

class PerceptionInput(BaseModel):
    user_preferences: UserPreferences
    current_context: str

class PerceptionOutput(BaseModel):
    analyzed_context: Dict[str, float]
    relevant_preferences: List[str]
    reasoning_steps: List[ReasoningStep]
    confidence_level: str
    reasoning_type: str
    fallback_used: bool
    fallback_reason: Optional[str] = None
    current_context: str

class MovieRecommendation(BaseModel):
    title: str
    year: int
    genre: List[str]
    rating: float
    description: str
    reason_recommended: str

class DecisionInput(BaseModel):
    perception_output: PerceptionOutput
    user_preferences: UserPreferences

class DecisionOutput(BaseModel):
    recommended_movies: List[MovieRecommendation]
    confidence_score: float
    reasoning: str
    reasoning_steps: List[ReasoningStep]
    reasoning_type: str
    fallback_used: bool
    fallback_reason: Optional[str] = None

class ActionInput(BaseModel):
    decision_output: DecisionOutput
    user_preferences: UserPreferences

class ActionOutput(BaseModel):
    movies_presented: List[MovieRecommendation]
    success_status: bool
    details: str
    next_steps: Optional[List[str]] = None

class MemoryItem(BaseModel):
    timestamp: str
    context: str
    action_taken: str
    success_rating: Optional[float] = None

class MemoryOutput(BaseModel):
    relevant_memories: List[MemoryItem]
    pattern_insights: Dict[str, float] 