# app/services/rag_sentence_generator.py
"""
Integrates your RAG system to generate contextually appropriate sentences.
Uses the vector store to find similar known sentences, then generates new ones.
"""

import json
import os
import re
import sys
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.orm import Session

from app.models.sentence import Sentence

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def semantic_search(db: Session, query_text: str, top_k: int = 5) -> List[Sentence]:
    """
    Perform semantic search using pgvector.
    Returns sentences most similar to the query.
    """

    # Generate embedding for the query
    try:
        response = client.embeddings.create(
            input=query_text, model="text-embedding-3-small"
        )
        query_embedding = response.data[0].embedding
    except Exception as e:
        print(f"Error generating query embedding: {e}")
        return []
    try:
        # Use pgvector's cosine distance for similarity search
        results = (
            db.query(Sentence)
            .order_by(Sentence.embedding.cosine_distance(query_embedding))
            .limit(top_k)
            .all()
        )

        return results
    except Exception as e:
        print(f"Error during DB search: {e}")
        return []


def retrieve_context(db: Session, word_text: str, top_k: int = 5) -> List[Sentence]:
    search_query = f"sentences using the French word {word_text}"
    return semantic_search(db, search_query, top_k=top_k)


def generate_sentences_with_rag(
    db: Session, word_text: str, word_pos: str, count: int = 5, top_k: int = 5
) -> List[Dict]:
    """
    Generate French sentences using RAG:
    1. RETRIEVE: Find similar sentences from your Tatoeba DB
    2. AUGMENT: Use them as context
    3. GENERATE: Create new sentences at appropriate difficulty

    Args:
        word_text: The French word (e.g., "aller")
        word_pos: Part of speech (e.g., "VERB")
        count: Number of sentences to generate

    Returns:
        List of dicts: [{'sentence': '...', 'blanked': '...', 'tense': '...'}]
    """
    search_query = f"sentences using the French word {word_text}"

    relevant_sentences = retrieve_context(db, search_query, top_k=top_k)

    if not relevant_sentences:
        print(
            f"⚠️ No similar sentences found for '{word_text}'. Using basic generation."
        )
        return generate_basic_sentences(word_text, word_pos, count)

    # Format context from retrieved sentences
    context_string = "\n".join(
        [
            f"- {s.text} ({s.english_translation or 'no translation'})"
            for s in relevant_sentences
        ]
    )

    print(f"✅ RAG: Found {len(relevant_sentences)} similar sentences for context")

    # --- PHASE 2: AUGMENTED PROMPT ---
    prompt = f"""
Role: You are a French language tutor creating practice exercises.

Task: Generate {count} French sentences using the word "{word_text}" ({word_pos}).

CRITICAL CONSTRAINT - ADAPTIVE DIFFICULTY:
The user has already seen similar sentences at this level.
Write sentences with **similar vocabulary complexity and grammar** to these examples:

USER'S KNOWN CONTEXT:
{context_string}

Requirements:
1. Use simple, everyday French (A1-A2 level similar to the examples)
2. If the word is a verb, vary the tense (présent, passé composé, futur simple)
3. Keep sentences short (5-10 words)
4. Make them natural and practical

Output Format (JSON):
[
  {{"sentence": "Je vais à l'école", "tense": "présent"}},
  {{"sentence": "Tu es allé au marché", "tense": "passé composé"}}
]

Output ONLY the JSON array, no explanation.
"""

    # --- PHASE 3: GENERATION ---
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.5,
        )

        # Parse the JSON response

        response_text = response.choices[0].message.content.strip()
        # Try to extract JSON from markdown if needed
        json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group()

        sentences_data = json.loads(response_text)

        # Add blanked versions
        results = []
        for item in sentences_data:
            sentence = item["sentence"]
            # Simple blanking: replace the target word
            blanked = sentence.replace(word_text, "___", 1)

            results.append(
                {
                    "sentence": sentence,
                    "blanked": blanked,
                    "tense": item.get("tense", None),
                }
            )

        print(f"✅ RAG: Generated {len(results)} contextually appropriate sentences")
        return results

    except Exception as e:
        print(f"❌ RAG generation error: {e}")
        return generate_basic_sentences(word_text, word_pos, count)


def generate_basic_sentences(word_text: str, word_pos: str, count: int = 5):
    """
    Fallback: Generate sentences without RAG context.
    Used when vector store is unavailable.
    """
    prompt = f"""
Generate {count} simple French sentences (A1-A2 level) using the word "{word_text}" ({word_pos}).

If it's a verb, vary the tense (présent, passé composé, futur).
Keep sentences short and natural.

Output Format (JSON):
[
  {{"sentence": "Je vais à l'école", "tense": "présent"}},
  {{"sentence": "Tu es allé au marché", "tense": "passé composé"}}
]

Output ONLY the JSON array.
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            max_output_tokens=100,
            temperature=0.5,
        )

        response_text = response.output_text.strip()
        json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group()

        sentences_data = json.loads(response_text)

        results = []
        for item in sentences_data:
            sentence = item["sentence"]
            blanked = sentence.replace(word_text, "___", 1)

            results.append(
                {
                    "sentence": sentence,
                    "blanked": blanked,
                    "tense": item.get("tense", None),
                }
            )

        return results

    except Exception as e:
        print(f"❌ Basic generation error: {e}")
        return []
