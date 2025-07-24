# ChromaDB Vector Storage for Resume Data

## Overview

This document describes our approach for storing structured JSON resume representations in ChromaDB, a vector database optimized for semantic search and retrieval. Our implementation transforms parsed resume data into field-level embeddings that enable sophisticated semantic matching between candidate profiles and job requirements.

---

## Architecture & Design Principles

### Field-Level Embedding Strategy

Rather than creating a single embedding per resume, we implement a **field-level embedding approach** that provides several key advantages:

1. **Granular Search Capabilities**: Query specific aspects of a candidate's profile (skills, work history, education) independently
2. **Improved Relevance**: Match queries to the most relevant sections of a resume
3. **Flexible Filtering**: Combine semantic search with field-specific filters
4. **Scalable Storage**: Efficiently store and retrieve large volumes of resume data

### Embeddable Fields

We focus on five core fields that capture the most semantically meaningful aspects of a candidate's profile:

- **`summary`**: LLM-generated overall profile summary
- **`skills`**: Consolidated skills and competencies
- **`work_history`**: Professional experience narrative
- **`project_history`**: Relevant projects and achievements
- **`education`**: Educational background and qualifications

---

## Implementation Details

### 1. Storage Architecture

```
ResumeChromaStorage Class
├── ChromaDB PersistentClient (auto-persisting)
├── OpenAI Embedding Client (text-embedding-3-small)
├── Collection Management
└── Field-Level Processing
```

### 2. Data Processing Pipeline

#### Resume Processing Flow:
1. **Input**: Structured JSON resume (from our parsing pipeline)
2. **Field Extraction**: Extract embeddable fields from the resume
3. **Content Validation**: Skip empty or whitespace-only fields
4. **Embedding Generation**: Create OpenAI embeddings for each field
5. **Metadata Enrichment**: Add contextual metadata for filtering and retrieval
6. **Storage**: Store in ChromaDB with unique field-level IDs

#### Unique ID Strategy:
- **Format**: `{resume_id}_{field_name}`
- **Example**: `profile_123_skills`, `profile_123_work_history`
- **Benefits**: Easy field-level retrieval and updates

### 3. Metadata Schema

Each embedding entry includes rich metadata for enhanced querying:

```json
{
  "resume_id": "unique_resume_identifier",
  "name": "candidate_name",
  "field": "field_type",
  "confidence_score": 0.95,
  "processing_timestamp": "2024-01-01T12:00:00",
  "links": "{'linkedin': 'url', 'github': 'url'}",
  "content_length": 150
}
```

---

## Key Features & Capabilities

### 1. Semantic Search

**Multi-Modal Querying**:
- Query across all fields: `"senior software engineer with ML experience"`
- Field-specific search: `"Python expertise"` filtered to `skills` field
- Hybrid semantic + metadata filtering

### 2. Flexible Retrieval

**Query Options**:
- **`query_resumes()`**: Semantic similarity search with optional field filtering
- **`get_resume_by_id()`**: Retrieve complete resume reconstruction from stored fields
- **`get_collection_stats()`**: Analytics on stored data distribution

---

## Usage Patterns

### 1. Initial Data Loading

```python
# Initialize storage
storage = ResumeChromaStorage(
    persist_directory="./chroma_store",
    collection_name="resumes"
)

# Batch load from JSONL
stats = storage.store_resumes_from_jsonl("resumes.jsonl")
```

### 2. Semantic Search

```python
# General search across all fields
results = storage.query_resumes(
    query_text="experienced React developer",
    n_results=10
)

# Field-specific search
skills_results = storage.query_resumes(
    query_text="machine learning",
    field_filter="skills",
    n_results=5
)
```

### 3. Complete Profile Retrieval

```python
# Reconstruct full resume from field embeddings
resume = storage.get_resume_by_id("profile_123")
```

---

## Performance & Scalability

### Embedding Model
- **Model**: OpenAI `text-embedding-3-small`
- **Dimensions**: 1,536
- **Performance**: Optimized for semantic similarity tasks

