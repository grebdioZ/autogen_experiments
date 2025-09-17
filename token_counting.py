"""Utilities for tracking and estimating token usage across model clients and conversations.

This module centralizes logic previously embedded in the notebook. It provides:

- wrap_chat_client_for_tokens: monkey-patch async `create` to accumulate usage (OpenAI-style response)
- print_token_usage: show native accumulated usage (if any)
- estimate_conversation_tokens: fallback estimation using tiktoken or heuristic
- print_token_usage_with_estimate: prefer native, else estimate
- log_token_usage: append usage metrics to a CSV log

The functions are resilient to missing attributes / structures and fail silently where
appropriate so they can be safely used in exploratory notebooks.
"""

from __future__ import annotations

import asyncio
import csv
import datetime
import os
from dataclasses import dataclass
from typing import Any, Iterable, List, Mapping, Sequence

__all__ = [
    "wrap_chat_client_for_tokens",
    "print_token_usage",
    "estimate_conversation_tokens",
    "print_token_usage_with_estimate",
    "log_token_usage",
]


# ---------------------------------------------------------------------------
# Native token accumulation via wrapping async client.create
# ---------------------------------------------------------------------------
@dataclass
class _TokenUsage:
    prompt: int = 0
    completion: int = 0
    total: int = 0


def wrap_chat_client_for_tokens(client: Any):
    """Wrap an async `create` method (if present) to accumulate token usage.

    The response object is expected to expose a `usage` attribute or dict
    containing keys like `prompt_tokens`, `completion_tokens`, `total_tokens` or
    model-specific variants. Missing keys are ignored.
    """
    orig_create = getattr(client, "create", None)
    if not (orig_create and asyncio.iscoroutinefunction(orig_create)):
        # Nothing to wrap; still attach accumulator for interface consistency
        client._token_usage_accumulator = _TokenUsage()  # type: ignore[attr-defined]
        return client

    usage_acc = _TokenUsage()

    async def wrapped_create(*args, **kwargs):  # type: ignore[override]
        resp = await orig_create(*args, **kwargs)
        try:  # noqa: SIM105
            usage: Any | None = None
            if hasattr(resp, "usage"):
                usage = getattr(resp, "usage")
            elif isinstance(resp, Mapping) and "usage" in resp:
                usage = resp["usage"]
            if usage:
                # Prompt tokens
                for k in (
                    "prompt_tokens",
                    "prompt",
                    "input_tokens",
                    "input_tokens_count",
                ):
                    if isinstance(usage, Mapping) and isinstance(usage.get(k), int):
                        usage_acc.prompt += int(usage[k])
                        break
                # Completion tokens
                for k in (
                    "completion_tokens",
                    "output_tokens",
                    "generated_tokens",
                    "output_tokens_count",
                ):
                    if isinstance(usage, Mapping) and isinstance(usage.get(k), int):
                        usage_acc.completion += int(usage[k])
                        break
                # Total tokens
                if isinstance(usage, Mapping) and isinstance(
                    usage.get("total_tokens"), int
                ):
                    usage_acc.total += int(usage["total_tokens"])
                else:
                    usage_acc.total = usage_acc.prompt + usage_acc.completion
        except Exception:  # noqa: BLE001
            # Silent fail to avoid breaking main workflow
            pass
        return resp

    setattr(client, "_orig_create", orig_create)
    setattr(client, "create", wrapped_create)
    client._token_usage_accumulator = usage_acc  # type: ignore[attr-defined]
    return client


def print_token_usage(client: Any) -> None:
    usage = getattr(client, "_token_usage_accumulator", None)
    if not usage or (usage.prompt == 0 and usage.completion == 0 and usage.total == 0):
        print("No token usage recorded yet.")
        return
    print(
        f"Token usage so far -> prompt: {usage.prompt}, completion: {usage.completion}, total: {usage.total}"
    )


# ---------------------------------------------------------------------------
# Fallback estimation using tiktoken if available, else heuristic
# ---------------------------------------------------------------------------
try:  # Optional dependency
    import tiktoken  # type: ignore

    _TIKTOKEN_AVAILABLE = True
except Exception:  # noqa: BLE001
    _TIKTOKEN_AVAILABLE = False


def _resolve_default_encoding():
    if not _TIKTOKEN_AVAILABLE:
        return None
    try:
        return tiktoken.get_encoding("cl100k_base")  # type: ignore
    except Exception:  # noqa: BLE001
        return None


