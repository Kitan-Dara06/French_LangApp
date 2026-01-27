import os
import pickle

import numpy as np
import psycopg2
from dotenv import load_dotenv

load_dotenv()  # This loads .env file

DATABASE_URL = os.getenv("DATABASE_URL")
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_sentences_from_db(limit=4000):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        query = f"""SELECT text, english_translation
        FROM sentences
        WHERE english_translation IS NOT NULL
        ORDER BY RANDOM()
        LIMIT {limit}"""
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        print(f"Retrieved {len(rows)} sentences")
        return rows

    except Exception as e:
        print(f"Error retrieving sentences: {e}")
        return []


def build_vector():
    print("connecting to database")
    raw_data = get_sentences_from_db(limit=4000)

    if not raw_data:
        return
    vectors = []
    print(f"Generating Embeddings for {len(raw_data)} sentences")
    for french_text, english_translation in raw_data:
        text_to_embed = f"{french_text} {english_translation}"
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small", input=text_to_embed
            )
            embedding = response.data[0].embedding
            vectors.append(
                {
                    "french": french_text,
                    "english": english_translation,
                    "vector": np.array(embedding),
                }
            )
            print(f"   Processed: {french_text[:20]}...")

            print(".", end="", flush=True)
        except Exception as e:
            print("x", end="", flush=True)
    print("\n")
    output_path = "app/database/tatoeba_vectors.pkl"

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "wb") as f:
        pickle.dump(vectors, f)

    print(f"✅ Success! Vector Cache saved to '{output_path}'")
    print("   You can now run your main app.")


if __name__ == "__main__":
    build_vector()
