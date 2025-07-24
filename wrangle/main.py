#!/usr/bin/env python3
"""
Main entry point for resume parser.

Usage:
    python main.py                    # Process all PDFs in PDFs/ directory
    python main.py --pdf-dir custom/  # Process PDFs in custom directory
    python main.py --test-api         # Test OpenAI API connection
    python main.py --single file.pdf  # Process single PDF
"""

import argparse
import logging
import sys
from pathlib import Path

from config import Config
from instructor_parser import ResumeInstructorParser, InstructorParsingError
from batch_processor import ResumeBatchProcessor
from pdf_extractor import extract_pdf_text, PDFExtractionError

logger = logging.getLogger(__name__)


def test_api_connection(parser: ResumeInstructorParser) -> bool:
    """Test the OpenAI API connection."""
    print("Testing OpenAI API connection...")
    
    try:
        success = parser.test_connection()
        if success:
            print("✅ API connection successful!")
            return True
        else:
            print("❌ API connection failed!")
            return False
    except Exception as e:
        print(f"❌ API connection error: {e}")
        return False


def process_single_pdf(pdf_path: Path, parser: ResumeInstructorParser) -> bool:
    """Process a single PDF file."""
    if not pdf_path.exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return False
    
    print(f"Processing single PDF: {pdf_path}")
    
    try:
        # Extract text
        text, basic_links = extract_pdf_text(pdf_path)
        print(f"✅ Extracted {len(text)} characters from PDF")
        
        # Parse with Instructor
        profile = parser.extract_resume_profile(text, basic_links)
        
        # Set ID from filename
        filename_parts = pdf_path.stem.split('_')
        if len(filename_parts) > 1 and filename_parts[-1].isdigit():
            profile.id = filename_parts[-1]
        
        print(f"✅ Extracted profile with confidence: {profile.confidence_score:.2f}")
        print(f"📋 Profile ID: {profile.id}")
        
        # Save output
        output_file = Config.OUTPUT_DIR / f"{pdf_path.stem}.json"
        Config.OUTPUT_DIR.mkdir(exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(profile.model_dump_json(indent=2))
        
        print(f"✅ Saved output to: {output_file}")
        
        # Print summary
        print("\nExtracted Profile Summary:")
        print(f"  Name: {profile.name or 'N/A'}")
        print(f"  Summary: {profile.summary[:100]}..." if len(profile.summary) > 100 else f"  Summary: {profile.summary}")
        print(f"  Skills: {profile.skills[:80]}..." if len(profile.skills) > 80 else f"  Skills: {profile.skills}")
        
        if profile.links and any(v for v in profile.links.values() if v):
            print("  Links:")
            for key, value in profile.links.items():
                if value:
                    print(f"    {key}: {value}")
        
        return True
        
    except (PDFExtractionError, InstructorParsingError) as e:
        print(f"❌ Processing failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.error("Unexpected error in single PDF processing", exc_info=True)
        return False


def process_batch(pdf_dir: Path, parser: ResumeInstructorParser) -> bool:
    """Process all PDFs in a directory."""
    if not pdf_dir.exists():
        print(f"❌ PDF directory not found: {pdf_dir}")
        return False
    
    print(f"Processing all PDFs in: {pdf_dir}")
    
    try:
        # Create batch processor
        processor = ResumeBatchProcessor(
            parser=parser,
            output_dir=Config.OUTPUT_DIR,
            logs_dir=Config.LOGS_DIR,
            max_workers=Config.MAX_WORKERS
        )
        
        # Process directory
        stats = processor.process_directory(
            pdf_dir=pdf_dir,
            output_jsonl=Config.OUTPUT_JSONL,
            skip_existing=Config.SKIP_EXISTING
        )
        
        # Print results
        summary = stats.get_summary()
        print(f"\n📊 Processing Results:")
        print(f"  Total files: {summary['total_files']}")
        print(f"  Successful: {summary['successful']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Skipped: {summary['skipped']}")
        print(f"  Success rate: {summary['success_rate']:.1%}")
        
        if summary['duration_seconds']:
            print(f"  Duration: {summary['duration_seconds']:.1f} seconds")
            print(f"  Rate: {summary['total_files'] / summary['duration_seconds']:.1f} files/second")
        
        if stats.errors:
            print(f"\n⚠️  First 5 errors:")
            for error in stats.errors[:5]:
                print(f"    {error['file']}: {error['error']}")
        
        jsonl_path = Config.OUTPUT_DIR / Config.OUTPUT_JSONL
        if jsonl_path.exists():
            print(f"\n✅ JSONL output saved to: {jsonl_path}")
        
        return summary['failed'] == 0
        
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")
        logger.error("Batch processing error", exc_info=True)
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Resume Parser using Instructor")
    
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=Config.PDF_DIR,
        help=f"Directory containing PDF files (default: {Config.PDF_DIR})"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Config.OUTPUT_DIR,
        help=f"Output directory for processed files (default: {Config.OUTPUT_DIR})"
    )
    
    parser.add_argument(
        "--output-jsonl",
        type=str,
        default=Config.OUTPUT_JSONL,
        help=f"Output JSONL filename (default: {Config.OUTPUT_JSONL})"
    )
    
    parser.add_argument(
        "--test-api",
        action="store_true",
        help="Test OpenAI API connection and exit"
    )
    
    parser.add_argument(
        "--single",
        type=Path,
        help="Process a single PDF file"
    )
    
    parser.add_argument(
        "--max-workers",
        type=int,
        default=Config.MAX_WORKERS,
        help=f"Maximum parallel workers (default: {Config.MAX_WORKERS})"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default=Config.OPENAI_MODEL,
        help=f"OpenAI model to use (default: {Config.OPENAI_MODEL})"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Update config with command line arguments
    Config.OUTPUT_DIR = args.output_dir
    Config.OUTPUT_JSONL = args.output_jsonl
    Config.MAX_WORKERS = args.max_workers
    Config.OPENAI_MODEL = args.model
    
    if args.verbose:
        Config.LOG_LEVEL = "DEBUG"
    
    # Setup logging
    Config.setup_logging()
    
    # Print configuration
    if args.verbose:
        Config.print_settings()
    
    # Validate configuration
    if not Config.validate():
        print("❌ Configuration validation failed!")
        sys.exit(1)
    
    # Create output directories
    Config.OUTPUT_DIR.mkdir(exist_ok=True)
    Config.LOGS_DIR.mkdir(exist_ok=True)
    
    try:
        # Initialize parser
        print("Initializing OpenAI Instructor parser...")
        resume_parser = ResumeInstructorParser(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            max_retries=Config.OPENAI_MAX_RETRIES,
            timeout=Config.OPENAI_TIMEOUT
        )
        
        # Handle different modes
        if args.test_api:
            success = test_api_connection(resume_parser)
            sys.exit(0 if success else 1)
        
        elif args.single:
            success = process_single_pdf(args.single, resume_parser)
            sys.exit(0 if success else 1)
        
        else:
            success = process_batch(args.pdf_dir, resume_parser)
            sys.exit(0 if success else 1)
    
    except InstructorParsingError as e:
        print(f"❌ Parser initialization failed: {e}")
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⚠️  Processing interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.error("Unexpected error in main", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 