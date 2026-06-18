import json
from typing import Any, Dict

import anthropic
import httpx
from pydantic import ValidationError

from app.schemas.ai_category import (
    AICategoryCreateResponse,
)


GEMINI_BASE_URL_V1BETA = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_BASE_URL_V1 = "https://generativelanguage.googleapis.com/v1"


def _build_prompt(prompt: str, language_from: str, language_to: str, count: int) -> str:
    # STRICT JSON request: no markdown, no commentary.
    return f"""You are a language-learning assistant.

Task:
User prompt: {prompt!r}
Create vocabulary for a learner.

Rules:
- Generate EXACTLY {count} items.
- The items must be base-form verbs (e.g., 'go', 'make', 'travel') unless language rules strongly suggest otherwise.
- language_from words must be in {language_from}.
- translations must be in {language_to}.
- Return ONLY valid JSON (no markdown, no backticks, no extra keys, no explanations).

JSON schema to follow:
{{
  \"category_name\": string,
  \"category_description\": string | null,
  \"words\": [
    {{
      \"original_word\": string,
      \"translation\": string,
      \"language_from\": string,
      \"language_to\": string
    }}
  ]
}}
"""


def _normalize_model_for_rest(model: str) -> str:
    """
    Generative Language REST expects the model id without a leading `models/`.
    We defensively strip any repeated prefix like `models/models/...`.
    """
    m = (model or "").strip()
    while m.startswith("models/"):
        m = m[len("models/") :].strip()
    return m


def _candidate_gemini_models(raw_model: str) -> list[str]:
    raw_model = _normalize_model_for_rest(raw_model)

    fallbacks = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
    ]

    if not raw_model:
        return fallbacks

    candidates = [raw_model] + [m for m in fallbacks if m != raw_model]

    seen = set()
    out = []
    for m in candidates:
        nm = _normalize_model_for_rest(m)
        if nm and nm not in seen:
            seen.add(nm)
            out.append(nm)
    return out


async def _post_gemini_generate_content(
    *,
    api_key: str,
    model: str,
    full_prompt: str,
    timeout_s: int,
) -> Dict[str, Any]:
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": full_prompt}
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
        },
    }

    # Try both v1beta and v1. Some projects/accounts differ in what's enabled.
    base_urls = [GEMINI_BASE_URL_V1BETA, GEMINI_BASE_URL_V1]
    errors: list[str] = []

    # REST path must not include a leading `models/`
    model_for_rest = _normalize_model_for_rest(model)

    for base in base_urls:
        url = f"{base}/models/{model_for_rest}:generateContent?key={api_key}"
        try:
            async with httpx.AsyncClient(timeout=timeout_s) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code in (404, 429):
                    errors.append(f"{base}/models/{model}:generateContent ({resp.status_code})")
                    continue
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response is not None else 0
            errors.append(f"{base}/models/{model}:generateContent ({status})")

    raise RuntimeError(
        "Gemini generateContent failed (tried v1beta and v1) for model. "
        f"Tried errors: {errors}"
    )


async def generate_category_and_words_gemini(
    *,
    api_key: str,
    model: str,
    prompt: str,
    language_from: str,
    language_to: str,
    count: int,
    timeout_s: int = 60,
) -> Dict[str, Any]:
    full_prompt = _build_prompt(prompt, language_from, language_to, count)

    last_error: Exception | None = None
    data: Dict[str, Any] | None = None

    for candidate_model in _candidate_gemini_models(model):
        try:
            data = await _post_gemini_generate_content(
                api_key=api_key,
                model=candidate_model,
                full_prompt=full_prompt,
                timeout_s=timeout_s,
            )
            break
        except Exception as exc:
            last_error = exc
            continue
    else:
        raise RuntimeError(f"Gemini generateContent failed for all model candidates. Last error: {last_error}")

    if data is None:
        raise RuntimeError("Gemini generateContent returned no data")

    # Gemini response shape varies; try common paths.
    text = None
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        pass

    if not text:
        raise RuntimeError("Gemini returned empty content")

    # AI should return raw JSON; parse it.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: attempt to extract first JSON object.
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


async def generate_category_and_words_claude(
    *,
    api_key: str,
    model: str,
    prompt: str,
    language_from: str,
    language_to: str,
    count: int,
    timeout_s: int = 60,
) -> Dict[str, Any]:
    full_prompt = _build_prompt(prompt, language_from, language_to, count)

    client = anthropic.AsyncAnthropic(api_key=api_key)

    stream = await client.messages.create(
        model=model,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": full_prompt}],
        stream=True,
    )

    message = await stream.get_final_message()

    text = None
    for block in message.content:
        if block.type == "text":
            text = block.text
            break

    if not text:
        raise RuntimeError("Claude returned empty content")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def validate_ai_category_payload(payload: Dict[str, Any]) -> AICategoryCreateResponse:
    # We map AI payload to our response model; inserted/skipped are filled by endpoint.
    # The endpoint will re-embed words; here we only validate structure.
    # Build a partial response for validation.
    words = payload.get("words", [])

    # Validate word fields exist.
    normalized_payload = {
        "category_id": 0,
        "category_name": payload.get("category_name"),
        "category_description": payload.get("category_description"),
        "inserted_words": 0,
        "skipped_words": 0,
        "words": words,
    }

    return AICategoryCreateResponse(**normalized_payload)

