#!/usr/bin/env python3
"""
Simple Multi-Field Resume Search Engine

A simplified version of the resume search system for teaching purposes.
This demonstrates weighted semantic search across different resume fields
with clear, easy-to-follow code.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.chroma_storage import ResumeChromaStorage
from typing import List, Dict, Any
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SimpleResumeSearch:
    """
    A simple resume search engine that searches multiple fields with weights.
    
    Think of this like a smart recruiter that looks at different parts of a resume
    and gives them different importance levels.
    """
    
    def __init__(self, chroma_directory: str = "chroma_store"):
        """Initialize the search engine."""
        print("🔧 Setting up resume search engine...")
        
        # Connect to our resume database
        self.storage = ResumeChromaStorage(persist_directory=chroma_directory)
        
        # Define which resume fields we'll search and their importance
        # Higher weight = more important for the final score
        self.field_weights = {
            "summary": 0.3,        # 30% - Overall professional summary
            "skills": 0.3,         # 30% - Technical skills
            "work_history": 0.25,  # 25% - Work experience
            "project_history": 0.1, # 10% - Projects
            "education": 0.05      # 5% - Education background
        }
        
        print("✅ Search engine ready!")
        print(f"📊 Field weights: {self.field_weights}")
    
    def search_single_field(self, query: str, field: str, num_results: int = 20) -> List[Dict]:
        """
        Search for candidates in just one field (like 'skills' or 'summary').
        
        Args:
            query: What we're looking for (e.g., "Python developer")
            field: Which field to search in (e.g., "skills")
            num_results: How many results to get
            
        Returns:
            List of matches from that field
        """
        print(f"🔍 Searching '{field}' field for: '{query}'")
        
        # Ask ChromaDB to find similar content in this field
        results = self.storage.query_resumes(
            query_text=query,
            n_results=num_results,
            field_filter=field,  # Only search this specific field
            include_metadata=True
        )
        
        # DEBUG: Print raw ChromaDB results
        print(f"   DEBUG: ChromaDB returned {len(results['ids'][0]) if results['ids'][0] else 0} raw results")
        if results['ids'][0]:
            print(f"   DEBUG: First result distance: {results['distances'][0][0]:.3f}")
        
        # Convert ChromaDB results to a simpler format
        matches = []
        if results['ids'][0]:  # If we found any results
            for i in range(len(results['ids'][0])):
                match = {
                    'resume_id': results['metadatas'][0][i]['resume_id'],
                    'name': results['metadatas'][0][i]['name'],
                    'field': field,
                    'content': results['documents'][0][i],
                    'distance': results['distances'][0][i]  # Lower = better match
                }
                matches.append(match)
        
        print(f"   Found {len(matches)} matches in {field}")
        return matches
    
    def calculate_scores(self, all_field_results: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """
        Combine results from all fields and calculate weighted scores.
        
        This is where the magic happens - we combine scores from different
        fields based on their importance weights.
        
        Args:
            all_field_results: Results from searching each field
            
        Returns:
            Dictionary of {resume_id: candidate_info}
        """
        print("🧮 Calculating weighted scores...")
        
        candidates = {}  # Will store: resume_id -> candidate info
        
        # Process results from each field
        for field, matches in all_field_results.items():
            field_weight = self.field_weights[field]
            
            for match in matches:
                resume_id = match['resume_id']
                
                # Convert distance to similarity score (0-1, higher is better)
                # For cosine distance: distance = 1 - cosine_similarity, ranges 0-2
                # So similarity = 1 - (distance / 2) to get proper 0-1 range
                similarity = max(0, 1 - (match['distance'] / 2))
                
                # If this is the first time we see this candidate
                if resume_id not in candidates:
                    candidates[resume_id] = {
                        'resume_id': resume_id,
                        'name': match['name'],
                        'field_scores': {},  # Score in each field
                        'field_matches': {}, # Best matching content from each field
                        'total_score': 0.0,
                        'fields_matched': 0
                    }
                
                # Keep the best score for this field (in case we have multiple matches)
                if field not in candidates[resume_id]['field_scores'] or \
                   similarity > candidates[resume_id]['field_scores'][field]:
                    
                    candidates[resume_id]['field_scores'][field] = similarity
                    candidates[resume_id]['field_matches'][field] = match['content'][:150] + "..."
        
        # Calculate final weighted scores
        for candidate in candidates.values():
            total_weighted_score = 0.0
            
            # Add up weighted scores from each field
            for field, score in candidate['field_scores'].items():
                weight = self.field_weights[field]
                weighted_score = score * weight
                total_weighted_score += weighted_score
                
                print(f"   {candidate['name']}: {field} = {score:.3f} × {weight} = {weighted_score:.3f}")
            
            candidate['total_score'] = total_weighted_score
            candidate['fields_matched'] = len(candidate['field_scores'])
        
        return candidates
    
    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Main search function - searches all fields and returns top candidates.
        
        Args:
            query: What we're looking for (e.g., "senior Python developer")
            num_results: How many final results to return
            
        Returns:
            List of top candidates sorted by score
        """
        print(f"\n🎯 Searching for: '{query}'")
        print("=" * 60)
        
        # Step 1: Search each field separately
        all_field_results = {}
        for field in self.field_weights.keys():
            all_field_results[field] = self.search_single_field(
                query=query,
                field=field,
                num_results=40  # Get plenty of results per field
            )
        
        # Step 2: Calculate weighted scores
        candidates = self.calculate_scores(all_field_results)
        
        # Step 3: Sort by total score and return top results
        top_candidates = sorted(
            candidates.values(),
            key=lambda x: x['total_score'],
            reverse=True  # Highest scores first
        )
        
        return top_candidates[:num_results]
    
    def print_results(self, results: List[Dict]):
        """Pretty print the search results."""
        if not results:
            print("❌ No candidates found.")
            return
        
        print(f"\n🏆 Top {len(results)} candidates:")
        print("=" * 60)
        
        for i, candidate in enumerate(results, 1):
            print(f"\n{i}. 👤 {candidate['name']}")
            print(f"   📊 Overall Score: {candidate['total_score']:.3f}")
            print(f"   🎯 Fields Matched: {candidate['fields_matched']}/{len(self.field_weights)}")
            print(f"   🆔 Resume ID: {candidate['resume_id']}")
            
            # Show breakdown by field
            print("   📋 Field Breakdown:")
            for field, score in sorted(candidate['field_scores'].items(), 
                                     key=lambda x: x[1], reverse=True):
                weight = self.field_weights[field]
                contribution = score * weight
                print(f"      • {field.replace('_', ' ').title()}: {score:.3f} "
                      f"(weight: {weight}, contributes: {contribution:.3f})")
                
                # Show a preview of the matching content
                if field in candidate['field_matches']:
                    preview = candidate['field_matches'][field]
                    print(f"        💬 \"{preview}\"")
            
            print("-" * 40)


def main():
    """
    Demo function showing how to use the simple search engine.
    """
    try:
        # Create the search engine
        search_engine = SimpleResumeSearch()
        
        # Example searches
        example_queries = [
            "Python developer",
            "senior software engineer",
            "machine learning",
            "full stack developer",
            "data scientist"
        ]
        
        print("\n🚀 Welcome to Simple Resume Search!")
        print("\nExample queries you can try:")
        for i, query in enumerate(example_queries, 1):
            print(f"  {i}. {query}")
        
        # Interactive search
        while True:
            print("\n" + "="*60)
            user_query = input("\n🔍 Enter your search query (or 'quit' to exit): ").strip()
            
            if user_query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not user_query:
                print("❌ Please enter a search query.")
                continue
            
            try:
                # Perform the search
                results = search_engine.search(user_query, num_results=3)
                
                # Show results
                search_engine.print_results(results)
                
            except Exception as e:
                print(f"❌ Search error: {e}")
                logger.error(f"Search error: {e}")
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Main error: {e}")


if __name__ == "__main__":
    main() 