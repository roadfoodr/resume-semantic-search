"""
Pydantic schema definitions for resume parsing.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict
import uuid


class ResumeProfile(BaseModel):
    """Structured resume profile with all extracted fields."""
    
    id: str = Field(description="Unique identifier for the resume")
    name: Optional[str] = Field(default=None, description="Full name of the candidate")
    summary: str = Field(description="1-2 sentence professional summary", min_length=10)
    work_history: str = Field(description="Summarized work experience and roles", min_length=10)
    project_history: str = Field(description="Notable projects and achievements", min_length=5)
    skills: str = Field(description="Technical and professional skills", min_length=5)
    education: str = Field(description="Educational background and certifications", min_length=5)
    links: Dict[str, Optional[str]] = Field(
        default_factory=dict, 
        description="Professional links (linkedin, github, personal_website)"
    )
    raw_text: Optional[str] = Field(default=None, description="Original resume text")
    confidence_score: Optional[float] = Field(default=None, description="Extraction confidence (0-1)")
    processing_timestamp: Optional[str] = Field(default=None, description="When this profile was processed")
    
    @field_validator('id', mode='before')
    @classmethod
    def set_id(cls, v):
        """Generate ID from filename or fallback to UUID if not provided."""
        if not v:
            # Try to extract from filename if available in raw_text metadata
            # If not available, fallback to UUID generation
            return str(uuid.uuid4())
        return v
    
    @field_validator('links', mode='before')
    @classmethod
    def ensure_links_structure(cls, v):
        """Ensure links has expected keys."""
        if not isinstance(v, dict):
            v = {}
        
        # Ensure standard keys exist
        standard_keys = ['linkedin', 'github', 'personal_website', 'email']
        for key in standard_keys:
            if key not in v:
                v[key] = None
        
        return v
    
    def to_jsonl_line(self) -> str:
        """Convert to JSONL format (single line JSON)."""
        return self.model_dump_json()
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        str_strip_whitespace = True
        
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "John Doe",
                "summary": "Experienced software engineer with 5+ years in Python and web development.",
                "work_history": "Software Engineer at TechCorp (2020-2023), Junior Developer at StartupInc (2018-2020)",
                "project_history": "Built microservices architecture handling 1M+ requests/day, Led team of 3 developers",
                "skills": "Python, JavaScript, React, PostgreSQL, AWS, Docker, Git",
                "education": "B.S. Computer Science, University of Technology (2018)",
                "links": {
                    "linkedin": "https://linkedin.com/in/johndoe",
                    "github": "https://github.com/johndoe",
                    "personal_website": "https://johndoe.dev",
                    "email": "john@example.com"
                },
                "confidence_score": 0.95
            }
        } 