# scripts/seed_test_data.py
"""
Quick script to populate your database with test data.
Run this ONCE to get started testing.
"""

from datetime import datetime, timedelta, timezone

from app.core.database import Base, SessionLocal, engine
from app.models.memory import UserWordMemory
from app.models.sentence import Sentence, SourceType
from app.models.word import CEFRLevel, POSType, Word


def seed_database():
    """Add test words, sentences, and memory records"""

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    print("🌱 Seeding test data...")

    # Check if already seeded
    existing_words = db.query(Word).count()
    if existing_words > 0:
        print(f"⚠️  Database already has {existing_words} words. Skipping seed.")
        print("   Delete your database and re-run if you want fresh data.")
        db.close()
        return

    # 1. Create some basic French verbs
    verbs_data = [
        ("aller", "to go"),
        ("être", "to be"),
        ("avoir", "to have"),
        ("faire", "to do/make"),
        ("pouvoir", "to be able to"),
        ("voir", "to see"),
        ("venir", "to come"),
        ("prendre", "to take"),
        ("vouloir", "to want"),
        ("dire", "to say"),
    ]

    words = []
    for french, english in verbs_data:
        word = Word(text=french, part_of_speech=POSType.VERB, level=CEFRLevel.A1)
        db.add(word)
        words.append(word)

    db.commit()
    print(f"✅ Created {len(words)} French verbs")

    # 2. Create sentences for each word
    sentences_data = {
        "aller": [
            ("Je vais à l'école", "Je ___ à l'école"),
            ("Tu vas au marché", "Tu ___ au marché"),
            ("Il va bien", "Il ___ bien"),
        ],
        "être": [
            ("Je suis français", "Je ___ français"),
            ("Tu es intelligent", "Tu ___ intelligent"),
            ("Elle est belle", "Elle ___ belle"),
        ],
        "avoir": [
            ("J'ai un chat", "J'___ un chat"),
            ("Tu as faim", "Tu ___ faim"),
            ("Il a vingt ans", "Il ___ vingt ans"),
        ],
        "faire": [
            ("Je fais du sport", "Je ___ du sport"),
            ("Tu fais tes devoirs", "Tu ___ tes devoirs"),
            ("On fait la cuisine", "On ___ la cuisine"),
        ],
        "pouvoir": [
            ("Je peux venir", "Je ___ venir"),
            ("Tu peux m'aider", "Tu ___ m'aider"),
            ("Il peut courir vite", "Il ___ courir vite"),
        ],
        "voir": [
            ("Je vois la mer", "Je ___ la mer"),
            ("Tu vois le problème", "Tu ___ le problème"),
            ("Elle voit ses amis", "Elle ___ ses amis"),
        ],
        "venir": [
            ("Je viens demain", "Je ___ demain"),
            ("Tu viens avec moi", "Tu ___ avec moi"),
            ("Il vient de Paris", "Il ___ de Paris"),
        ],
        "prendre": [
            ("Je prends le bus", "Je ___ le bus"),
            ("Tu prends un café", "Tu ___ un café"),
            ("On prend le train", "On ___ le train"),
        ],
        "vouloir": [
            ("Je veux dormir", "Je ___ dormir"),
            ("Tu veux manger", "Tu ___ manger"),
            ("Elle veut partir", "Elle ___ partir"),
        ],
        "dire": [
            ("Je dis la vérité", "Je ___ la vérité"),
            ("Tu dis bonjour", "Tu ___ bonjour"),
            ("Il dit au revoir", "Il ___ au revoir"),
        ],
    }

    sentence_count = 0
    for word in words:
        if word.text in sentences_data:
            for full_text, blanked_text in sentences_data[word.text]:
                sentence = Sentence(
                    text=full_text,
                    blanked_text=blanked_text,
                    target_word_id=word.id,
                    source=SourceType.MANUAL,
                )
                db.add(sentence)
                sentence_count += 1

    db.commit()
    print(f"✅ Created {sentence_count} test sentences")

    # 3. Create UserWordMemory records (make them all due for review NOW)
    now = datetime.now(timezone.utc)
    for word in words:
        memory = UserWordMemory(
            word_id=word.id,
            strength=0,  # New word
            error_count=0,
            success_count=0,
            last_seen=now - timedelta(days=1),  # Last seen yesterday
            next_review_at=now - timedelta(minutes=5),  # Due now!
        )
        db.add(memory)

    db.commit()
    print(f"✅ Created {len(words)} memory records (all due for review)")

    db.close()

    print("\n" + "=" * 60)
    print("🎉 DATABASE SEEDED SUCCESSFULLY!")
    print("=" * 60)
    print(f"📊 Summary:")
    print(f"   • {len(words)} French verbs")
    print(f"   • {sentence_count} practice sentences")
    print(f"   • All words are due for review RIGHT NOW")
    print()
    print("🚀 Next steps:")
    print("   1. Run: uvicorn app.main:app --reload")
    print("   2. Visit: http://localhost:8000")
    print("   3. Start practicing!")
    print("=" * 60)


if __name__ == "__main__":
    seed_database()
