# Resume Parser & Semantic Search System

A comprehensive resume processing and semantic search system that converts PDF resumes into structured JSON data and enables intelligent candidate matching using ChromaDB vector storage and OpenAI embeddings.

## Key Features

### Core Processing
- **PDF Text Extraction**: Robust PDF processing with PyMuPDF
- **Structured LLM Extraction**: Uses Instructor + OpenAI for reliable, schema-validated JSON extraction
- **Batch Processing**: Process hundreds of resumes with parallel processing and progress tracking
- **JSONL Output**: Standard format for data science workflows and database imports

### Semantic Search & Vector Storage
- **ChromaDB Vector Storage**: Field-level embeddings for granular semantic search
- **Multi-Field Search**: Weighted search across summary, skills, work history, projects, and education
- **Intelligent Ranking**: Cosine similarity scoring with configurable field weights
- **Real-time Query**: Interactive search with detailed scoring breakdowns

## Data Schema

Each resume is parsed into a structured JSON with these fields:

```json
{
  "id": "unique-identifier",
  "name": "Candidate Name",
  "summary": "Professional summary optimized for semantic search",
  "work_history": "Structured work experience narrative",
  "project_history": "Notable projects and achievements", 
  "skills": "Technical and professional competencies",
  "education": "Educational background and certifications",
  "links": {
    "linkedin": "https://linkedin.com/in/profile",
    "github": "https://github.com/username",
    "personal_website": "https://example.com",
    "email": "email@example.com"
  },
  "raw_text": "Full extracted text from PDF",
  "confidence_score": 0.95,
  "processing_timestamp": "2024-01-01T12:00:00"
}
```

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd resume-parser

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=your_api_key_here
```

### 3. Basic Usage

```bash
# Test API connection
cd wrangle
python main.py --test-api

# Process all PDFs in the PDFs/ directory
python main.py

# Process a single PDF
python main.py --single path/to/resume.pdf

# Process PDFs from custom directory
python main.py --pdf-dir /path/to/custom/directory
```

### 4. Vector Storage & Search

```bash
# Store processed resumes in ChromaDB
cd storage
python chroma_storage.py --jsonl-path ../output/resumes.jsonl

# Interactive semantic search
cd query
python query_resume_db.py

# Programmatic search
cd examples
python example_search.py "Python developer with machine learning experience"
```

## Project Structure

```
resume-parser/
├── wrangle/                   # Core processing pipeline
│   ├── main.py               # Main entry point
│   ├── schema.py             # Pydantic data models
│   ├── pdf_extractor.py      # PDF text extraction
│   ├── instructor_parser.py  # LLM-based parsing
│   ├── batch_processor.py    # Batch processing logic
│   └── config.py             # Configuration management
├── storage/                   # Vector storage system
│   └── chroma_storage.py     # ChromaDB implementation
├── query/                     # Search & retrieval
│   └── query_resume_db.py    # Multi-field semantic search
├── examples/                  # Usage examples
│   └── example_search.py     # Programmatic search examples
├── tools/                     # Utility tools
│   └── inspect_chroma_store.py # Database inspection
├── docs/                      # Documentation
├── PDFs/                      # Input PDF directory
├── output/                    # JSON/JSONL outputs
├── chroma_store/              # Vector database storage
├── logs/                      # Processing logs
├── requirements.txt           # Dependencies
├── env.example               # Environment template
└── README.md
```

## Configuration Options

All settings can be configured via environment variables:

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| OpenAI API Key | `OPENAI_API_KEY` | - | Required: Your OpenAI API key |
| Model | `OPENAI_MODEL` | `gpt-4-turbo` | OpenAI model to use |
| Max Workers | `MAX_WORKERS` | `3` | Parallel processing workers |
| PDF Directory | `PDF_DIR` | `PDFs` | Input directory for PDFs |
| Output Directory | `OUTPUT_DIR` | `output` | Output directory |
| Output JSONL | `OUTPUT_JSONL` | `resumes.jsonl` | JSONL filename |
| Skip Existing | `SKIP_EXISTING` | `true` | Skip already processed files |
| Log Level | `LOG_LEVEL` | `INFO` | Logging verbosity |

## Semantic Search System

### Field-Level Embeddings

The system creates separate embeddings for each resume field, enabling granular search:

- **Summary** (30% weight): Overall professional profile
- **Skills** (30% weight): Technical competencies
- **Work History** (25% weight): Professional experience
- **Project History** (10% weight): Notable achievements
- **Education** (5% weight): Academic background

### Search Capabilities

```python
from query.query_resume_db import SimpleResumeSearch

