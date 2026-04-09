"""
LLM Helper — LaunchMind

Shared utility for calling Ollama with retry logic and robust JSON parsing.
"""

import json
import logging
import os
import re

import ollama

logger = logging.getLogger(__name__)

MODEL = os.getenv("OLLAMA_MODEL", "phi4:14b")
MAX_RETRIES = 2


def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = True) -> str | dict:
    """
    Call Ollama LLM with retry logic.

    Args:
        system_prompt: System message.
        user_prompt: User message.
        json_mode: If True, parse response as JSON with retries.

    Returns:
        Parsed dict if json_mode, raw string otherwise.
    """
    model = os.getenv("OLLAMA_MODEL", MODEL)

    for attempt in range(MAX_RETRIES + 1):
        try:
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "options": {
                    "num_ctx": 8192,
                    "temperature": 0.7,
                },
            }
            if json_mode:
                kwargs["format"] = "json"

            response = ollama.chat(**kwargs)
            content = response["message"]["content"]

            logger.info(f"LLM response length: {len(content)} chars")

            if not json_mode:
                return content

            # Try parsing JSON, with cleanup for common issues
            return _parse_json(content)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed (attempt {attempt + 1}): {e}")
            logger.warning(f"Raw content preview: {content[:200]}...")
            if attempt == MAX_RETRIES:
                raise
        except Exception as e:
            logger.error(f"LLM call failed (attempt {attempt + 1}): {e}")
            if attempt == MAX_RETRIES:
                raise


def _parse_json(text: str) -> dict:
    """Parse JSON from LLM response, handling common formatting issues."""
    text = text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find a complete JSON object in the text
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Try fixing common issues (trailing commas, unclosed strings)
    cleaned = re.sub(r',\s*}', '}', text)
    cleaned = re.sub(r',\s*]', ']', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to fix truncated JSON by closing open structures
    fixed = _fix_truncated_json(text)
    return json.loads(fixed)


def _fix_truncated_json(text: str) -> str:
    """Attempt to fix truncated JSON by closing open brackets/braces."""
    # Remove trailing incomplete string value
    text = re.sub(r',\s*"[^"]*$', '', text)
    text = re.sub(r':\s*"[^"]*$', ': ""', text)

    # Count open/close brackets
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')

    # Check for unclosed string
    in_string = False
    escaped = False
    for ch in text:
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string

    if in_string:
        text += '"'

    # Close open structures
    text += ']' * max(0, open_brackets)
    text += '}' * max(0, open_braces)

    return text
