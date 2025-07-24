"""
Batch processing for resume PDFs with JSONL output.
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pdf_extractor import extract_pdf_text, validate_extracted_text, PDFExtractionError
from instructor_parser import ResumeInstructorParser, InstructorParsingError
from schema import ResumeProfile

logger = logging.getLogger(__name__)


class BatchProcessingStats:
    """Track batch processing statistics."""
    
    def __init__(self):
        self.total_files = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = None
        self.end_time = None
        self.errors = []
    
    def add_error(self, filename: str, error: str):
        """Add an error to the tracking list."""
        self.errors.append({"file": filename, "error": error})
    
    def get_summary(self) -> Dict:
        """Get processing summary."""
        duration = None
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
        
        return {
            "total_files": self.total_files,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "success_rate": self.successful / self.total_files if self.total_files > 0 else 0,
            "duration_seconds": duration,
            "errors": self.errors
        }


class ResumeBatchProcessor:
    """Batch processor for resume PDFs."""
    
    def __init__(
        self,
        parser: ResumeInstructorParser,
        output_dir: Path = Path("output"),
        logs_dir: Path = Path("logs"),
        max_workers: int = 3
    ):
        """
        Initialize batch processor.
        
        Args:
            parser: Configured ResumeInstructorParser instance
            output_dir: Directory for output files
            logs_dir: Directory for log files
            max_workers: Maximum concurrent workers for processing
        """
        self.parser = parser
        self.output_dir = Path(output_dir)
        self.logs_dir = Path(logs_dir)
        self.max_workers = max_workers
        
        # Create directories
        self.output_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        logger.info(f"Initialized batch processor with {max_workers} workers")
    
    def process_single_pdf(
        self, 
        pdf_path: Path, 
        skip_existing: bool = True
    ) -> Tuple[bool, Optional[ResumeProfile], Optional[str]]:
        """
        Process a single PDF file.
        
        Args:
            pdf_path: Path to PDF file
            skip_existing: Skip if output already exists
            
        Returns:
            Tuple of (success, profile, error_message)
        """
        try:
            # Check if output already exists
            output_file = self.output_dir / f"{pdf_path.stem}.json"
            if skip_existing and output_file.exists():
                logger.info(f"Skipping {pdf_path.name} - output already exists")
                return True, None, "skipped"
            
            logger.info(f"Processing {pdf_path.name}")
            
            # Extract text from PDF
            try:
                text, basic_links = extract_pdf_text(pdf_path)
            except PDFExtractionError as e:
                error_msg = f"PDF extraction failed: {str(e)}"
                logger.error(f"{pdf_path.name}: {error_msg}")
                return False, None, error_msg
            
            # Validate extracted text
            if not validate_extracted_text(text):
                error_msg = "Extracted text failed validation (too short or low quality)"
                logger.error(f"{pdf_path.name}: {error_msg}")
                return False, None, error_msg
            
            # Extract structured data using Instructor
            try:
                profile = self.parser.extract_resume_profile(text, basic_links)
                
                # Override ID with filename timestamp
                filename_id = self._extract_id_from_filename(pdf_path.name)
                if filename_id:
                    profile.id = filename_id
                    
            except InstructorParsingError as e:
                error_msg = f"Instructor parsing failed: {str(e)}"
                logger.error(f"{pdf_path.name}: {error_msg}")
                return False, None, error_msg
            
            # Save individual JSON file (for debugging/inspection)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(profile.model_dump(), f, indent=2, ensure_ascii=False)
            
            logger.info(
                f"Successfully processed {pdf_path.name} "
                f"(confidence: {profile.confidence_score:.2f})"
            )
            
            return True, profile, None
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"{pdf_path.name}: {error_msg}", exc_info=True)
            return False, None, error_msg
    
    def process_directory(
        self,
        pdf_dir: Path,
        output_jsonl: str = "resumes.jsonl",
        skip_existing: bool = True,
        pattern: str = "*.pdf"
    ) -> BatchProcessingStats:
        """
        Process all PDFs in a directory.
        
        Args:
            pdf_dir: Directory containing PDF files
            output_jsonl: Output JSONL filename
            skip_existing: Skip files with existing output
            pattern: File pattern to match
            
        Returns:
            BatchProcessingStats with processing results
        """
        pdf_dir = Path(pdf_dir)
        if not pdf_dir.exists():
            raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")
        
        # Find all PDF files
        pdf_files = list(pdf_dir.glob(pattern))
        if not pdf_files:
            logger.warning(f"No PDF files found in {pdf_dir} matching pattern '{pattern}'")
            return BatchProcessingStats()
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        stats = BatchProcessingStats()
        stats.total_files = len(pdf_files)
        stats.start_time = time.time()
        
        # Prepare JSONL output file
        jsonl_path = self.output_dir / output_jsonl
        
        # Process files
        successful_profiles = []
        
        if self.max_workers == 1:
            # Sequential processing
            for pdf_file in pdf_files:
                success, profile, error = self.process_single_pdf(pdf_file, skip_existing)
                
                if success and profile:
                    successful_profiles.append(profile)
                    stats.successful += 1
                elif success and not profile:  # skipped
                    stats.skipped += 1
                else:
                    stats.failed += 1
                    stats.add_error(pdf_file.name, error or "Unknown error")
        
        else:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(self.process_single_pdf, pdf_file, skip_existing): pdf_file
                    for pdf_file in pdf_files
                }
                
                # Collect results
                for future in as_completed(future_to_file):
                    pdf_file = future_to_file[future]
                    
                    try:
                        success, profile, error = future.result()
                        
                        if success and profile:
                            successful_profiles.append(profile)
                            stats.successful += 1
                        elif success and not profile:  # skipped
                            stats.skipped += 1
                        else:
                            stats.failed += 1
                            stats.add_error(pdf_file.name, error or "Unknown error")
                            
                    except Exception as e:
                        stats.failed += 1
                        error_msg = f"Future execution failed: {str(e)}"
                        stats.add_error(pdf_file.name, error_msg)
                        logger.error(f"{pdf_file.name}: {error_msg}", exc_info=True)
        
        stats.end_time = time.time()
        
        # Write JSONL file
        if successful_profiles:
            logger.info(f"Writing {len(successful_profiles)} profiles to {jsonl_path}")
            
            with open(jsonl_path, 'w', encoding='utf-8') as f:
                for profile in successful_profiles:
                    f.write(profile.to_jsonl_line() + '\n')
        
        # Write processing statistics
        stats_file = self.logs_dir / f"processing_stats_{int(time.time())}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats.get_summary(), f, indent=2)
        
        # Log summary
        summary = stats.get_summary()
        logger.info(
            f"Batch processing complete: "
            f"{summary['successful']} successful, "
            f"{summary['failed']} failed, "
            f"{summary['skipped']} skipped "
            f"({summary['success_rate']:.1%} success rate)"
        )
        
        if stats.errors:
            logger.warning(f"Errors occurred in {len(stats.errors)} files")
            for error in stats.errors[:5]:  # Log first 5 errors
                logger.warning(f"  {error['file']}: {error['error']}")
        
        return stats
    
    def load_jsonl_profiles(self, jsonl_path: Path) -> List[ResumeProfile]:
        """Load profiles from a JSONL file."""
        profiles = []
        
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())
                    profile = ResumeProfile(**data)
                    profiles.append(profile)
                except Exception as e:
                    logger.error(f"Error loading line {line_num} from {jsonl_path}: {e}")
        
        logger.info(f"Loaded {len(profiles)} profiles from {jsonl_path}")
        return profiles
    
    def _extract_id_from_filename(self, filename: str) -> Optional[str]:
        """Extract ID from filename like 'Profile_1735798769828.pdf'."""
        try:
            # Remove extension and split by underscore
            name_without_ext = filename.rsplit('.', 1)[0]
            if '_' in name_without_ext:
                parts = name_without_ext.split('_')
                # Get the last part which should be the timestamp
                potential_id = parts[-1]
                # Validate it's a number (timestamp)
                if potential_id.isdigit() and len(potential_id) >= 10:  # Reasonable timestamp length
                    return potential_id
            return None
        except Exception as e:
            logger.warning(f"Could not extract ID from filename {filename}: {e}")
            return None 