# Initialize search engine
search = SimpleResumeSearch()

# Semantic search with weighted scoring
results = search.search("senior Python developer with AWS experience", num_results=5)

# Field-specific search
skills_matches = search.search_single_field("machine learning", "skills")
```

### Search Field Weights

You can customize field importance by modifying the weights in `SimpleResumeSearch`:

```python
field_weights = {
    "summary": 0.3,        # Professional summary
    "skills": 0.3,         # Technical skills  
    "work_history": 0.25,  # Work experience
    "project_history": 0.1, # Projects
    "education": 0.05      # Education
}
```

## Usage Examples

### Complete Pipeline

```bash
# 1. Process resumes
cd wrangle
python main.py --pdf-dir ../PDFs --output-dir ../output

# 2. Store in vector database
cd ../storage
python chroma_storage.py --jsonl-path ../output/resumes.jsonl

# 3. Search candidates
cd ../query
python query_resume_db.py
```

### Batch Processing with Custom Settings

```bash
cd wrangle
# Use more workers for faster processing
python main.py --max-workers 5 --model gpt-3.5-turbo

# Custom directories and output
python main.py --pdf-dir custom_resumes/ --output-dir results/ --output-jsonl my_resumes.jsonl
```

### Programmatic Search

```python
from query.query_resume_db import SimpleResumeSearch

# Setup search
search_engine = SimpleResumeSearch("chroma_store")

# Search for candidates
candidates = search_engine.search("DevOps engineer AWS Kubernetes", num_results=10)

# Access detailed candidate information
for candidate in candidates:
    print(f"{candidate['name']}: {candidate['total_score']:.3f}")
    print(f"Fields matched: {candidate['fields_matched']}")
    
    # Get full resume data
         full_resume = search_engine.storage.get_resume_by_id(candidate['resume_id'])
```

## Advanced Features

### Vector Database Management

```bash
# Inspect database statistics
cd tools
python inspect_chroma_store.py

# Reset database (clear all data)
cd storage
python chroma_storage.py --reset
```

### Debug Mode

```bash
# Enable verbose logging
cd wrangle
python main.py --verbose

# Check processing logs
tail -f logs/resume_parser.log

# Check search debug output
cd query
python query_resume_db.py  # Includes built-in debug output
```

### API Integration

```python
# Example: FastAPI endpoint
from fastapi import FastAPI, UploadFile
from wrangle.instructor_parser import ResumeInstructorParser
from storage.chroma_storage import ResumeChromaStorage

app = FastAPI()
parser = ResumeInstructorParser()
search_storage = ResumeChromaStorage()

@app.post("/parse-resume")
async def parse_resume(pdf_file: UploadFile):
    # Extract and parse resume
    profile = parser.extract_resume_profile(pdf_text)
    # Store in vector database
    search_storage.store_resume(profile.model_dump())
    return profile.model_dump()

@app.get("/search-candidates")
async def search_candidates(query: str, limit: int = 10):
    from query.query_resume_db import SimpleResumeSearch
    search_engine = SimpleResumeSearch()
    results = search_engine.search(query, num_results=limit)
    return results
```

### Search Integration

```python
# Integrate with existing recruitment systems
from query.query_resume_db import SimpleResumeSearch

class RecruitmentSystem:
    def __init__(self):
        self.search_engine = SimpleResumeSearch()
    
    def find_candidates(self, job_description: str):
        # Extract key requirements from job description
        # Use semantic search to find matching candidates
        candidates = self.search_engine.search(job_description, num_results=20)
        
        # Apply additional business logic
        filtered_candidates = self.apply_filters(candidates)
        
        return filtered_candidates
```

## Sample Queries & Results

```bash
# Technical role searches
"senior Python developer with machine learning experience"
"DevOps engineer AWS Kubernetes Docker"
"full stack JavaScript React Node.js"

# Experience-based searches  
"engineering manager 10+ years experience"
"data scientist PhD statistics"
"startup founder technical background"

# Skill-specific searches
"natural language processing transformers"
"cloud architecture Azure microservices"
"mobile development iOS Android"
```


## Architecture Notes

This system is designed for:
- **Semantic Matching**: Goes beyond keyword matching to understand intent and context
- **Scalability**: Handles large resume databases with efficient vector search
- **Flexibility**: Configurable weights and search parameters for different use cases
- **Production Ready**: Comprehensive error handling, logging, and monitoring capabilities 