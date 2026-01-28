import os
from collections import Counter

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.orm import Session

from app.models.session import SessionAttempt
from app.models.word import Word  # ← ADD THIS

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_session(session_id: str, db: Session) -> dict:
    attempts = (
        db.query(SessionAttempt).filter(SessionAttempt.session_id == session_id).all()
    )

    total = len(attempts)
    correct = sum(1 for a in attempts if a.is_correct)

    errors = [a for a in attempts if not a.is_correct]
    error_types = Counter(e.error_type for e in errors)
    confused_words = Counter(e.confused_with for e in errors if e.confused_with)

    avg_time = sum(a.response_time_ms for a in attempts) / total if total > 0 else 0

    strengths = detect_strengths(attempts, db)
    weaknesses = detect_weaknesses(attempts, db)

    return {
        "total": total,
        "correct": correct,
        "error_types": dict(error_types),
        "confused_words": dict(confused_words),
        "avg_response_time": avg_time,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }


def detect_strengths(attempts, db) -> list:
    strengths = []
    word_performance = {}

    for attempt in attempts:
        wid = attempt.word_id
        if wid not in word_performance:
            word_performance[wid] = []
        word_performance[wid].append(attempt.is_correct)

    for wid, results in word_performance.items():  # ← FIX: was word_id
        if len(results) >= 3:  # ← FIX: was 4, changed to 3
            accuracy = sum(results) / len(results)
            if accuracy >= 0.8:
                word = db.query(Word).get(wid)  # ← FIX: use wid
                if word:  # ← Safety check
                    strengths.append(
                        {
                            "word": word.text,
                            "accuracy": f"{sum(results)}/{len(results)}",
                            "context": "improving",
                        }
                    )

    return strengths[:3]  # ← Max 3, not 5


def detect_weaknesses(attempts, db) -> list:
    weaknesses = []
    word_performance = {}

    for attempt in attempts:
        if not attempt.is_correct:
            wid = attempt.word_id
            if wid not in word_performance:
                word_performance[wid] = 0
            word_performance[wid] += 1

    for word_id, fail_count in word_performance.items():
        if fail_count >= 2:
            word = db.query(Word).get(word_id)
            if word:  # ← Safety check
                weaknesses.append(
                    {"word": word.text, "pattern": "hesitation", "count": fail_count}
                )

    return weaknesses[:2]


def generate_linguistic_insight(analysis: dict, attempts, db) -> str:
    """Use OpenAI to generate ONE linguistic insight."""

    error_context = ""
    if analysis["confused_words"]:
        confused = list(analysis["confused_words"].items())[0]
        error_context = (
            f"User confused '{confused[0]}' with correct answer {confused[1]} times"
        )

    prompt = f"""You are a French linguistics expert analyzing a learning session.

Session context:
- Total attempts: {analysis["total"]}
- Main error pattern: {error_context}
- Error types: {analysis["error_types"]}

Generate ONE linguistic insight (2-3 sentences) that explains:
1. Why this confusion happens linguistically
2. The underlying grammar rule

Example: "Weather expressions in French use 'faire' (actions), not 'être' (states). This is because French treats weather as something the sky 'does', not 'is'."

Be specific and teaching-focused. No generic advice."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # ← FIX: correct model name
            messages=[
                {"role": "user", "content": prompt}  # ← FIX: was "system"
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating insight: {e}")
        return "Practice makes perfect. Keep working on the patterns you struggle with."


def generate_headline(analysis: dict, strengths: list, weaknesses: list) -> str:
    """Generate the one-sentence summary."""

    if len(weaknesses) > 0 and weaknesses[0]["count"] >= 3:
        return f"You're still working through {weaknesses[0]['word']} — that's the hardest part."

    if len(strengths) > 0:
        return f"You stopped hesitating on {strengths[0]['word']} — it's becoming automatic."

    return "You're building consistency across your vocabulary."


def generate_next_focus(weaknesses: list) -> str:  # ← ADD THIS FUNCTION
    """Generate forward-looking nudge."""

    if not weaknesses:
        return "Next session: New vocabulary awaits."

    weak_word = weaknesses[0]["word"]
    return f"Next session will focus on '{weak_word}' in different contexts."
