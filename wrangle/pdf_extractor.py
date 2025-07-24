"""
PDF text extraction utilities using PyMuPDF.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFExtractionError(Exception):
    """Custom exception for PDF extraction errors."""
    pass


def extract_basic_links(text: str) -> Dict[str, Optional[str]]:
    """Extract common links using regex patterns."""
    links = {
        'linkedin': None,
        'github': None,
        'personal_website': None,
        'email': None
    }
    
    # LinkedIn
    linkedin_pattern = r'https?://(www\.)?linkedin\.com/in/[^\s)>\]]+|linkedin\.com/in/[^\s)>\]]+'
    linkedin_match = re.search(linkedin_pattern, text, re.IGNORECASE)
    if linkedin_match:
        url = linkedin_match.group(0)
        if not url.startswith('http'):
            url = 'https://' + url
        links['linkedin'] = url
    
    # GitHub
    github_pattern = r'https?://(www\.)?github\.com/[^\s)>\]]+|github\.com/[^\s)>\]]+'
    github_match = re.search(github_pattern, text, re.IGNORECASE)
    if github_match:
        url = github_match.group(0)
        if not url.startswith('http'):
            url = 'https://' + url
        links['github'] = url
    
    # Email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_match = re.search(email_pattern, text)
    if email_match:
        links['email'] = email_match.group(0)
    
    # Personal website (basic heuristic)
    website_pattern = r'https?://[^\s)>\]]+\.(com|net|org|io|dev|me|tech)[^\s)>\]]*'
    website_matches = re.findall(website_pattern, text, re.IGNORECASE)
    if website_matches:
        # Filter out social media sites
        for match in website_matches:
            full_match = match if isinstance(match, str) else match[0]
            if not any(social in full_match.lower() for social in ['linkedin', 'github', 'twitter', 'facebook']):
                links['personal_website'] = full_match
                break
    
    return links


def extract_pdf_text(pdf_path: Path) -> Tuple[str, Dict[str, Optional[str]]]:
    """
    Extract text from PDF using PyMuPDF.
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Tuple of (extracted_text, basic_links_dict)
    
    Raises:
        PDFExtractionError: If extraction fails
    """
    if not pdf_path.exists():
        raise PDFExtractionError(f"PDF file not found: {pdf_path}")
    
    if not pdf_path.suffix.lower() == '.pdf':
        raise PDFExtractionError(f"File is not a PDF: {pdf_path}")
    
    try:
        doc = fitz.open(str(pdf_path))
        text_parts = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text.strip():
                text_parts.append(text)
        
        doc.close()
        full_text = "\n".join(text_parts)
        
        if not full_text or len(full_text.strip()) < 50:
            raise PDFExtractionError(f"Extracted text too short ({len(full_text)} chars)")
        
        # Extract basic links
        links = extract_basic_links(full_text)
        
        logger.info(f"Successfully extracted {len(full_text)} characters from {pdf_path.name}")
        return full_text, links
        
    except Exception as e:
        raise PDFExtractionError(f"PyMuPDF extraction failed: {str(e)}")


def validate_extracted_text(text: str, min_length: int = 100) -> bool:
    """Validate that extracted text meets basic quality criteria."""
    if not text or not isinstance(text, str):
        return False
    
    text = text.strip()
    
    if len(text) < min_length:
        return False
    
    # Check if text contains reasonable content (not just garbage)
    word_count = len(text.split())
    if word_count < 20:
        return False
    
    # Check for reasonable character distribution
    alpha_chars = sum(1 for c in text if c.isalpha())
    if alpha_chars / len(text) < 0.5:  # At least 50% alphabetic characters
        return False
    
    return True 