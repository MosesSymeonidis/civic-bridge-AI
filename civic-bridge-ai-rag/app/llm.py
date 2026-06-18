import litellm
from pydantic import BaseModel, ValidationError

from app import config


class LLMError(RuntimeError):
    pass


def embed(texts: list[str]) -> list[list[float]]:
    resp = litellm.embedding(model=config.EMBED_MODEL, input=texts)
    return [item["embedding"] for item in resp["data"]]


def _extract_json(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in response")
    return text[start:end + 1]


def complete(
    messages,
    schema: type[BaseModel] | None = None,
    temperature: float = 0.2,
    models: list[str] | None = None,
):
    """Call the first available model in the chain and return the response.

    Args:
        messages: List of OpenAI-style chat messages.
        schema: Optional pydantic model; when provided, requests JSON output and
            validates/repairs the response.  If the first attempt fails validation
            a single repair request is issued on the same model; if that also fails
            the exception propagates to the outer except and the next model is tried.
        temperature: Sampling temperature (default 0.2).
        models: Override the model chain.  Defaults to config.MODEL_CHAIN.

    Note: ollama/llama3.1 may not support response_format json_object via litellm.
    If it errors for schema calls the chain is simply exhausted, which is an
    acceptable failure mode when both cloud providers are unavailable.
    """
    errors: list[str] = []
    for model in models or config.MODEL_CHAIN:
        try:
            kwargs: dict = dict(
                model=model,
                messages=messages,
                temperature=temperature,
                num_retries=2,
            )
            if schema is not None:
                kwargs["response_format"] = {"type": "json_object"}
            text = litellm.completion(**kwargs).choices[0].message.content
            if schema is None:
                return text
            # Attempt validation; on failure issue a single repair on the same model.
            # A repair failure falls through to the next model in the chain.
            try:
                return schema.model_validate_json(_extract_json(text))
            except (ValidationError, ValueError) as exc:
                repair = list(messages) + [
                    {"role": "assistant", "content": text},
                    {
                        "role": "user",
                        "content": (
                            f"Your JSON failed validation: {exc}. "
                            "Reply with corrected JSON only, no prose."
                        ),
                    },
                ]
                text2 = litellm.completion(
                    model=model,
                    messages=repair,
                    temperature=0,
                    response_format={"type": "json_object"},
                    num_retries=1,
                ).choices[0].message.content
                return schema.model_validate_json(_extract_json(text2))
        except Exception as exc:  # provider down, auth error, or repair failed
            errors.append(f"{model}: {exc}")
    raise LLMError("all models failed: " + "; ".join(errors))
