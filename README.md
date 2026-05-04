# Integrated Agent Pipeline

This codebase connects three parts into one flow:

1. **UI** accepts a user prompt.
2. **Researcher Agent** creates a draft answer.
3. **Manager Agent** reviews the draft against quality criteria.
4. If needed, the pipeline asks the Researcher to revise once.
5. The UI displays the final answer, Manager decision, and agent interaction log.

## Files

- `agents.py` — Researcher Agent, Manager Agent, review tools, logger, and integrated pipeline.
- `app.py` — Streamlit UI plus CLI/demo runner.
- `requirements.txt` — dependencies.
- `demo_log.txt` / `demo_log.json` — generated after running the demo.

## Setup

```bash
cd integrated_agent_pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional Gemini setup:

```bash
export GEMINI_API_KEY="your_api_key_here"
```

Important: use the environment variable name `GEMINI_API_KEY`. Do not put the API key itself inside `os.getenv(...)`.

## Run the Streamlit UI

```bash
streamlit run app.py
```

## Run terminal UI

```bash
python3 app.py --cli
```

## Run demo

```bash
python3 app.py --demo
```

The demo creates:

- `demo_log.txt`
- `demo_log.json`

## Success criteria checklist

- Accepts a prompt: handled by Streamlit text area or CLI input.
- Routes data between agents: `AgentPipeline.run()` sends prompt to Researcher, draft to Manager, and feedback back to Researcher if needed.
- Logs interactions: `InteractionLogger` records UI, Pipeline, Researcher, and Manager actions.
- Displays final approved answer: UI and CLI show the final answer and Manager report.
