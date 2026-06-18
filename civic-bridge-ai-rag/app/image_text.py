"""Image-to-text extraction for chat attachments.

The frontend sends a short-lived data URL with a chat turn. This module
validates the payload, asks a vision-capable LiteLLM model to extract visible
text using the user's prompt as context, and returns only text for the main
chat context.
"""

from __future__ import annotations

import base64
import re

from app import config, llm

SUPPORTED_IMAGE_TYPES = frozenset({
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/webp",
})

_DATA_URL_RE = re.compile(
    r"^data:(?P<mime>[-\w.]+/[-\w.+]+);base64,(?P<data>.+)$",
    re.DOTALL,
)


class ImageTextError(ValueError):
    pass


class ImageTextUnavailableError(RuntimeError):
    pass


def _normalise_mime_type(mime_type: str | None) -> str | None:
    if not mime_type:
        return None
    return mime_type.split(";", 1)[0].strip().lower() or None


def _image_data_url(image: str, mime_type: str | None) -> str:
    image = image.strip()
    match = _DATA_URL_RE.match(image)

    if match:
        detected_mime_type = _normalise_mime_type(match.group("mime"))
        encoded_image = match.group("data")
    else:
        detected_mime_type = _normalise_mime_type(mime_type)
        encoded_image = image

    if detected_mime_type not in SUPPORTED_IMAGE_TYPES:
        supported = ", ".join(sorted(SUPPORTED_IMAGE_TYPES))
        raise ImageTextError(f"Unsupported image type. Use one of: {supported}.")

    try:
        decoded = base64.b64decode(encoded_image, validate=True)
    except ValueError as error:
        raise ImageTextError("Image data must be valid base64.") from error

    if not decoded:
        raise ImageTextError("Image data is empty.")
    if len(decoded) > config.IMAGE_MAX_BYTES:
        size_mb = config.IMAGE_MAX_BYTES / (1024 * 1024)
        raise ImageTextError(f"Image is too large. Maximum size is {size_mb:.0f} MB.")

    return f"data:{detected_mime_type};base64,{encoded_image}"


def extract_text(
    image: str,
    mime_type: str | None = None,
    user_prompt: str | None = None,
) -> str:
    image_url = _image_data_url(image, mime_type)
    prompt_context = (
        f"\n\nUser prompt for this image:\n{user_prompt.strip()}"
        if user_prompt and user_prompt.strip()
        else ""
    )
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Extract the visible text from this image for a chat "
                        "context. Preserve the wording as closely as possible. "
                        "If there is no readable text, give a concise neutral "
                        "description of visible content that may matter for "
                        "hate-speech, safety, or reporting analysis. Do not "
                        "identify private people, and do not make legal "
                        "conclusions."
                        f"{prompt_context}"
                    ),
                },
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    ]

    try:
        text = llm.complete(
            messages,
            temperature=0,
            models=config.VISION_MODEL_CHAIN,
        )
    except llm.LLMError as error:
        raise ImageTextUnavailableError(
            "Image text extraction is temporarily unavailable."
        ) from error

    text = text.strip()
    if not text:
        raise ImageTextUnavailableError("Image text extraction returned no text.")

    return text[: config.IMAGE_TEXT_MAX_CHARS]
