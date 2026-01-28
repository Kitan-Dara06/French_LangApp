from app.services.validator import levenshtein_distance


def classify_error(user_input: str, correct: str) -> str:
    user = user_input.lower().strip()
    correct = correct.lower().strip()

    if len(user) == len(correct):
        return "conjugation"

    if levenshtein_distance(user, correct) > 3:
        return "substitution"

    return "spelling"
