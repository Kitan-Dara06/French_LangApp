import random
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.memory import UserWordMemory
from app.models.sentence import Sentence, SourceType
from app.models.session import SessionAttempt, SessionSummary
from app.models.word import Word
from app.services.error_classifier import classify_error  # ← Import this
from app.services.rag import generate_sentences_with_rag
from app.services.session_analyzer import (
    analyze_session,
    detect_strengths,
    detect_weaknesses,
    generate_headline,
    generate_linguistic_insight,
    generate_next_focus,
)
from app.services.srs import get_due_words, update_on_correct, update_on_wrong
from app.services.validator import validate_answer
from app.services.verb_drill import generate_drill_sentences, should_enter_drill

router = APIRouter()


# ← UPDATED: Add missing fields
class SubmitAnswer(BaseModel):
    word_id: int
    sentence_id: int  # ← NEW: Which sentence was shown
    user_input: str
    response_time_ms: int  # ← NEW: How long they took (frontend tracks this)
    session_id: str  # ← NEW: Frontend sends this


@router.get("/next-question")
def get_next_question(db: Session = Depends(get_db)):
    due_words = get_due_words(db, limit=1)
    if not due_words:
        return {"message": "No words due for review!"}

    memory = due_words[0]
    word = db.query(Word).get(memory.word_id)

    if not word:
        raise HTTPException(404, "Word not found")

    sentences = (
        db.query(Sentence).filter(Sentence.target_word_id == memory.word_id).all()
    )

    if not sentences:
        generated = generate_sentences_with_rag(
            db, word.text, word.part_of_speech.value, count=5
        )

        for item in generated:
            sentence = Sentence(
                text=item["sentence"],
                blanked_text=item["blanked"],
                target_word_id=word.id,
                tense=item.get("tense"),
                source=SourceType.LLM,
            )
            db.add(sentence)

        db.commit()
        sentences = (
            db.query(Sentence).filter(Sentence.target_word_id == memory.word_id).all()
        )

    if not sentences:
        raise HTTPException(404, "No sentences available")

    sentence = random.choice(sentences)

    return {
        "sentence": sentence.blanked_text,
        "sentence_id": sentence.id,  # ← NEW: Return sentence ID
        "word_id": word.id,
        "word_text": word.text,
        "english_translation": sentence.english_translation,
    }


@router.post("/submit-answer")
def submit_answer(data: SubmitAnswer, db: Session = Depends(get_db)):
    memory = (
        db.query(UserWordMemory).filter(UserWordMemory.word_id == data.word_id).first()
    )

    word = db.query(Word).get(data.word_id)

    if not word:
        raise HTTPException(404, "Word not found")

    if not memory:
        raise HTTPException(404, "Memory record not found")

    # Validate answer
    is_correct = validate_answer(data.user_input, word.text)

    # ← Record the attempt for session analysis
    attempt = SessionAttempt(
        session_id=data.session_id,  # ← Now comes from frontend
        word_id=data.word_id,
        sentence_id=data.sentence_id,  # ← Now in the model
        user_input=data.user_input,
        correct_answer=word.text,
        is_correct=is_correct,
        response_time_ms=data.response_time_ms,  # ← Fixed field name
        error_type=classify_error(data.user_input, word.text)
        if not is_correct
        else None,
        confused_with=data.user_input if not is_correct else None,
    )
    db.add(attempt)

    # Update SRS
    if is_correct:
        update_on_correct(memory, db)
    else:
        update_on_wrong(memory, db)

        # Check if verb drill needed
        if should_enter_drill(memory, word):
            return {
                "correct": False,
                "next_action": "verb_drill",
                "drill_sentences": generate_drill_sentences(word, 10),
            }

    db.commit()  # ← Commit the attempt

    return {
        "correct": is_correct,
        "correct_answer": word.text,
        "next_review_in": str(memory.next_review_at),
    }


@router.get("/session-summary/{session_id}")
def get_session_summary(session_id: str, db: Session = Depends(get_db)):
    """
    Generate the 'What Changed Today?' screen.
    """

    # Check if already generated (cached)
    existing = (
        db.query(SessionSummary).filter(SessionSummary.session_id == session_id).first()
    )

    if existing:
        return {
            "headline": existing.headline,
            "strengths": existing.strengths,
            "weaknesses": existing.weaknesses,
            "insight": existing.linguistic_insight,
            "next_focus": existing.next_focus,
        }

    # Generate fresh analysis
    attempts = (
        db.query(SessionAttempt).filter(SessionAttempt.session_id == session_id).all()
    )

    analysis = analyze_session(session_id, db)
    strengths = detect_strengths(attempts, db)
    weaknesses = detect_weaknesses(attempts, db)

    headline = generate_headline(analysis, strengths, weaknesses)
    insight = generate_linguistic_insight(analysis, attempts, db)
    next_focus = generate_next_focus(weaknesses)

    # Save summary
    summary = SessionSummary(
        session_id=session_id,
        started_at=attempts[0].timestamp,
        ended_at=attempts[-1].timestamp,
        total_attempts=len(attempts),
        correct_count=sum(1 for a in attempts if a.is_correct),
        headline=headline,
        strengths=strengths,
        weaknesses=weaknesses,
        linguistic_insight=insight,
        next_focus=next_focus,
    )
    db.add(summary)
    db.commit()

    return {
        "headline": headline,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "insight": insight,
        "next_focus": next_focus,
    }
