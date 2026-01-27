# scripts/add_embeddings_to_db.py

"""
Generates embeddings for all existing sentences and stores them in PostgreSQL.
Run this ONCE after enabling pgvector.
"""

import os
import time

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.models.sentence import Sentence

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_embedding(text: str):
    """Generate embedding for a single text using OpenAI"""
    try:
        response = client.embeddings.create(input=text, model="text-embedding-3-small")
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def migrate_embeddings():
    """Add embeddings to all sentences in the database"""

    # Recreate tables with new schema
    print("📋 Recreating tables with pgvector support...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Get all sentences without embeddings
    sentences = db.query(Sentence).filter(Sentence.embedding.is_(None)).all()

    if not sentences:
        print("✅ No sentences need embeddings!")
        return

    total = len(sentences)
    print(f"🔄 Generating embeddings for {total} sentences...")
    print("⏱️  This might take a few minutes...\n")

    for i, sentence in enumerate(sentences, 1):
        # Generate embedding for the French sentence
        embedding = generate_embedding(sentence.text)

        if embedding:
            sentence.embedding = embedding

            if i % 10 == 0:
                db.commit()
                print(f"Progress: {i}/{total} ({(i / total) * 100:.1f}%)")
                time.sleep(0.5)  # Rate limiting
        else:
            print(f"⚠️  Failed to generate embedding for: {sentence.text}")

    db.commit()
    db.close()

    print(f"\n✅ Successfully added embeddings to {total} sentences!")
    print("🎉 Your database now supports semantic search!")


if __name__ == "__main__":
    migrate_embeddings()
