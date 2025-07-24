#!/usr/bin/env python3
"""
Inspect ChromaDB store to show schema and statistics.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path to import storage module
sys.path.append(str(Path(__file__).parent.parent))
from storage.chroma_storage import ResumeChromaStorage


def inspect_chroma_store(store_path: str = "../chroma_store"):
    """
    Inspect ChromaDB store and display schema and statistics.
    
    Args:
        store_path: Path to the ChromaDB store directory
    """
    print(f"🔍 Inspecting ChromaDB store at: {store_path}")
    print("=" * 60)
    
    try:
        # Initialize storage
        storage = ResumeChromaStorage(persist_directory=store_path)
        
        # Get collection statistics
        print("\n📊 COLLECTION STATISTICS")
        print("-" * 30)
        stats = storage.get_collection_stats()
        
        if not stats:
            print("❌ No data found in the collection or error occurred")
            return
        
        print(f"Collection Name: {stats.get('collection_name', 'N/A')}")
        print(f"Storage Directory: {stats.get('persist_directory', 'N/A')}")
        print(f"Total Embeddings: {stats.get('total_embeddings', 0):,}")
        print(f"Unique Resumes: {stats.get('unique_resumes', 0):,}")
        
        # Field distribution
        field_dist = stats.get('field_distribution', {})
        if field_dist:
            print(f"\n📋 FIELD DISTRIBUTION")
            print("-" * 30)
            total_fields = sum(field_dist.values())
            for field, count in sorted(field_dist.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_fields * 100) if total_fields > 0 else 0
                print(f"{field:15}: {count:4,} ({percentage:5.1f}%)")
        
        # Get sample data to show schema structure
        print(f"\n🗂️  DATA SCHEMA")
        print("-" * 30)
        
        # Get a small sample
        sample = storage.collection.get(limit=3, include=["documents", "metadatas"])
        
        if sample and sample["ids"]:
            print("Sample embedding entry structure:")
            
            # Show the first entry as an example
            example_metadata = sample["metadatas"][0]
            example_doc = sample["documents"][0]
            example_id = sample["ids"][0]
            
            print(f"\nEntry ID Format: {example_id}")
            print(f"Document Length: {len(example_doc)} characters")
            
            print(f"\nMetadata Schema:")
            for key, value in example_metadata.items():
                value_type = type(value).__name__
                if isinstance(value, str) and len(value) > 50:
                    display_value = f"{value[:47]}..."
                else:
                    display_value = value
                print(f"  {key:20}: {display_value} ({value_type})")
            
            print(f"\nDocument Sample:")
            doc_preview = example_doc[:200] + "..." if len(example_doc) > 200 else example_doc
            print(f"  {doc_preview}")
        
        # Show embeddable fields from the schema
        print(f"\n🏷️  EMBEDDABLE FIELDS")
        print("-" * 30)
        embeddable_fields = storage.embeddable_fields
        print("Fields that get embedded separately:")
        for i, field in enumerate(embeddable_fields, 1):
            print(f"  {i}. {field}")
        
        # Get unique resume IDs to show some examples
        if stats.get('total_embeddings', 0) > 0:
            print(f"\n👤 SAMPLE RESUME IDs")
            print("-" * 30)
            
            # Get a sample of metadata to find unique resume IDs
            sample_size = min(50, stats.get('total_embeddings', 0))
            larger_sample = storage.collection.get(limit=sample_size, include=["metadatas"])
            
            resume_ids = set()
            for metadata in larger_sample["metadatas"]:
                resume_ids.add(metadata.get("resume_id", "unknown"))
            
            # Show up to 5 examples
            displayed_ids = list(sorted(resume_ids))[:5]
            for i, resume_id in enumerate(displayed_ids, 1):
                print(f"  {i}. {resume_id}")
            
            if len(resume_ids) < stats.get('unique_resumes', 0):
                remaining = stats.get('unique_resumes', 0) - len(displayed_ids)
                print(f"  ... and {remaining} more unique resumes")
    
    except Exception as e:
        print(f"❌ Error inspecting ChromaDB store: {e}")
        print(f"Make sure the store exists at: {store_path}")
        return


if __name__ == "__main__":
    store_path = sys.argv[1] if len(sys.argv) > 1 else "../chroma_store"
    inspect_chroma_store(store_path) 