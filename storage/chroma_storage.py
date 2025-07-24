"""
ChromaDB storage for resume data with field-level embeddings.

This module handles storing resume data in ChromaDB with separate embeddings 
for different fields (summary, skills, work_history, etc.) along with metadata
for efficient querying and filtering.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

import chromadb
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)


class ResumeChromaStorage:
    """
    ChromaDB storage manager for resume data with field-level embeddings.
    """
    
    def __init__(
        self, 
        persist_directory: str = "../chroma_store",
        collection_name: str = "resumes",
        openai_model: str = "text-embedding-3-small"
    ):
        """
        Initialize ChromaDB storage.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the ChromaDB collection
            openai_model: OpenAI embedding model to use
        """
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.openai_model = openai_model
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize ChromaDB client (using PersistentClient for v1.0+)
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.persist_directory)
        )
        
        # Create or get collection with cosine distance for better text similarity
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine distance for text embeddings
        )
        
        # Define fields to embed
        self.embeddable_fields = [
            "summary", 
            "skills", 
            "work_history", 
            "project_history", 
            "education"
        ]
        
        logger.info(f"ChromaDB storage initialized with collection '{self.collection_name}'")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Create embedding for text using OpenAI.
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding values
        """
        try:
            response = self.openai_client.embeddings.create(
                model=self.openai_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            raise
    
    def process_resume(self, resume: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a resume into field-level embeddings.
        
        Args:
            resume: Resume data dictionary
            
        Returns:
            List of embedding entries for the resume
        """
        entries = []
        resume_id = resume.get("id", str(uuid4()))
        resume_name = resume.get("name", "Unknown")
        
        for field in self.embeddable_fields:
            content = resume.get(field, "")
            
            # Skip empty fields
            if not content or not content.strip():
                logger.debug(f"Skipping empty field '{field}' for resume {resume_id}")
                continue
            
            try:
                # Create unique ID for this field embedding
                entry_id = f"{resume_id}_{field}"
                
                # Generate embedding
                embedding = self.embed_text(content)
                
                # Create entry
                entry = {
                    "id": entry_id,
                    "embedding": embedding,
                    "document": content,
                    "metadata": {
                        "resume_id": resume_id,
                        "name": resume_name,
                        "field": field,
                        "confidence_score": resume.get("confidence_score", 1.0),
                        "processing_timestamp": resume.get("processing_timestamp", ""),
                        "links": json.dumps(resume.get("links", {})),
                        "content_length": len(content)
                    }
                }
                
                entries.append(entry)
                logger.debug(f"Created embedding for {resume_id}.{field}")
                
            except Exception as e:
                logger.error(f"Error processing field '{field}' for resume {resume_id}: {e}")
                continue
        
        return entries
    
    def store_resume(self, resume: Dict[str, Any]) -> bool:
        """
        Store a single resume in ChromaDB.
        
        Args:
            resume: Resume data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            entries = self.process_resume(resume)
            
            if not entries:
                logger.warning(f"No embeddable content found for resume {resume.get('id', 'unknown')}")
                return False
            
            # Add to ChromaDB
            self.collection.add(
                ids=[entry["id"] for entry in entries],
                embeddings=[entry["embedding"] for entry in entries],
                documents=[entry["document"] for entry in entries],
                metadatas=[entry["metadata"] for entry in entries]
            )
            
            logger.info(f"Stored {len(entries)} field embeddings for resume {resume.get('id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing resume {resume.get('id', 'unknown')}: {e}")
            return False
    
    def store_resumes_from_jsonl(self, jsonl_path: str) -> Dict[str, int]:
        """
        Store all resumes from a JSONL file.
        
        Args:
            jsonl_path: Path to the JSONL file
            
        Returns:
            Dictionary with processing statistics
        """
        stats = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "total_embeddings": 0
        }
        
        jsonl_file = Path(jsonl_path)
        if not jsonl_file.exists():
            raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")
        
        logger.info(f"Processing resumes from {jsonl_path}")
        
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    resume = json.loads(line.strip())
                    stats["processed"] += 1
                    
                    if self.store_resume(resume):
                        stats["successful"] += 1
                        # Count embeddings for this resume
                        resume_id = resume.get("id", "unknown")
                        field_count = sum(1 for field in self.embeddable_fields 
                                        if resume.get(field, "").strip())
                        stats["total_embeddings"] += field_count
                    else:
                        stats["failed"] += 1
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error on line {line_num}: {e}")
                    stats["failed"] += 1
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    stats["failed"] += 1
        
        logger.info(f"Processing complete. Stats: {stats}")
        return stats
    
    def query_resumes(
        self, 
        query_text: str, 
        n_results: int = 10,
        field_filter: Optional[str] = None,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Query resumes using semantic search.
        
        Args:
            query_text: Text to search for
            n_results: Number of results to return
            field_filter: Optional field to filter by (e.g., "skills", "summary")
            include_metadata: Whether to include metadata in results
            
        Returns:
            Query results dictionary
        """
        try:
            # Generate embedding for query
            query_embedding = self.embed_text(query_text)
            
            # Build where clause for filtering
            where_clause = None
            if field_filter:
                where_clause = {"field": field_filter}
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause,
                include=["documents", "metadatas", "distances"] if include_metadata else ["documents"]
            )
            
            logger.info(f"Query '{query_text}' returned {len(results['ids'][0])} results")
            return results
            
        except Exception as e:
            logger.error(f"Error querying resumes: {e}")
            raise
    
    def get_resume_by_id(self, resume_id: str) -> Dict[str, Any]:
        """
        Get all fields for a specific resume.
        
        Args:
            resume_id: Resume ID to retrieve
            
        Returns:
            Dictionary with all resume fields
        """
        try:
            results = self.collection.get(
                where={"resume_id": resume_id},
                include=["documents", "metadatas"]
            )
            
            if not results["ids"]:
                return {}
            
            # Reconstruct resume from fields
            resume_data = {
                "id": resume_id,
                "name": results["metadatas"][0]["name"]
            }
            
            for i, metadata in enumerate(results["metadatas"]):
                field = metadata["field"]
                resume_data[field] = results["documents"][i]
            
            return resume_data
            
        except Exception as e:
            logger.error(f"Error retrieving resume {resume_id}: {e}")
            return {}
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the stored data.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            
            if count == 0:
                return {
                    "total_embeddings": 0,
                    "unique_resumes": 0,
                    "field_distribution": {},
                    "collection_name": self.collection_name,
                    "persist_directory": str(self.persist_directory)
                }
            
            # Get ALL records to accurately count unique resumes and field distribution
            all_records = self.collection.get(include=["metadatas"])
            
            field_counts = {}
            unique_resumes = set()
            
            for metadata in all_records["metadatas"]:
                field = metadata["field"]
                field_counts[field] = field_counts.get(field, 0) + 1
                unique_resumes.add(metadata["resume_id"])
            
            return {
                "total_embeddings": count,
                "unique_resumes": len(unique_resumes),
                "field_distribution": field_counts,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory)
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
    
    def persist(self):
        """Persist the ChromaDB data to disk (automatic in v1.0+)."""
        # In ChromaDB 1.0+, PersistentClient automatically persists data
        # This method is kept for compatibility but does nothing
        logger.info("ChromaDB data is automatically persisted with PersistentClient")
    
    def reset_collection(self):
        """Reset/clear the collection."""
        try:
            self.chroma_client.delete_collection(self.collection_name)
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name
            )
            logger.info(f"Collection '{self.collection_name}' reset successfully")
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            raise


def main():
    """
    Main function to demonstrate usage.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Store resume data in ChromaDB")
    parser.add_argument(
        "--jsonl-path", 
        default="../output/resumes.jsonl",
        help="Path to the JSONL file containing resume data"
    )
    parser.add_argument(
        "--collection-name",
        default="resumes",
        help="Name of the ChromaDB collection"
    )
    parser.add_argument(
        "--persist-dir",
        default="../chroma_store",
        help="Directory to persist ChromaDB data"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the collection before storing data"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show collection statistics only"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize storage
    storage = ResumeChromaStorage(
        persist_directory=args.persist_dir,
        collection_name=args.collection_name
    )
    
    if args.stats:
        # Show statistics
        stats = storage.get_collection_stats()
        print(f"\nCollection Statistics:")
        print(f"Total embeddings: {stats.get('total_embeddings', 0)}")
        print(f"Unique resumes: {stats.get('unique_resumes', 0)}")
        print(f"Field distribution: {stats.get('field_distribution', {})}")
        return
    
    if args.reset:
        print("Resetting collection...")
        storage.reset_collection()
    
    # Store resumes
    try:
        stats = storage.store_resumes_from_jsonl(args.jsonl_path)
        print(f"\nProcessing complete!")
        print(f"Processed: {stats['processed']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Total embeddings created: {stats['total_embeddings']}")
        
        # Persist data
        storage.persist()
        print(f"Data persisted to {args.persist_dir}")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise


if __name__ == "__main__":
    main() 