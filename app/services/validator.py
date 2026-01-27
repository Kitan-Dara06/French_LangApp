import unicodedata


def normalize_text(text: str) -> str:
    text = text.strip().lower()
    return text


def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def validate_answer(
    user_input: str, correct_answer: str, allow_typo: bool = True
) -> bool:
    user = normalize_text(user_input)
    correct = normalize_text(correct_answer)

    if user == correct:
        return True

    if allow_typo and levenshtein_distance(user, correct) <= 1:
        return True

    return False
