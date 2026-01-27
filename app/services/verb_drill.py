import json
import re

from openai import OpenAI
from sqlalchemy.orm import Session

from app.models.memory import UserWordMemory
from app.models.word import POSType, Word


def should_enter_drill(memory: UserWordMemory, word: Word) -> bool:
    return bool(
        word.part_of_speech == POSType.VERB
        and memory.error_count >= 2
        and memory.success_count == 0
    )


client = OpenAI()


def _call_llm(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("LLM response content is None")
    return str(content)


def generate_drill_sentences(word: Word, count: int = 10):
    # Avoid directly using ColumnElement in conditionals by extracting its value for comparison
    if str(word.part_of_speech) != str(POSType.VERB):
        raise ValueError("Drill sentences can only be generated for verbs")

    prompt = f"""
You are a French language teacher.

Generate exactly {count} short French sentences
using the verb "{word.text}".

Rules:
- CEFR level: {word.level.value}
- Vary tense: présent, passé composé, imparfait, futur
- One sentence per item
- Return ONLY valid JSON

Format:
[
  {{"sentence": "...", "tense": "présent"}}
]
"""

    raw_response = ""
    try:
        raw_response = _call_llm(prompt)
        return json.loads(raw_response)

    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw_response, re.DOTALL)
        if match:
            return json.loads(match.group())

    except Exception as e:
        print("LLM error:", e)

    return []
