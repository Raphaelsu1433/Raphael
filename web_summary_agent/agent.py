from google.adk.agents import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="web_summary_agent",
    model="gemini-2.5-flash-lite",
    instruction=(
        "You are a concise research assistant.\n"
        "Your job is to answer user questions accurately.\n"
        "Decide whether web search is needed.\n"
        "Use Google Search when the question depends on recent, factual, or verifiable information.\n"
        "Do not use web search for simple common-knowledge or opinion questions.\n"
        "After getting enough information, produce a short, clear, accurate summary.\n"
        "When search is used, include source citations."
    ),
    description="Answers questions and uses web search only when needed.",
    tools=[google_search],
)