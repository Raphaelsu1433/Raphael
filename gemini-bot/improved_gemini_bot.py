#!/usr/bin/env python3
"""Improved Gemini CLI bot with optional Google Search grounding.

Features:
- Clean command-line interface
- Better output formatting
- Optional web-grounded answers with sources
- Helpful slash commands
- Graceful error handling

Environment:
    export GEMINI_API_KEY="your_api_key"

Install:
    pip install google-genai
"""

from __future__ import annotations

import os
import sys
import textwrap
from dataclasses import dataclass
from typing import Iterable, List, Optional

from google import genai
from google.genai import types


APP_TITLE = "Gemini Search Bot"
DEFAULT_MODEL = "gemini-2.5-flash"
LINE_WIDTH = 88


class Style:
    """Very small ANSI styling helper with safe fallback."""

    enabled = sys.stdout.isatty() and os.getenv("TERM") not in {None, "dumb"}

    RESET = "\033[0m" if enabled else ""
    BOLD = "\033[1m" if enabled else ""
    DIM = "\033[2m" if enabled else ""
    CYAN = "\033[36m" if enabled else ""
    GREEN = "\033[32m" if enabled else ""
    YELLOW = "\033[33m" if enabled else ""
    RED = "\033[31m" if enabled else ""
    MAGENTA = "\033[35m" if enabled else ""


def color(text: str, *codes: str) -> str:
    return "".join(codes) + text + Style.RESET


@dataclass
class BotState:
    model: str = DEFAULT_MODEL
    search_enabled: bool = True


def hr(char: str = "─") -> str:
    return char * LINE_WIDTH


def panel(title: str, body: str = "") -> str:
    lines = [color(title, Style.BOLD, Style.CYAN), hr()]
    if body:
        lines.append(body)
    return "\n".join(lines)


def wrap(text: str, width: int = LINE_WIDTH) -> str:
    paragraphs = text.splitlines() or [text]
    wrapped: List[str] = []
    for p in paragraphs:
        if not p.strip():
            wrapped.append("")
        else:
            wrapped.append(textwrap.fill(p, width=width))
    return "\n".join(wrapped)


def get_api_key() -> Optional[str]:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def create_client() -> genai.Client:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "Missing API key. Set GEMINI_API_KEY or GOOGLE_API_KEY in your terminal first."
        )
    return genai.Client(api_key=api_key)


def build_config(search_enabled: bool) -> types.GenerateContentConfig:
    tools = []
    if search_enabled:
        tools.append(types.Tool(google_search=types.GoogleSearch()))
    return types.GenerateContentConfig(
        tools=tools,
        temperature=0.3,
        system_instruction=(
            "Answer clearly and concisely. If the prompt needs recent or verifiable "
            "information, use search grounding when available. When sources are available, "
            "base the answer on them."
        ),
    )


def safe_get_text(response) -> str:
    text = getattr(response, "text", None)
    if text:
        return text.strip()

    # Fallback if .text is unavailable
    candidates = getattr(response, "candidates", None) or []
    parts: List[str] = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            maybe_text = getattr(part, "text", None)
            if maybe_text:
                parts.append(maybe_text)
    return "\n".join(parts).strip() or "[No text returned]"


@dataclass
class Source:
    title: str
    uri: str


def extract_sources(response) -> List[Source]:
    """Extract source list from grounding metadata with multiple fallbacks."""
    sources: List[Source] = []
    seen = set()

    # Try top-level metadata first.
    metadata = getattr(response, "grounding_metadata", None)
    candidates = list(getattr(response, "candidates", None) or [])

    if metadata is None:
        for cand in candidates:
            metadata = getattr(cand, "grounding_metadata", None)
            if metadata is not None:
                break

    if metadata is None:
        return sources

    chunks = getattr(metadata, "grounding_chunks", None) or []
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        if not web:
            continue
        title = getattr(web, "title", None) or "Untitled source"
        uri = getattr(web, "uri", None)
        if not uri:
            continue
        key = (title, uri)
        if key not in seen:
            seen.add(key)
            sources.append(Source(title=title, uri=uri))

    return sources


