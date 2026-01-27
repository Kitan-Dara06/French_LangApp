"""
Generates embeddings on-demand for sentences that need them.
Only called when RAG is active and sentence has no embedding.
"""

import os

from openai import OpenAI
from sqlalchemy.orm import Session

from app.models.sentence import Sentence

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ensure_embedding(sentence: Sentence, db: Session) -> bool:
    """
    Generate embedding for a sentence if it doesn't have one.

    Returns:
        True if embedding was generated/already exists
        False if generation failed
    """

    # Already has embedding
    if sentence.embedding is not None:
        return True

    # Generate embedding
    try:
        response = client.embeddings.create(
            input=sentence.text, model="text-embedding-3-small"
        )

        sentence.embedding = response.data[0].embedding
        db.commit()

        print(f"✅ Generated embedding for: {sentence.text[:50]}...")
        return True

    except Exception as e:
        print(f"❌ Failed to generate embedding: {e}")
        return False


def batch_ensure_embeddings(sentences: list[Sentence], db: Session):
    """
    Generate embeddings for multiple sentences at once.
    More efficient than one-by-one.
    """

    # Filter sentences without embeddings
    need_embeddings = [s for s in sentences if s.embedding is None]

    if not need_embeddings:
        return

    print(f"🔄 Generating {len(need_embeddings)} embeddings...")

    try:
        # Batch API call
        texts = [s.text for s in need_embeddings]
        response = client.embeddings.create(input=texts, model="text-embedding-3-small")

        # Assign embeddings
        for sentence, embedding_data in zip(need_embeddings, response.data):
            sentence.embedding = embedding_data.embedding

        db.commit()
        print(f"✅ Generated {len(need_embeddings)} embeddings")

    except Exception as e:
        print(f"❌ Batch embedding failed: {e}")
