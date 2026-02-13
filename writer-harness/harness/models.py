from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime


class ContinuityLedger(BaseModel):
    """The persistent story state."""
    location_current: str
    location_previous: Optional[str] = None
    time_of_day: str
    date_or_day_count: str
    elapsed_time_since_last_scene: str
    who_present: List[str] = Field(default_factory=list)
    transport_last_leg: Optional[Dict[str, Any]] = None
    relationship_elapsed_time: Optional[str] = None
    relationship_last_contact: Optional[str] = None
    relationship_status_note: Optional[str] = None
    physical_constraints: Optional[Dict[str, Any]] = None
    devices_and_objects_in_scene: List[str] = Field(default_factory=list)
    scene_goal: str = ""
    tone_profile: str = ""


class StyleRules(BaseModel):
    """Collection of writing rules with categorical structure."""
    hard_rules: Dict[str, Union[List[str], str]] = Field(default_factory=dict)
    soft_preferences: Dict[str, Union[List[str], str]] = Field(default_factory=dict)
    output_targets: Optional[Dict[str, Any]] = None


class BannedPhrases(BaseModel):
    """Regex patterns to flag as violations."""
    banned_regex: List[str] = Field(default_factory=list)
    warn_regex: List[str] = Field(default_factory=list)


class LintViolation(BaseModel):
    """A single lint violation."""
    category: str
    severity: str
    message: str
    line_number: Optional[int] = None
    context: str = ""
