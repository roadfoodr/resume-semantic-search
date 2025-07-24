"""
Configuration management for resume parser.
"""

import os
import logging
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    # Load environment variables from .env file
    load_dotenv()
except ImportError:
    # dotenv not installed, skip loading .env file
    pass


class Config:
    """Configuration settings for resume parser."""
    
    # OpenAI Settings
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    OPENAI_MAX_RETRIES: int = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
    OPENAI_TIMEOUT: int = int(os.getenv("OPENAI_TIMEOUT", "60"))
    
    # Processing Settings
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "3"))
    PREFERRED_PDF_LIBRARY: str = os.getenv("PREFERRED_PDF_LIBRARY", "pymupdf")
    MIN_TEXT_LENGTH: int = int(os.getenv("MIN_TEXT_LENGTH", "100"))
    
    # File Paths
    PDF_DIR: Path = Path(os.getenv("PDF_DIR", "PDFs"))
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "output"))
    LOGS_DIR: Path = Path(os.getenv("LOGS_DIR", "logs"))
    
    # Output Settings
    OUTPUT_JSONL: str = os.getenv("OUTPUT_JSONL", "resumes.jsonl")
    SKIP_EXISTING: bool = os.getenv("SKIP_EXISTING", "true").lower() == "true"
    
    # Logging Settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings."""
        if not cls.OPENAI_API_KEY:
            print("Warning: OPENAI_API_KEY not set. Please set it as an environment variable.")
            return False
        
        if cls.MAX_WORKERS < 1:
            print("Error: MAX_WORKERS must be at least 1")
            return False
        
        if not cls.PDF_DIR.exists():
            print(f"Warning: PDF directory does not exist: {cls.PDF_DIR}")
            
        return True
    
    @classmethod
    def setup_logging(cls):
        """Setup logging configuration."""
        # Create logs directory
        cls.LOGS_DIR.mkdir(exist_ok=True)
        
        # Configure logging
        log_level = getattr(logging, cls.LOG_LEVEL.upper(), logging.INFO)
        
        # File handler
        log_file = cls.LOGS_DIR / "resume_parser.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(cls.LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter("%(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)
        
        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # Reduce noise from external libraries
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    @classmethod
    def print_settings(cls):
        """Print current configuration settings."""
        print("Resume Parser Configuration:")
        print(f"  OpenAI Model: {cls.OPENAI_MODEL}")
        print(f"  Max Workers: {cls.MAX_WORKERS}")
        print(f"  PDF Library: {cls.PREFERRED_PDF_LIBRARY}")
        print(f"  PDF Directory: {cls.PDF_DIR}")
        print(f"  Output Directory: {cls.OUTPUT_DIR}")
        print(f"  Output JSONL: {cls.OUTPUT_JSONL}")
        print(f"  Skip Existing: {cls.SKIP_EXISTING}")
        print(f"  Log Level: {cls.LOG_LEVEL}")
        api_key_status = "Set" if cls.OPENAI_API_KEY else "Not Set"
        print(f"  OpenAI API Key: {api_key_status}") 