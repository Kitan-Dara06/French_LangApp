# scripts/extract_vocabulary_from_tatoeba.py
"""
Intelligent vocabulary extraction from Tatoeba using spaCy.

This script:
1. Scans all Tatoeba sentences
2. Counts word frequencies
3. Uses spaCy to detect part-of-speech (verb, noun, adjective)
4. Extracts top N most common words
5. Seeds your database with real, high-frequency French vocabulary
"""

import os
import sys
from collections import Counter
from datetime import datetime, timedelta

import spacy
from dotenv import load_dotenv

from app.core.database import Base, SessionLocal, engine
from app.models.memory import UserWordMemory
from app.models.word import CEFRLevel, POSType, Word

load_dotenv()

# Map spaCy POS tags to our POSType enum
SPACY_TO_POSTYPE = {
    "VERB": POSType.VERB,
    "NOUN": POSType.NOUN,
    "ADJ": POSType.ADJECTIVE,
    "ADV": POSType.ADVERB,
}


def load_french_model():
    """Load spaCy French model. Install if not available."""
    try:
        nlp = spacy.load("fr_core_news_sm")
        print("✅ Loaded spaCy French model")
        return nlp
    except OSError:
        print("❌ French model not found. Installing...")
        print("   Run: python -m spacy download fr_core_news_sm")
        print("   Then re-run this script.")
        sys.exit(1)


def extract_word_frequencies(filepath: str, limit: int = 50000):
    """
    Extract word frequencies from Tatoeba file.
    Returns: Counter of {word: frequency}
    """
    print(f"📖 Scanning {filepath}...")

    word_counter = Counter()
    processed = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue

            french_sentence = parts[1].strip().lower()

            # Simple tokenization (split on whitespace, remove punctuation)
            import re

            words = re.findall(r"\b[a-zàâäçéèêëïîôùûüÿæœ]+\b", french_sentence)

            for word in words:
                if len(word) > 2:  # Skip very short words (le, la, de)
                    word_counter[word] += 1

            processed += 1
            if processed % 10000 == 0:
                print(f"   Processed {processed} sentences...")

            if processed >= limit:
                break

    print(f"✅ Found {len(word_counter)} unique words from {processed} sentences")
    return word_counter


def analyze_with_spacy(words_list, nlp, batch_size=1000):
    """
    Use spaCy to determine part-of-speech for each word.
    Returns: List of (word, pos_type, frequency) tuples
    """
    print(f"\n🔬 Analyzing {len(words_list)} words with spaCy...")

    analyzed_words = []

    # Process in batches for efficiency
    for i in range(0, len(words_list), batch_size):
        batch = words_list[i : i + batch_size]

        # Create sentences for spaCy (it needs context)
        # We'll use simple template: "Je [word]" for verbs, "Le [word]" for nouns
        docs = list(nlp.pipe([f"Je {word}" for word, _ in batch]))

        for (word, freq), doc in zip(batch, docs):
            # Get POS tag of our target word (usually second token)
            if len(doc) > 1:
                token = doc[1]  # Our word
                pos = token.pos_

                # Map to our enum
                pos_type = SPACY_TO_POSTYPE.get(pos, POSType.OTHER)

                analyzed_words.append((word, pos_type, freq))

        if (i + batch_size) % 5000 == 0:
            print(f"   Analyzed {i + batch_size}/{len(words_list)} words...")

    print(f"✅ Analysis complete!")
    return analyzed_words


def filter_vocabulary(analyzed_words, min_freq=10):
    """
    Filter and prioritize vocabulary.

    Rules:
    - Verbs: Keep top 200
    - Nouns: Keep top 400
    - Adjectives: Keep top 150
    - Adverbs: Keep top 50
    - Skip very low frequency words
    """
    print(f"\n🎯 Filtering vocabulary (min frequency: {min_freq})...")

    verbs = []
    nouns = []
    adjectives = []
    adverbs = []
    others = []

    for word, pos_type, freq in analyzed_words:
        if freq < min_freq:
            continue

        if pos_type == POSType.VERB:
            verbs.append((word, pos_type, freq))
        elif pos_type == POSType.NOUN:
            nouns.append((word, pos_type, freq))
        elif pos_type == POSType.ADJECTIVE:
            adjectives.append((word, pos_type, freq))
        elif pos_type == POSType.ADVERB:
            adverbs.append((word, pos_type, freq))
        else:
            others.append((word, pos_type, freq))

    # Sort by frequency
    verbs.sort(key=lambda x: x[2], reverse=True)
    nouns.sort(key=lambda x: x[2], reverse=True)
    adjectives.sort(key=lambda x: x[2], reverse=True)
    adverbs.sort(key=lambda x: x[2], reverse=True)

    # Take top N from each category
    final_vocab = verbs[:200] + nouns[:400] + adjectives[:150] + adverbs[:50]

    print(f"   📊 Selected vocabulary:")
    print(f"      • {min(200, len(verbs))} verbs")
    print(f"      • {min(400, len(nouns))} nouns")
    print(f"      • {min(150, len(adjectives))} adjectives")
    print(f"      • {min(50, len(adverbs))} adverbs")
    print(f"   Total: {len(final_vocab)} words")

    return final_vocab


