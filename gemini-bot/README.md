# Improved Gemini Search Bot

A cleaner command-line chatbot built with the **Google Gen AI Python SDK**. It supports:

- a more user-friendly CLI
- better formatted answers
- optional **Google Search grounding** for fresher, verifiable responses
- simple slash commands for control

According to Google's current Gemini API docs, the recommended Python SDK is `google-genai`, and Google Search grounding is enabled with `types.Tool(google_search=types.GoogleSearch())`. The model then decides whether a search is needed for a given prompt.

## Files

- `improved_gemini_bot.py` — the improved chatbot script
- `README.md` — this guide

## 1. Create a virtual environment

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Install the package

```bash
pip install google-genai
```

Google's SDK installation docs list `pip install google-genai` as the current installation command.

## 3. Set your API key

### macOS / Linux

```bash
export GEMINI_API_KEY="YOUR_API_KEY"
```

The SDK can read either `GEMINI_API_KEY` or `GOOGLE_API_KEY` from the environment.

## 4. Run the bot

```bash
python improved_gemini_bot.py
```

## Commands

```text
/help            Show commands
/search on       Enable Google Search grounding
/search off      Disable Google Search grounding
/model NAME      Change model
/sources         Explain source display
/quit            Exit the bot
```

## Notes about search grounding

Google's official grounding guide says that when `google_search` is enabled, Gemini analyzes the prompt, decides whether search would help, may run one or more searches automatically, and can return `groundingMetadata` containing search queries, source chunks, and citation mappings.

The same guide notes that current models use `google_search`, while older models used `google_search_retrieval`. Supported current models include Gemini 2.5 and Gemini 3 variants with search grounding support.

## Example usage

```text
You > What happened at the latest Apple event?
You > Explain Bernoulli's equation in simple terms.
You > /search off
You > Write a short email asking for a meeting.
```

## Troubleshooting

### `Missing API key`
Set your key first:

```bash
export GEMINI_API_KEY="YOUR_API_KEY"
```

### `429 RESOURCE_EXHAUSTED`
This usually means quota or billing limits were hit. Check your Gemini API usage and billing settings.

### `command not found: pip`
Try:

```bash
python3 -m pip install google-genai
```

### Wrong interpreter in VS Code
Make sure VS Code is using the Python interpreter from your `.venv`.

## Suggested next improvements

- add chat history memory in the same session
- export answers to Markdown or JSON
- add streaming output
- add retry logic for transient API failures
- add a proper citation formatter tied to grounding segments