_DEFAULT_ENCODING = _resolve_default_encoding()


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    if _DEFAULT_ENCODING is not None:
        try:
            return len(_DEFAULT_ENCODING.encode(text))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    # Heuristic: ~4 chars ≈ 1 token
    return max(1, len(text) // 4)


def estimate_conversation_tokens(
    messages: Sequence[Any], participantNames: Iterable[str] | None = None
) -> dict:
    """Estimate prompt/completion tokens from message objects or dicts.

    participantNames: iterable of agent names considered "prompt" roles unless
    role indicates assistant.
    Returns: dict(prompt=..., completion=..., total=..., method="tiktoken"|"heuristic")
    """
    participant_lower = {p.lower() for p in (participantNames or [])}

    prompt_tokens = 0
    completion_tokens = 0
    last_role_kind = None  # track for alternation fallback

    for idx, m in enumerate(messages):
        role = getattr(m, "role", None)
        if role is None and isinstance(m, Mapping):  # type: ignore[redundant-expr]
            role = m.get("role")  # type: ignore[index]
        content = getattr(m, "content", None)
        if content is None and isinstance(m, Mapping):
            content = m.get("content")  # type: ignore[index]
        tok = _estimate_tokens(str(content or ""))
        if role:
            rl = role.lower()
            if rl in ("assistant", "assistant_agent"):
                completion_tokens += tok
            elif rl in ("user", "system", "host") or rl in participant_lower:
                prompt_tokens += tok
            else:  # unknown label → alternate
                if last_role_kind == "prompt":
                    completion_tokens += tok
                    last_role_kind = "completion"
                else:
                    prompt_tokens += tok
                    last_role_kind = "prompt"
        else:  # No role → alternate by index
            if idx % 2 == 0:
                prompt_tokens += tok
            else:
                completion_tokens += tok

    return {
        "prompt": prompt_tokens,
        "completion": completion_tokens,
        "total": prompt_tokens + completion_tokens,
        "method": "tiktoken" if _DEFAULT_ENCODING else "heuristic",
    }


def print_token_usage_with_estimate(
    client: Any,
    messages: Sequence[Any] | None = None,
    participantNames: Iterable[str] | None = None,
    model_info: dict | None = None,
) -> None:
    """Print token usage and estimated cost if model_info is provided."""
    native = getattr(client, "_token_usage_accumulator", None)
    native_total = getattr(native, "total", 0) if native else 0
    if native_total > 0:
        print_token_usage(client)
        usage = native
    else:
        if messages is None:
            print("No native usage; supply messages for estimation.")
            return
        est = estimate_conversation_tokens(messages, participantNames)
        print(
            f"Estimated token usage -> prompt: {est['prompt']}, completion: {est['completion']}, total: {est['total']} (method={est['method']})"
        )
        usage = type("Obj", (), est)  # hack: allow attribute access
    # Compute cost if model_info is provided
    if model_info:
        model_type = model_info.get("type", "")
        if model_type.lower() == "ollama":
            in_cost = out_cost = 0.0
        else:
            in_cost = float(model_info.get("_approx-cost-per-input-megatoken_usd", 0))
            out_cost = float(model_info.get("_approx-cost-per-output-megatoken_usd", 0))
        input_tokens = getattr(usage, "prompt", 0)
        output_tokens = getattr(usage, "completion", 0)
        input_cost = (input_tokens / 1e6) * in_cost
        output_cost = (output_tokens / 1e6) * out_cost
        total_cost = input_cost + output_cost
        print(
            f"Approximate cost for this run: ${total_cost:.4f} USD (input: ${input_cost:.4f}, output: ${output_cost:.4f})"
        )


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def log_token_usage(
    topic: str,
    client: Any,
    messages: Sequence[Any] | None,
    participantNames: Iterable[str] | None = None,
    csv_path: str = "token_usage_log.csv",
    model_info: dict | None = None,
) -> dict:
    """Append usage information (native or estimated) to a CSV.

    Returns the row dict that was logged.
    """

    native = getattr(client, "_token_usage_accumulator", None)
    if native and getattr(native, "total", 0) > 0:
        data = {
            "prompt": native.prompt,
            "completion": native.completion,
            "total": native.total,
            "method": "native",
        }
    else:
        if messages is None:
            raise ValueError("messages must be provided when native usage is absent")
        est = estimate_conversation_tokens(messages, participantNames)
        data = {**est}

    # Compute cost if model_info is provided
    input_cost = output_cost = total_cost = None
    if model_info:
        model_type = model_info.get("type", "")
        if model_type.lower() == "ollama":
            in_cost = out_cost = 0.0
        else:
            in_cost = float(model_info.get("_approx-cost-per-input-megatoken_usd", 0))
            out_cost = float(model_info.get("_approx-cost-per-output-megatoken_usd", 0))
        input_tokens = data["prompt"]
        output_tokens = data["completion"]
        input_cost = (input_tokens / 1e6) * in_cost
        output_cost = (output_tokens / 1e6) * out_cost
        total_cost = input_cost + output_cost

    row = {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "topic": topic,
        "prompt": data["prompt"],
        "completion": data["completion"],
        "total": data["total"],
        "method": data.get("method", "native"),
    }
    if total_cost is not None:
        row["cost_usd"] = round(float(total_cost or 0.0), 6)
        row["input_cost_usd"] = round(float(input_cost or 0.0), 6)
        row["output_cost_usd"] = round(float(output_cost or 0.0), 6)

    file_exists = os.path.isfile(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    print(f"Logged token usage to {csv_path}: {row}")
    return row
