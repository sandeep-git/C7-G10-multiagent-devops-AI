"""Quick sanity check: seed the vector store without starting the full API."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from backend.vectorstore import get_collection

if __name__ == "__main__":
    print("Seeding vector store...")
    col = get_collection()
    print(f"Collection '{col.name}' has {col.count()} documents.")
    results = col.query(query_texts=["database connection pool exhaustion"], n_results=2,
                         include=["metadatas"])
    print("Top 2 results for 'database connection pool exhaustion':")
    for meta in results["metadatas"][0]:
        print(f"  - {meta['title']}")
    print("Done.")
