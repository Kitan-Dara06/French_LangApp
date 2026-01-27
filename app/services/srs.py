from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.memory import UserWordMemory

INTERVALS = {
    0: timedelta(minutes=5),
    1: timedelta(hours=2),
    2: timedelta(hours=4),
    3: timedelta(days=1),
    4: timedelta(days=3),
    5: timedelta(days=7),
    6: timedelta(days=21),
}


def update_on_correct(memory: UserWordMemory, db: Session):
    memory.strength = min(memory.strength + 1, 5)
    memory.success_streak += 1
    memory.last_seen = datetime.now(timezone.utc)
    memory.next_review_at = datetime.now(timezone.utc) + INTERVALS[memory.strength]
    db.commit()


def update_on_wrong(memory: UserWordMemory, db: Session):
    memory.strength = max(memory.strength - 1, 0)
    memory.success_streak = 0
    memory.error_count += 1
    memory.last_seen = datetime.now(timezone.utc)
    memory.next_review_at = datetime.now(timezone.utc) + INTERVALS[0]
    db.commit()


def get_due_words(db: Session, limit: int = 10):
    now = datetime.now(timezone.utc)
    return (
        db.query(UserWordMemory)
        .filter(UserWordMemory.next_review_at <= now)
        .order_by(UserWordMemory.strength.asc(), UserWordMemory.next_review_at.asc())
        .limit(limit)
        .all()
    )