def print_banner(state: BotState) -> None:
    body = (
        f"Model: {state.model}\n"
        f"Search grounding: {'ON' if state.search_enabled else 'OFF'}\n"
        "Type a question, or use /help for commands."
    )
    print(panel(APP_TITLE, body))


def print_help() -> None:
    body = "\n".join(
        [
            "/help            Show commands",
            "/search on       Enable Google Search grounding",
            "/search off      Disable Google Search grounding",
            "/model NAME      Change model, e.g. /model gemini-2.5-flash",
            "/sources         Explain how sources are shown",
            "/quit            Exit the bot",
        ]
    )
    print(panel("Commands", body))


def print_sources_help() -> None:
    msg = (
        "When Google Search grounding is enabled, Gemini may decide to search the web. "
        "If grounded source metadata is returned, the bot prints a Sources section below the answer."
    )
    print(panel("About sources", wrap(msg)))


def handle_command(raw: str, state: BotState) -> bool:
    cmd = raw.strip()

    if cmd == "/help":
        print_help()
        return True

    if cmd == "/sources":
        print_sources_help()
        return True

    if cmd == "/quit":
        print(color("Goodbye.", Style.GREEN))
        raise SystemExit(0)

    if cmd.startswith("/search"):
        parts = cmd.split(maxsplit=1)
        if len(parts) == 2 and parts[1].lower() in {"on", "off"}:
            state.search_enabled = parts[1].lower() == "on"
            status = "ON" if state.search_enabled else "OFF"
            print(color(f"Search grounding: {status}", Style.GREEN))
        else:
            print(color("Usage: /search on  or  /search off", Style.YELLOW))
        return True

    if cmd.startswith("/model"):
        parts = cmd.split(maxsplit=1)
        if len(parts) == 2 and parts[1].strip():
            state.model = parts[1].strip()
            print(color(f"Model changed to: {state.model}", Style.GREEN))
        else:
            print(color("Usage: /model MODEL_NAME", Style.YELLOW))
        return True

    return False


def ask_gemini(client: genai.Client, prompt: str, state: BotState) -> tuple[str, List[Source]]:
    response = client.models.generate_content(
        model=state.model,
        contents=prompt,
        config=build_config(state.search_enabled),
    )
    return safe_get_text(response), extract_sources(response)


def print_answer(answer: str, sources: Iterable[Source]) -> None:
    print(panel("Answer", wrap(answer)))

    source_list = list(sources)
    if source_list:
        lines = []
        for idx, src in enumerate(source_list, start=1):
            lines.append(f"[{idx}] {src.title}\n    {src.uri}")
        print(panel("Sources", "\n".join(lines)))
    else:
        print(panel("Sources", color("No grounded sources returned for this answer.", Style.DIM)))


def main() -> None:
    state = BotState()

    try:
        client = create_client()
    except Exception as exc:
        print(color(f"Startup error: {exc}", Style.RED), file=sys.stderr)
        sys.exit(1)

    print_banner(state)

    while True:
        try:
            user_input = input(color("\nYou > ", Style.BOLD, Style.MAGENTA)).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n" + color("Session ended.", Style.GREEN))
            break

        if not user_input:
            continue

        if user_input.startswith("/") and handle_command(user_input, state):
            continue

        print(color("\nThinking...", Style.DIM))

        try:
            answer, sources = ask_gemini(client, user_input, state)
            print_answer(answer, sources)
        except Exception as exc:
            print(panel("Error", wrap(str(exc))))
            print(
                color(
                    "Tip: check your API key, billing/quota, model name, and network connection.",
                    Style.YELLOW,
                )
            )


if __name__ == "__main__":
    main()
