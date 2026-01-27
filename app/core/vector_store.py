import os
import pickle

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class VectorStore:
    def __init__(self, cache_path="app/database/tatoeba_vectors.pkl"):
        """
        Initialize the store.
        It automatically tries to load the pre-computed vectors from the .pkl file.
        """
        self.vocabulary_db = []
        self.cache_path = cache_path
        self.load_cache()

    def load_cache(self):
        """Loads the .pkl file into memory."""
        if os.path.exists(self.cache_path):
            print(f"📦 Found cache at {self.cache_path}. Loading...")
            try:
                with open(self.cache_path, "rb") as f:
                    self.vocabulary_db = pickle.load(f)
                print(f"✅ Successfully loaded {len(self.vocabulary_db)} items.")
            except Exception as e:
                print(f"❌ Error loading cache: {e}")
        else:
            print(f"⚠️ Warning: No cache found at {self.cache_path}.")
            print("   (Did you run scripts/ingest_tatoeba.py?)")

    def search(self, user_query, top_k=5):
        """
        The RAG Retriever.
        1. Vectorizes the user's query.
        2. Scans the loaded vocabulary_db for matches.
        """
        if not self.vocabulary_db:
            return []

        # 1. Vectorize the User's Query (e.g., "Story about travel")
        try:
            query_vector = (
                client.embeddings.create(
                    input=user_query, model="text-embedding-3-small"
                )
                .data[0]
                .embedding
            )
        except Exception as e:
            print(f"API Error during search: {e}")
            return []

        scored_results = []

        # 2. Linear Scan (Dot Product)
        # We compare the query vector against every vector in our list.
        for entry in self.vocabulary_db:
            # entry is { 'french': '...', 'english': '...', 'vector': [...] }
            score = np.dot(query_vector, entry["vector"])
            scored_results.append((score, entry))

        # 3. Sort by Score (Highest first)
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # Return just the dictionary data (stripping the score)
        return [item[1] for item in scored_results[:top_k]]


# --- SELF-TEST ---
if __name__ == "__main__":
    # Test if it works immediately
    store = VectorStore()

    if store.vocabulary_db:
        print("\n--- Testing Search ---")
        results = store.search("I want to eat something", top_k=3)
        for r in results:
            print(f"Match: {r['french']} ({r['english']})")
