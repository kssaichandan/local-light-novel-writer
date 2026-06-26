"""Thin client over the local Ollama HTTP API.

All calls go to OLLAMA_HOST (the user's own machine). No external network —
unless the user pastes their own cloud API key (opt-in), which routes to that provider.
"""
from __future__ import annotations

import asyncio
import contextvars
import json
import re
from typing import AsyncIterator

import httpx

from . import config


class OllamaError(RuntimeError):
    pass


# --------------------------------------------------------------------------- cloud LLM (opt-in)
# If the user pastes an API key in the browser, it rides along on each request as a header and is
# turned into this per-request config. When set, ALL generation routes to that cloud provider
# instead of local Ollama. When unset (the default), nothing changes — everything stays local.
# The key is NEVER stored on disk by the server; it only lives in this per-request context var.
_cloud_cfg: contextvars.ContextVar = contextvars.ContextVar("ln_cloud_cfg", default=None)


# Known providers: how to reach each + a sensible default model.
_PROVIDERS = {
    "openai":     {"kind": "openai",    "base": "https://api.openai.com/v1",                          "model": "gpt-4o-mini"},
    "openrouter": {"kind": "openai",    "base": "https://openrouter.ai/api/v1",                       "model": "openrouter/auto"},
    "anthropic":  {"kind": "anthropic", "base": "https://api.anthropic.com/v1",                       "model": "claude-sonnet-4-6"},
    "gemini":     {"kind": "openai",    "base": "https://generativelanguage.googleapis.com/v1beta/openai", "model": "gemini-2.0-flash"},
    "groq":       {"kind": "openai",    "base": "https://api.groq.com/openai/v1",                     "model": "llama-3.3-70b-versatile"},
}


def _auto_provider(key: str) -> str:
    """Best-effort guess from the key's prefix (used when the user picks 'Auto')."""
    if key.startswith("sk-or-"):
        return "openrouter"
    if key.startswith("sk-ant-"):
        return "anthropic"
    if key.startswith("gsk_"):
        return "groq"
    if key.startswith("AIza") or key.startswith("AQ.") or key.startswith("AQ"):
        return "gemini"
    return "openai"


def _detect(key: str, model: str, provider: str = "") -> dict:
    """Build the per-request cloud config. If the user picked a provider explicitly, use it;
    otherwise guess from the key prefix so 'just paste the key' still works."""
    provider = (provider or "").strip().lower()
    if provider not in _PROVIDERS:
        provider = _auto_provider(key)
    cfg = dict(_PROVIDERS[provider])
    cfg["key"] = key
    if model:
        cfg["model"] = model
    return cfg


def set_cloud(key: str | None, model: str | None, provider: str | None = None):
    """Set (or clear) the cloud config for this request from a pasted key. Returns a reset token."""
    key = (key or "").strip()
    return _cloud_cfg.set(_detect(key, (model or "").strip(), provider or "") if key else None)


def reset_cloud(token) -> None:
    try:
        _cloud_cfg.reset(token)
    except (ValueError, LookupError):
        pass


def cloud_active() -> bool:
    """True when this request is routed to a cloud model (so callers can safely run several
    generations in parallel — local Ollama on a small CPU should NOT be hit concurrently)."""
    return _cloud_cfg.get() is not None


_CLOUD_TIMEOUT = httpx.Timeout(connect=15.0, read=300.0, write=60.0, pool=60.0)


