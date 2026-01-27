import json
import os
import re

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_sentences_for_word(word_text: str, count: int = 5, level: str = "A2"):
    prompt = f"""
You are a French language teacher.

Generate {count} French sentences at {level} level using the word "{word_text}".

Requirements:
- Natural, everyday French
- Vary sentence structure
- If verb, use different tenses
- One sentence per item
- No explanations
- Return ONLY valid JSON (no markdown)

Format:
[
  {{"sentence": "Je vais à l'école", "blanked": "Je ___ à l'école", "tense": "présent"}},
  {{"sentence": "Il est allé au marché", "blanked": "Il est ___ au marché", "tense": "passé composé"}}
]
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    content = response.choices[0].message.content
    if content is None:
        raise ValueError("LLM response content is None")
    response_text = content.strip()

    # Parse JSON safely
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Fallback: extract JSON block
        match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []
