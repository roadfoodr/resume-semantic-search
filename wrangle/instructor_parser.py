"""
Instructor-based structured extraction using OpenAI.
"""

import logging
import time
from datetime import datetime
from typing import Optional

try:
    import instructor
    from openai import OpenAI
    INSTRUCTOR_AVAILABLE = True
except ImportError:
    INSTRUCTOR_AVAILABLE = False

from schema import ResumeProfile

logger = logging.getLogger(__name__)


class InstructorParsingError(Exception):
    """Custom exception for Instructor parsing errors."""
    pass


class ResumeInstructorParser:
    """Parser using Instructor for structured LLM extraction."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "gpt-4-turbo",
        max_retries: int = 3,
        timeout: int = 60
    ):
        """
        Initialize the Instructor parser.
        
        Args:
            api_key: OpenAI API key (if None, uses environment variable)
            model: OpenAI model to use
            max_retries: Maximum retry attempts for failed requests
            timeout: Request timeout in seconds
        """
        if not INSTRUCTOR_AVAILABLE:
            raise InstructorParsingError(
                "Instructor package not available. Install with: pip install instructor"
            )
        
        try:
            openai_client = OpenAI(api_key=api_key, timeout=timeout)
            self.client = instructor.from_openai(openai_client)
            self.model = model
            self.max_retries = max_retries
            
            logger.info(f"Initialized Instructor parser with model: {model}")
            
        except Exception as e:
            raise InstructorParsingError(f"Failed to initialize OpenAI client: {str(e)}")
    
    def create_system_prompt(self) -> str:
        """Create the system prompt for resume extraction."""
        return """You are an expert resume parser that extracts structured information from resume text.

Your task is to analyze the provided resume text and extract the following information:

1. **name**: The candidate's full name (first name + last name)
2. **summary**: A concise 1-2 sentence professional summary highlighting key experience and focus areas
3. **work_history**: A structured summary of work experience including company names, roles, and key responsibilities
4. **project_history**: Notable projects, achievements, or technical accomplishments mentioned in the resume
5. **skills**: Technical skills, programming languages, tools, and professional competencies
6. **education**: Educational background including degrees, institutions, graduation dates, and relevant certifications

Guidelines:
- If information is missing or unclear, provide the best approximation based on available context
- Keep summaries concise but informative
- Focus on professional and technical content
- Maintain consistent formatting
- If a section has minimal information, provide what's available rather than leaving it empty
- Use clear, professional language"""

    def extract_resume_profile(
        self, 
        text: str, 
        basic_links: Optional[dict] = None
    ) -> ResumeProfile:
        """
        Extract structured resume profile using Instructor.
        
        Args:
            text: Raw resume text
            basic_links: Pre-extracted links dictionary
            
        Returns:
            ResumeProfile object with extracted data
            
        Raises:
            InstructorParsingError: If extraction fails after retries
        """
        if not text or len(text.strip()) < 50:
            raise InstructorParsingError("Resume text too short or empty")
        
        system_prompt = self.create_system_prompt()
        user_prompt = f"""Please extract structured information from this resume:

{text}

Note: Focus on extracting the most relevant and complete information available in the text."""

        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Extraction attempt {attempt + 1}/{self.max_retries}")
                
                start_time = time.time()
                
                profile = self.client.chat.completions.create(
                    model=self.model,
                    response_model=ResumeProfile,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.1  # Low temperature for consistent extraction
                )
                
                extraction_time = time.time() - start_time
                
                # Add metadata
                profile.raw_text = text
                profile.processing_timestamp = datetime.utcnow().isoformat()
                
                # Note: ID will be set from filename in batch processor
                
                # Merge basic links if provided
                if basic_links:
                    if not profile.links:
                        profile.links = {}
                    
                    # Update with regex-extracted links, but don't overwrite LLM-found links
                    for key, value in basic_links.items():
                        if value and (key not in profile.links or not profile.links[key]):
                            profile.links[key] = value
                
                # Calculate basic confidence score
                profile.confidence_score = self._calculate_confidence_score(profile)
                
                logger.info(
                    f"Successfully extracted profile in {extraction_time:.2f}s "
                    f"(confidence: {profile.confidence_score:.2f})"
                )
                
                return profile
                
            except Exception as e:
                last_error = e
                logger.warning(f"Extraction attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
        
        raise InstructorParsingError(
            f"All {self.max_retries} extraction attempts failed. Last error: {str(last_error)}"
        )
    
    def _calculate_confidence_score(self, profile: ResumeProfile) -> float:
        """Calculate a basic confidence score based on extracted data completeness."""
        score = 0.0
        total_fields = 7  # Number of main fields to score
        
        # Check each field for completeness
        if profile.name and len(profile.name.strip()) > 2:
            score += 1.0
        
        if profile.summary and len(profile.summary.strip()) > 20:
            score += 1.0
        
        if profile.work_history and len(profile.work_history.strip()) > 20:
            score += 1.0
        
        if profile.project_history and len(profile.project_history.strip()) > 10:
            score += 1.0
        
        if profile.skills and len(profile.skills.strip()) > 10:
            score += 1.0
        
        if profile.education and len(profile.education.strip()) > 10:
            score += 1.0
        
        if profile.links and any(v for v in profile.links.values() if v):
            score += 1.0
        
        return score / total_fields
    
    def test_connection(self) -> bool:
        """Test the OpenAI API connection."""
        try:
            test_profile = self.extract_resume_profile(
                "John Doe\nSoftware Engineer\nExperience: 5 years Python development\nEducation: BS Computer Science"
            )
            logger.info("API connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"API connection test failed: {str(e)}")
            return False 