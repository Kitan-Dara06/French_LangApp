import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.memory import UserWordMemory
from app.models.sentence import Sentence, SourceType
from app.models.word import Word
from app.services.embedding_service import ensure_embedding
from app.services.rag import generate_sentences_with_rag
from app.services.srs import get_due_words, update_on_correct, update_on_wrong
from app.services.validator import validate_answer
from app.services.verb_drill import generate_drill_sentences, should_enter_drill

router = APIRouter()


class SubmitAnswer(BaseModel):
    word_id: int
    user_input: str


@router.get("/next-question")
def get_next_question(db: Session = Depends(get_db)):
    due_words = get_due_words(db, limit=1)
    if not due_words:
        return {"message": "No words due for review!"}

    memory = due_words[0]

    # ← FIX: Define word BEFORE using it
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
        raise HTTPException(404, "No sentences available and generation failed")

    sentence = random.choice(sentences)
    # if sentence.embedding is None:
    #     ensure_embedding(sentence, db)

    return {
        "sentence": sentence.blanked_text,
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
    is_correct = validate_answer(data.user_input, word.text)

    if is_correct:
        update_on_correct(memory, db)
    else:
        update_on_wrong(memory, db)

        if word is not None and should_enter_drill(memory, word):
            return {
                "correct": False,
                "next_action": "verb_drill",
                "drill_sentences": generate_drill_sentences(word, 10),
            }

    return {
        "correct": is_correct,
        "correct_answer": word.text if word else None,
        "next_review_in": str(memory.next_review_at) if memory else None,
    }