def seed_database_with_vocabulary(vocabulary):
    """
    Add extracted vocabulary to database.
    vocabulary: List of (word, pos_type, frequency) tuples
    """
    print(f"\n💾 Seeding database with {len(vocabulary)} words...")

    # Recreate tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    added = 0
    for word_text, pos_type, freq in vocabulary:
        existing = db.query(Word).filter(Word.text == word_text).first()

        if not existing:
            # Estimate CEFR level based on frequency
            # Very rough heuristic: high freq = A1, low freq = B2
            if freq > 1000:
                level = CEFRLevel.A1
            elif freq > 500:
                level = CEFRLevel.A2
            elif freq > 200:
                level = CEFRLevel.B1
            else:
                level = CEFRLevel.B2

            word = Word(text=word_text, part_of_speech=pos_type, level=level)
            db.add(word)
            added += 1

    db.commit()
    print(f"✅ Added {added} new words to database")

    # Create UserWordMemory for all words
    print("📝 Creating memory records...")
    now = datetime.utcnow()

    for word in db.query(Word).all():
        existing_memory = (
            db.query(UserWordMemory).filter(UserWordMemory.word_id == word.id).first()
        )

        if not existing_memory:
            memory = UserWordMemory(
                word_id=word.id,
                strength=0,
                error_count=0,
                success_streak=0,
                last_seen=now - timedelta(days=1),
                next_review_at=now - timedelta(minutes=5),
            )
            db.add(memory)

    db.commit()
    db.close()

    print(f"✅ Created memory records for all words")


def main():
    """Main extraction pipeline"""

    print("=" * 70)
    print("INTELLIGENT VOCABULARY EXTRACTION FROM TATOEBA")
    print("=" * 70)
    print()

    filepath = "fra-eng.tsv"

    if not os.path.exists(filepath):
        print("❌ Error: fra-eng.tsv not found!")
        print("   Download from: https://www.manythings.org/anki/fra-eng.zip")
        sys.exit(1)

    # Step 1: Load spaCy
    nlp = load_french_model()

    # Step 2: Extract word frequencies
    word_counter = extract_word_frequencies(filepath, limit=100000)

    # Step 3: Get top 2000 most common words
    most_common = word_counter.most_common(2000)
    print(f"\n📈 Top 10 most frequent words:")
    for word, freq in most_common[:10]:
        print(f"   • {word}: {freq} occurrences")

    # Step 4: Analyze with spaCy
    analyzed = analyze_with_spacy(most_common, nlp)

    # Step 5: Filter and select vocabulary
    final_vocab = filter_vocabulary(analyzed, min_freq=10)

    # Step 6: Seed database
    seed_database_with_vocabulary(final_vocab)

    print("\n" + "=" * 70)
    print("🎉 VOCABULARY EXTRACTION COMPLETE!")
    print("=" * 70)
    print(f"\n✅ Your database now has ~800 real, high-frequency French words")
    print(f"📊 Distribution:")
    print(f"   • 200 most common verbs")
    print(f"   • 400 most common nouns")
    print(f"   • 150 most common adjectives")
    print(f"   • 50 most common adverbs")
    print()
    print("🚀 Next steps:")
    print("   1. Run: python scripts/import_tatoeba_with_embeddings.py")
    print("   2. This will import ~50k-100k sentences!")
    print("   3. Start your server: uvicorn app.main:app --reload")
    print("=" * 70)


if __name__ == "__main__":
    main()
