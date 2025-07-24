#!/usr/bin/env python3
"""
Programmatic Resume Search Script

Simple script to perform weighted resume searches programmatically.
Usage: python programmatic_search.py "your search query"
"""

import sys
import os

# Add parent directory to path to import query_resume_db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from query.query_resume_db import SimpleResumeSearch


def search_resumes(query: str, num_results: int = 5):
    """
    Perform a weighted search and return results.
    
    Args:
        query: Search query string
        num_results: Number of results to return
        
    Returns:
        List of candidate dictionaries
    """
    print(f"🔍 Searching for: '{query}'")
    
    # Initialize search engine
    search_engine = SimpleResumeSearch()
    
    # Perform search
    results = search_engine.search(query, num_results=num_results)
    
    # Print results
    if results:
        print(f"\n✅ Found {len(results)} candidates:")
        for i, candidate in enumerate(results, 1):
            print(f"\n{i}. {candidate['name']} (Score: {candidate['total_score']:.3f})")
            print(f"   Resume ID: {candidate['resume_id']}")
            print(f"   Fields matched: {candidate['fields_matched']}")
            
            # Retrieve and display the summary field
            try:
                full_resume = search_engine.storage.get_resume_by_id(candidate['resume_id'])
                summary = full_resume.get('summary', 'No summary available')
                
                print(f"   📄 Summary:")
                # Format the summary with proper indentation
                summary_lines = summary.split('\n')
                for line in summary_lines:
                    if line.strip():  # Only print non-empty lines
                        print(f"      {line.strip()}")
                    
            except Exception as e:
                print(f"      ⚠️  Could not retrieve summary: {e}")
    else:
        print("❌ No candidates found.")
    
    return results


def main():
    """Main function to handle command line arguments and run search."""
    if len(sys.argv) > 2:
        print("Usage: python programmatic_search.py \"your search query\"")
        print("Example: python programmatic_search.py \"Python developer\"")
        sys.exit(1)
    
    # Use provided query or default
    if len(sys.argv) == 2:
        query = sys.argv[1]
    else:
        query = "DevOps engineer AWS Kubernetes Terraform"
        print(f"ℹ️  No query provided, using default: '{query}'")
        print("   Usage: python programmatic_search.py \"your search query\"")
        print()
    
    try:
        results = search_resumes(query)
        return results
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 