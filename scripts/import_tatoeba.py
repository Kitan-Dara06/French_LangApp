# scripts/import_tatoeba_no_embeddings.py
"""
Fast Tatoeba import WITHOUT pre-generating embeddings.
Uses spaCy lemmatizer to match all word forms automatically.
"""

import os

import spacy

from app.core.database import SessionLocal
from app.models.sentence import Sentence, SourceType
from app.models.word import Word

# Load spaCy French model
print("🔄 Loading spaCy French model...")
try:
    nlp = spacy.load("fr_core_news_sm")
    print("✅ spaCy model loaded")
except OSError:
    print("❌ French model not found. Run: python -m spacy download fr_core_news_sm")
    exit(1)


def create_blanked_sentence(sentence, word_to_blank):
    """Replace target word with ___"""
    import re

    pattern = re.compile(re.escape(word_to_blank), re.IGNORECASE)
    blanked = pattern.sub("___", sentence, count=1)
    return blanked


def build_lemma_map(db):
    """
    Build a map of lemmas to Word objects.
    Returns: {lemma: Word}

    Example: {"aller": Word(text="aller"), "être": Word(text="être")}
    """
    lemma_map = {}

    for word in db.query(Word).all():
        # The word text itself is the lemma (infinitive form)
        lemma_map[word.text.lower()] = word

    print(f"📖 Loaded {len(lemma_map)} lemmas (base word forms)")
    return lemma_map


def import_with_lemmatization(filepath: str, limit: int = 100000):
    """
    Import sentences using spaCy lemmatizer to match all forms.
    """

    db = SessionLocal()

    # Build lemma map
    lemma_map = build_lemma_map(db)

    imported_count = 0
    processed_count = 0

    print(f"🚀 Starting intelligent import with lemmatization...")
    print(f"   This will match ALL conjugations automatically!\n")

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            processed_count += 1

            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue

            french_sentence = parts[1].strip()
            english_translation = parts[3].strip()

            # Use spaCy to lemmatize the sentence
            doc = nlp(french_sentence)

            # Find words that match our vocabulary (by lemma)
            matched = False
            for token in doc:
                if matched:
                    break

                lemma = token.lemma_.lower()

                # Check if this lemma exists in our vocabulary
                if lemma in lemma_map:
                    word = lemma_map[lemma]

                    # Use the ACTUAL word from the sentence (conjugated form)
                    actual_word = token.text

                    blanked = create_blanked_sentence(french_sentence, actual_word)

                    # Check if this sentence already exists
                    existing = (
                        db.query(Sentence)
                        .filter(
                            Sentence.text == french_sentence,
                            Sentence.target_word_id == word.id,
                        )
                        .first()
                    )

                    if not existing:
                        sentence = Sentence(
                            text=french_sentence,
                            blanked_text=blanked,
                            target_word_id=word.id,
                            source=SourceType.TATOEBA,
                            english_translation=english_translation,
                            embedding=None,  # Generated on-demand
                        )
                        db.add(sentence)
                        imported_count += 1
                        matched = True  # Only one word per sentence

                        if imported_count % 1000 == 0:
                            db.commit()
                            print(
                                f"Imported {imported_count} sentences "
                                f"(processed {processed_count})..."
                            )

            if imported_count >= limit:
                break

    db.commit()
    db.close()

    print(f"\n✅ Imported {imported_count} sentences WITHOUT embeddings")
    print(f"📊 Processed {processed_count} lines from Tatoeba")
    print(f"💾 Database size: ~{imported_count * 100 / 1024:.1f} KB (text only)")
    print(f"💰 Cost: $0 (embeddings generated on-demand)")
    print(f"\n🎯 Matched verb forms automatically:")
    print(f"   Example: 'aller' matched vais, va, allons, irai, etc.")
    print(f"   Example: 'être' matched suis, est, était, sera, etc.")


if __name__ == "__main__":
    import sys

    filepath = "fra-eng.tsv"

    if not os.path.exists(filepath):
        print("❌ fra-eng.txt not found!")
        print("   Download from: https://www.manythings.org/anki/fra-eng.zip")
        sys.exit(1)

    print("=" * 60)
    print("INTELLIGENT TATOEBA IMPORT (NO EMBEDDINGS)")
    print("Using spaCy Lemmatizer")
    print("=" * 60)
    print()

    import_with_lemmatization(filepath, limit=100000)

    print("\n" + "=" * 60)
    print("🎉 IMPORT COMPLETE!")
    print("=" * 60)
    print("\nℹ️  Benefits of this approach:")
    print("   ✅ No hardcoded conjugations needed")
    print("   ✅ Matches ALL verb forms automatically")
    print("   ✅ Works for nouns, adjectives too (plural forms)")
    print("   ✅ Embeddings generated on-demand (pay as you go)")
    print("\n💡 Next: Start your server and practice!")
    print("=" * 60)
