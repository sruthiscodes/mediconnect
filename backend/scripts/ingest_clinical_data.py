#!/usr/bin/env python3
"""
Clinical Data Ingestion Script
Processes clinical guidelines and ingests them into ChromaDB for RAG retrieval
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.embeddings import embedding_service

async def ingest_clinical_guidelines():
    """Read and ingest clinical guidelines from data file"""
    
    guidelines_file = Path(__file__).parent.parent / "data" / "clinical_guidelines.txt"
    
    if not guidelines_file.exists():
        print(f"Error: Clinical guidelines file not found at {guidelines_file}")
        return
    
    print("Reading clinical guidelines...")
    
    with open(guidelines_file, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Split content into individual guidelines
    guidelines = []
    current_guideline = ""
    
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            if current_guideline:
                guidelines.append(current_guideline.strip())
                current_guideline = ""
        else:
            current_guideline += line + " "
    
    # Add the last guideline if exists
    if current_guideline:
        guidelines.append(current_guideline.strip())
    
    print(f"Found {len(guidelines)} clinical guidelines to process")
    
    # Ingest each guideline
    successful_ingestions = 0
    for i, guideline in enumerate(guidelines, 1):
        if len(guideline) > 20:  # Only ingest substantial guidelines
            try:
                # Extract category from guideline title
                category = "general"
                if ":" in guideline:
                    category = guideline.split(":")[0].lower().replace(" ", "_")
                
                doc_id = await embedding_service.add_clinical_guideline(
                    guideline_text=guideline,
                    metadata={
                        "category": category,
                        "guideline_id": f"guideline_{i}",
                        "source": "clinical_guidelines.txt"
                    }
                )
                
                print(f"✓ Ingested guideline {i}: {category} ({doc_id})")
                successful_ingestions += 1
                
            except Exception as e:
                print(f"✗ Failed to ingest guideline {i}: {e}")
    
    print(f"\nIngestion complete: {successful_ingestions}/{len(guidelines)} guidelines successfully processed")

async def verify_ingestion():
    """Verify that clinical guidelines were properly ingested"""
    print("\nVerifying ingestion...")
    
    # Test search functionality
    test_queries = [
        "chest pain",
        "difficulty breathing", 
        "severe headache",
        "high fever"
    ]
    
    for query in test_queries:
        try:
            results = await embedding_service.search_clinical_knowledge(query, n_results=2)
            print(f"Query '{query}': Found {len(results)} relevant guidelines")
            for result in results:
                snippet = result["document"][:100] + "..." if len(result["document"]) > 100 else result["document"]
                print(f"  - {snippet}")
        except Exception as e:
            print(f"Error searching for '{query}': {e}")

async def main():
    """Main ingestion process"""
    print("MediConnect Clinical Data Ingestion")
    print("=" * 40)
    
    try:
        await ingest_clinical_guidelines()
        await verify_ingestion()
        print("\n✅ Clinical data ingestion completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Ingestion failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 