class _CloudHTTPStatus(OllamaError):
    """A cloud call failed with an HTTP status BEFORE any text arrived (safe to retry)."""

    def __init__(self, status: int, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


def _parse_retry_after(resp: httpx.Response) -> float | None:
    ra = resp.headers.get("retry-after")
    if not ra:
        return None
    try:
        return max(0.0, float(ra))
    except ValueError:
        return None


async def _stream_openai(cfg: dict, system: str, user: str, temperature: float,
                         json_mode: bool = False, prose: bool = False) -> AsyncIterator[str]:
    """Stream from an OpenAI-compatible /chat/completions endpoint (OpenAI, OpenRouter, Groq, …)."""
    payload: dict = {
        "model": cfg["model"],
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": True,
        "temperature": temperature,
    }
    # Ask for guaranteed-JSON output where the API supports it (Groq/OpenAI/Gemini-compat do).
    # If a provider/model rejects it (400), _stream_cloud retries once without it.
    if json_mode and not cfg.get("no_json_mode"):
        payload["response_format"] = {"type": "json_object"}
    # Gentle anti-repetition for prose. The Ollama-specific repeat_penalty doesn't exist on these
    # APIs; frequency_penalty is the portable equivalent (kept light — big models need less help).
    if prose and config.CLOUD_PROSE_FREQUENCY_PENALTY:
        payload["frequency_penalty"] = config.CLOUD_PROSE_FREQUENCY_PENALTY
    headers = {"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"}
    url = cfg["base"].rstrip("/") + "/chat/completions"
    host = httpx.URL(url).host
    async with httpx.AsyncClient(timeout=_CLOUD_TIMEOUT) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code >= 400:
                body = (await resp.aread()).decode("utf-8", "replace")
                # Name the host so a mis-detected key (e.g. a non-OpenAI key sent to OpenAI) is obvious.
                raise _CloudHTTPStatus(
                    resp.status_code,
                    f"Cloud model error {resp.status_code} from {host}: {body[:300]}. "
                    f"If the provider looks wrong, set it explicitly in the key manager.",
                    retry_after=_parse_retry_after(resp),
                )
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = (obj.get("choices") or [{}])[0].get("delta", {})
                chunk = delta.get("content") or ""
                if chunk:
                    yield chunk


async def _stream_anthropic(cfg: dict, system: str, user: str, temperature: float,
                            json_mode: bool = False, prose: bool = False) -> AsyncIterator[str]:
    """Stream from Anthropic's Messages API (different shape from OpenAI)."""
    payload = {
        "model": cfg["model"],
        # Anthropic REQUIRES a positive max_tokens; the local NUM_PREDICT may be -1 (Ollama
        # "unlimited") or huge, which would 400. Clamp to a safe chapter-sized budget.
        "max_tokens": min(8192, config.NUM_PREDICT if config.NUM_PREDICT > 0 else 4096),
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "stream": True,
        "temperature": min(temperature, 1.0),  # Anthropic caps at 1.0
    }
    headers = {"x-api-key": cfg["key"], "anthropic-version": "2023-06-01",
               "content-type": "application/json"}
    url = cfg["base"].rstrip("/") + "/messages"
    async with httpx.AsyncClient(timeout=_CLOUD_TIMEOUT) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code >= 400:
                body = (await resp.aread()).decode("utf-8", "replace")
                raise _CloudHTTPStatus(resp.status_code,
                                       f"Cloud model error {resp.status_code}: {body[:300]}",
                                       retry_after=_parse_retry_after(resp))
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                try:
                    obj = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                if obj.get("type") == "content_block_delta":
                    chunk = (obj.get("delta") or {}).get("text") or ""
                    if chunk:
                        yield chunk
                elif obj.get("type") == "message_stop":
                    break


async def _strip_think(stream: AsyncIterator[str]) -> AsyncIterator[str]:
    """Remove a reasoning model's <think>…</think> block from a stream.

    Some cloud models (DeepSeek-R1 distills, QwQ, …) emit their chain-of-thought inside think-tags
    before the real answer. Without this filter that monologue would land in the user's chapter.
    Handles tags split across chunks by holding back a small tail when a '<' might start a tag."""
    buf, in_think = "", False
    async for chunk in stream:
        buf += chunk
        out = []
        while buf:
            if in_think:
                end = buf.find("</think>")
                if end == -1:
                    buf = buf[-8:]          # keep a tail in case '</think>' is split across chunks
                    break
                buf = buf[end + len("</think>"):].lstrip("\n")
                in_think = False
                continue
            start = buf.find("<think>")
            if start != -1:
                out.append(buf[:start])
                buf = buf[start + len("<think>"):]
                in_think = True
                continue
            # No full tag. Hold back the tail if it could be the START of '<think>'.
            cut = len(buf)
            for k in range(1, min(len("<think>"), len(buf)) + 1):
                if "<think>".startswith(buf[-k:]):
                    cut = len(buf) - k
                    break
            out.append(buf[:cut])
            buf = buf[cut:]
            break
        text = "".join(out)
        if text:
            yield text
    if buf and not in_think:
        yield buf


async def _stream_cloud(cfg: dict, system: str, user: str, temperature: float,
                        json_mode: bool = False, prose: bool = False) -> AsyncIterator[str]:
    """Stream from the cloud with RETRIES for failures that happen before any text arrives —
    rate limits (429) and transient server errors (5xx) are normal on free tiers (e.g. Groq), and
    without retries a single 429 used to kill the chapter and stop an auto-continue run.
    Once text starts flowing we never retry (we can't un-yield a partial chapter)."""
    gen = _stream_anthropic if cfg["kind"] == "anthropic" else _stream_openai
    attempts = max(1, config.CLOUD_RETRIES)
    last_err: Exception | None = None
    for attempt in range(attempts):
        started = False
        try:
            async for chunk in _strip_think(gen(cfg, system, user, temperature,
                                                json_mode=json_mode, prose=prose)):
                started = True
                yield chunk
            return
        except _CloudHTTPStatus as exc:
            if started:
                raise
            # A 400 right after asking for JSON mode usually means this provider/model doesn't
            # support response_format — drop it and try again immediately.
            if exc.status == 400 and json_mode and not cfg.get("no_json_mode"):
                cfg = dict(cfg)
                cfg["no_json_mode"] = True
                last_err = exc
                continue
            if exc.status not in (408, 409, 429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
            wait = exc.retry_after if exc.retry_after is not None else min(20.0, 2.0 * (2 ** attempt))
            await asyncio.sleep(wait)
            last_err = exc
        except httpx.HTTPError as exc:
            if started or attempt == attempts - 1:
                raise OllamaError(
                    f"Cloud model request failed ({type(exc).__name__}). "
                    "Check your API key, model name, and internet connection."
                ) from exc
            await asyncio.sleep(min(20.0, 2.0 * (2 ** attempt)))
            last_err = exc
    raise OllamaError(f"Cloud model kept failing after {attempts} tries: {last_err}")


async def list_models() -> list[str]:
    """Return the names of models the user has pulled locally."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{config.OLLAMA_HOST}/api/tags")
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaError(
                "Could not reach Ollama. Is it running? Try `ollama serve`."
            ) from exc
    data = resp.json()
    return [m["name"] for m in data.get("models", [])]


async def is_up() -> bool:
    try:
        await list_models()
        return True
    except OllamaError:
        return False


# We ALWAYS stream from Ollama, even for "single-shot" calls. On CPU a full
# generation can take many minutes; a non-streaming request would have to wait
# for the entire response in one socket read and hit the read timeout. Streaming
# resets the read clock on every token, so the per-read timeout below only fires
# if generation truly stalls — not just because it's slow.
# read = max wait between streamed chunks. On a slow CPU the *first* token of a big prompt
# (e.g. the arc map) can take several minutes, so give generous headroom.
_TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=60.0, pool=60.0)


def _payload(model: str, system: str, user: str, temperature: float, json_mode: bool,
             prose: bool = False) -> dict:
    options: dict = {
        "temperature": temperature,
        "num_ctx": config.NUM_CTX,
        "num_predict": config.NUM_PREDICT,
    }
    # Anti-repetition penalties for live prose only. JSON stages must be free to repeat keys and
    # structure, so we never apply these there.
    if prose:
        options["repeat_penalty"] = config.PROSE_REPEAT_PENALTY
        options["repeat_last_n"] = config.PROSE_REPEAT_LAST_N
        # Only send presence/frequency penalties when actually enabled. presence_penalty in
        # particular is left at 0 because it punishes periods/newlines/names and causes run-ons.
        if config.PROSE_PRESENCE_PENALTY:
            options["presence_penalty"] = config.PROSE_PRESENCE_PENALTY
        if config.PROSE_FREQUENCY_PENALTY:
            options["frequency_penalty"] = config.PROSE_FREQUENCY_PENALTY
    payload: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": True,
        "options": options,
    }
    if json_mode:
        payload["format"] = "json"
    return payload


async def _stream_chat(
    model: str, system: str, user: str, *, temperature: float, json_mode: bool = False,
    prose: bool = False,
) -> AsyncIterator[str]:
    """Core streaming generator. Yields content chunks as they arrive.

    If a cloud API key is set for this request, route there; otherwise use local Ollama."""
    cfg = _cloud_cfg.get()
    if cfg is not None:
        async for chunk in _stream_cloud(cfg, system, user, temperature,
                                         json_mode=json_mode, prose=prose):
            yield chunk
        return

    payload = _payload(model, system, user, temperature, json_mode, prose)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            async with client.stream(
                "POST", f"{config.OLLAMA_HOST}/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    chunk = obj.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                    if obj.get("done"):
                        break
    except httpx.HTTPError as exc:
        raise OllamaError(
            f"Generation stalled or failed ({type(exc).__name__}). "
            "The model may be too slow on this machine — try a smaller model."
        ) from exc


async def chat(
    model: str,
    system: str,
    user: str,
    *,
    temperature: float = config.DEFAULT_TEMPERATURE,
    json_mode: bool = False,
) -> str:
    """Collect a full completion (still streamed under the hood)."""
    parts = [chunk async for chunk in _stream_chat(model, system, user,
             temperature=temperature, json_mode=json_mode)]
    return "".join(parts)


async def chat_stream(
    model: str,
    system: str,
    user: str,
    *,
    temperature: float = config.DEFAULT_TEMPERATURE,
    prose: bool = False,
) -> AsyncIterator[str]:
    """Stream the assistant text token-by-token (for live chapter writing).

    Pass prose=True for chapter/scene prose so the anti-repetition penalties apply."""
    async for chunk in _stream_chat(model, system, user, temperature=temperature, prose=prose):
        yield chunk


async def chat_json(model: str, system: str, user: str, *, temperature: float = 0.6) -> dict:
    """Chat that must return a JSON object.

    Small local models occasionally emit truncated or slightly malformed JSON, so
    we retry a few times before giving up. Each retry is a fresh generation.
    """
    last_err: Exception | None = None
    for attempt in range(config.JSON_RETRIES):
        raw = await chat(model, system, user, temperature=temperature, json_mode=True)
        try:
            return _extract_json(raw)
        except (json.JSONDecodeError, OllamaError) as exc:
            last_err = exc
            # Nudge the next attempt to be a bit more deterministic.
            temperature = max(0.2, temperature - 0.2)
    raise OllamaError(
        f"Model failed to return valid JSON after {config.JSON_RETRIES} tries. "
        f"Last error: {last_err}. Try again, or pick a different model."
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    # Strip ```json fences if the model added them.
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    # Narrow to the outermost object if there's stray prose around it.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    for candidate in (text, _strip_trailing_commas(text)):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise OllamaError(f"Model did not return valid JSON:\n{text[:500]}")


def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] — a common small-model JSON slip."""
    return re.sub(r",(\s*[}\]])", r"\1", text)
